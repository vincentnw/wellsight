"""Strategy × universe × quarter loop (spec Section 6, M1-M3 acceptance)."""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from fin580.backtest.strategies import s01_full_system
from fin580.repro.manifest import build_manifest, finalize_manifest, write_manifest

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"

UNIVERSE = ["FANG", "EOG", "DVN", "CTRA", "OXY", "MTDR", "PR", "OVV", "SM", "CRGY"]


def _load_earnings_dates() -> dict[tuple[str, date], date]:
    out: dict[tuple[str, date], date] = {}
    with open(PHASE1_OUTPUT / "earnings_dates.csv") as f:
        for r in csv.DictReader(f):
            t = r["ticker"]
            fpe = datetime.strptime(r["fiscal_quarter_end"], "%Y-%m-%d").date()
            ed = datetime.strptime(r["earnings_date_actual"], "%Y-%m-%d").date()
            out[(t, fpe)] = ed
    return out


def parse_quarter(label: str) -> date:
    """e.g. '2024Q3' -> date(2024, 9, 30)"""
    y, q = int(label[:4]), int(label[5])
    m = {1: 3, 2: 6, 3: 9, 4: 12}[q]
    d = {3: 31, 6: 30, 9: 30, 12: 31}[m]
    return date(y, m, d)


def _enumerate_quarters(start: str, end: str) -> list[str]:
    s_y, s_q = int(start[:4]), int(start[5])
    e_y, e_q = int(end[:4]), int(end[5])
    out: list[str] = []
    y, q = s_y, s_q
    while (y, q) <= (e_y, e_q):
        out.append(f"{y}Q{q}")
        q += 1
        if q > 4:
            q = 1
            y += 1
    return out


def _prev_earnings(
    eds: dict[tuple[str, date], date], ticker: str, fpe: date, fallback: date
) -> date:
    prior = sorted([d for (t, d) in eds.keys() if t == ticker and d < fpe])
    if prior:
        prev_q = prior[-1]
        return eds.get((ticker, prev_q), fallback - timedelta(days=90))
    return fallback - timedelta(days=90)


def run_single_cell(
    *,
    strategy: int,
    ticker: str,
    quarter_label: str,
    cm_label: str = "target",
) -> Path:
    fpe = parse_quarter(quarter_label)
    eds = _load_earnings_dates()
    earnings_date = eds.get((ticker, fpe))
    if earnings_date is None:
        raise ValueError(f"No earnings date found for {ticker} {quarter_label}")
    decision_date_T = earnings_date - timedelta(days=14)
    prev_e = _prev_earnings(eds, ticker, fpe, earnings_date)

    run_id = (
        f"{datetime.now().strftime('%Y-%m-%d')}-strategy{strategy}-"
        f"{ticker}-{quarter_label}-{cm_label}"
    )
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if strategy == 1:
        td = s01_full_system.signal(
            ticker=ticker,
            fiscal_quarter_end=fpe,
            decision_date_T=decision_date_T,
            prev_earnings_date=prev_e,
            run_dir=run_dir,
            cm_label=cm_label,
        )
        # Per Codex Round-6 fix 2: distinguish error-no-trade from
        # agent-decided-no-trade in console output by reading the cell row.
        results_path = run_dir / "strategy_01" / "cell_results.parquet"
        flag_suffix = ""
        if results_path.exists():
            df = pd.read_parquet(results_path)
            row = df[(df["ticker"] == ticker) & (df["fiscal_quarter_end"] == fpe.isoformat())]
            if len(row):
                if bool(row.iloc[0]["low_quality_flag"]) and row.iloc[0]["error"]:
                    flag_suffix = f"  [ERROR: {row.iloc[0]['error'][:60]}]"
        print(
            f"Strategy 1 {ticker} {quarter_label}: "
            f"{td.direction} size={td.size_pct:.2%}{flag_suffix}"
        )
    else:
        raise NotImplementedError(
            f"Strategy {strategy} is added in Tasks 25-33"
        )

    manifest = build_manifest(
        run_id=run_id,
        run_dir=run_dir,
        llm_state={
            "agent2": {"model_id": "Qwen/Qwen2.5-72B-Instruct"},
            "agent3": {"model_id": "llama-3.3-70b-versatile"},
            "agent4": {"model_id": "llama-3.3-70b-versatile"},
            "agent5_bull": {"model_id": "Qwen/Qwen2.5-72B-Instruct"},
            "agent5_bear": {"model_id": "llama-3.3-70b-versatile"},
            "agent5_arbiter": {"model_id": "deepseek-r1"},
        },
        parameters={
            "threshold_pct": 10,
            "max_position_size_pct": 15,
            "max_names": 8,
            "transaction_cost_bps": 30,
            "starting_capital_usd": 1_000_000,
        },
        confusion_matrix_label=cm_label,
        modules_used=[
            "fin580.agents.orchestrator",
            "fin580.backtest.runner",
            "fin580.backtest.strategies.s01_full_system",
        ],
    )
    finalize_manifest(manifest, run_dir)
    return run_dir


def run_window(
    *,
    strategy: int,
    start_quarter: str,
    end_quarter: str,
    cm_label: str = "target",
    run_suffix: str = "",
) -> Path:
    """Run strategy across 10-firm universe × quarter range."""
    from fin580.backtest.strategies import REGISTRY

    if strategy not in REGISTRY:
        raise ValueError(f"Unknown strategy {strategy}; available: {sorted(REGISTRY)}")

    eds = _load_earnings_dates()
    quarters = _enumerate_quarters(start_quarter, end_quarter)
    suffix = f"-{run_suffix}" if run_suffix else ""
    run_id = (
        f"{datetime.now().strftime('%Y-%m-%d')}-strategy{strategy}-"
        f"{start_quarter}_{end_quarter}-{cm_label}{suffix}"
    )
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    strat_dir = run_dir / f"strategy_{strategy:02d}"
    strat_dir.mkdir(parents=True, exist_ok=True)

    cell_records: list[dict] = []
    cells_done_in_session = 0
    strat_module = REGISTRY[strategy]
    is_llm_strategy = strategy in (1, 2)

    for q_label in quarters:
        fpe = parse_quarter(q_label)
        for ticker in UNIVERSE:
            ed = eds.get((ticker, fpe))
            if ed is None:
                continue
            T = ed - timedelta(days=14)
            prev_e = _prev_earnings(eds, ticker, fpe, ed)

            if strategy == 1:
                from fin580.agents.orchestrator import cell_complete
                already_done = cell_complete(run_dir, ticker, fpe)
            else:
                already_done = False

            try:
                td = strat_module.signal(
                    ticker=ticker,
                    fiscal_quarter_end=fpe,
                    decision_date_T=T,
                    prev_earnings_date=prev_e,
                    run_dir=run_dir,
                    cm_label=cm_label,
                )
                cell_records.append({
                    "ticker": ticker,
                    "fiscal_quarter_end": fpe.isoformat(),
                    "decision_date_T": T.isoformat(),
                    "direction": td.direction,
                    "size_pct": td.size_pct,
                })
            except Exception as e:
                cell_records.append({
                    "ticker": ticker,
                    "fiscal_quarter_end": fpe.isoformat(),
                    "decision_date_T": T.isoformat(),
                    "direction": "no_trade",
                    "size_pct": 0.0,
                    "error": str(e)[:200],
                })

            if is_llm_strategy and not already_done:
                cells_done_in_session += 1
                if cells_done_in_session % 10 == 0:
                    print(f"[strat={strategy}] {cells_done_in_session} fresh cells done", flush=True)

    if cell_records:
        df = pd.DataFrame(cell_records)
        df.to_parquet(strat_dir / "cell_results_summary.parquet")
        print(f"Strategy {strategy}: wrote {len(cell_records)} rows to {strat_dir}/cell_results_summary.parquet")
    manifest = build_manifest(
        run_id=run_id,
        run_dir=run_dir,
        llm_state={},
        parameters={
            "threshold_pct": 10,
            "transaction_cost_bps": 30,
        },
        confusion_matrix_label=cm_label,
        modules_used=[
            "fin580.agents.orchestrator",
            "fin580.backtest.runner",
            "fin580.backtest.strategies.s01_full_system",
        ],
    )
    finalize_manifest(manifest, run_dir)
    return run_dir


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--strategy", type=int, default=None,
                   help="Single-strategy run, e.g. --strategy 1")
    p.add_argument("--strategies", help="Multi-strategy run, e.g. --strategies 3,4,5")
    p.add_argument("--ticker", help="Single-cell mode: e.g. FANG")
    p.add_argument("--quarter", help="Single-cell mode: e.g. 2024Q3")
    p.add_argument("--window", help="Window mode: e.g. 2021Q1-2025Q4")
    p.add_argument("--cm-label", default="target")
    p.add_argument("--run-suffix", default="",
                   help="Optional suffix appended to run_id (for ablations, e.g. alpha0, nosat)")
    args = p.parse_args()

    if args.strategies:
        if not args.window:
            p.error("--strategies requires --window")
        s, e = args.window.split("-")
        for sid in [int(x) for x in args.strategies.split(",")]:
            print(f"\n=== Running Strategy {sid} ===")
            run_window(strategy=sid, start_quarter=s, end_quarter=e,
                       cm_label=args.cm_label, run_suffix=args.run_suffix)
    elif args.window:
        if args.strategy is None:
            p.error("--window requires --strategy or --strategies")
        s, e = args.window.split("-")
        run_window(strategy=args.strategy, start_quarter=s, end_quarter=e,
                   cm_label=args.cm_label, run_suffix=args.run_suffix)
    else:
        if not args.ticker or not args.quarter:
            p.error("Provide either --window OR (--ticker AND --quarter).")
        if args.strategy is None:
            args.strategy = 1
        run_single_cell(strategy=args.strategy, ticker=args.ticker,
                        quarter_label=args.quarter, cm_label=args.cm_label)
