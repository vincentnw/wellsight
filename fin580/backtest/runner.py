"""Strategy × universe × quarter loop (spec Section 6, M1-M3 acceptance).

Trade-selection layer (per docs/AGENT4_5_REDESIGN.md): after Agent 5 scores
every cell with conviction_score 0-100, an explicit per-quarter budget
selects the top K cells to actually fire as `long`. Cells outside the
top-K are forced to `no_trade` regardless of Agent 5's raw decision.
This is the mechanical replacement for the removed DL #56/#61 gates.
"""

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

# Trade-selection parameters — PRE-REGISTERED before 2024 final eval.
# See docs/AGENT4_5_REDESIGN.md Section 5.
TRADE_BUDGET_K_PER_CYCLE = int(
    # Default 4 cells per earnings cycle. Override via FIN580_K_PER_CYCLE env var
    # for ablation runs (e.g., K=8 for "looser" sensitivity).
    __import__("os").environ.get("FIN580_K_PER_CYCLE", "4")
)
TRADE_BUDGET_MIN_SCORE = float(
    # Minimum conviction_score to fire long even if cell is in top-K.
    # Default 45 = the "low" tier threshold. Below this, score-derived tier
    # is "none" so size would be 0 anyway, but enforcing here is explicit.
    __import__("os").environ.get("FIN580_MIN_SCORE", "45")
)
MAX_SIMULTANEOUS_POSITIONS = 8  # Legacy rule from DL #16


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


def _apply_trade_budget(
    *,
    run_dir: Path,
    k_per_cycle: int,
    min_score: float,
    max_simultaneous: int,
) -> None:
    """Trade-selection layer per docs/AGENT4_5_REDESIGN.md.

    Reads cell_results.parquet (which contains Agent 5's per-cell
    conviction_score), groups by fiscal_quarter_end, sorts each group
    descending by score, picks top K, and overrides decisions for cells
    outside the top K to no_trade. Preserves the raw Agent 5 output in
    a sidecar `cell_results_pre_budget.parquet` for audit.

    The 8-position simultaneous cap is enforced AFTER per-cycle selection:
    if multiple cycles would have overlapping holding windows that exceed
    8 concurrent positions, the lowest-score positions are dropped.
    """
    cell_path = run_dir / "strategy_01" / "cell_results.parquet"
    if not cell_path.exists():
        return

    df = pd.read_parquet(cell_path)
    if "conviction_score" not in df.columns or len(df) == 0:
        # Old runs without scores or empty parquets — skip trade budget.
        return

    # Save the raw (pre-budget) snapshot so the budget can be re-applied later
    # with different K without losing Agent 5's original outputs.
    sidecar = run_dir / "strategy_01" / "cell_results_pre_budget.parquet"
    if not sidecar.exists():
        df.to_parquet(sidecar, index=False)

    # Group by fiscal_quarter_end (one budget cycle per earnings quarter)
    df["_score"] = df["conviction_score"].fillna(-1.0)
    df["_rank_in_cycle"] = (
        df.groupby("fiscal_quarter_end")["_score"]
          .rank(method="first", ascending=False)
    )
    in_top_k = df["_rank_in_cycle"] <= k_per_cycle
    above_threshold = df["_score"] >= min_score
    eligible = in_top_k & above_threshold

    # Per-cell override: any cell that isn't eligible becomes no_trade
    n_overridden = 0
    for idx in df.index:
        if not eligible[idx]:
            if df.at[idx, "decision"] == "long":
                n_overridden += 1
            df.at[idx, "decision"] = "no_trade"
            df.at[idx, "conviction_tier"] = "none"
            df.at[idx, "final_size_pct"] = 0.0

    # Simultaneous-position cap (8): for cells that survived the per-cycle
    # filter, sort by entry date and drop overlapping ones beyond the cap.
    long_cells = df[df["decision"] == "long"].copy()
    if len(long_cells) > 0 and "decision_date_T" in long_cells.columns:
        long_cells = long_cells.sort_values(
            ["decision_date_T", "_score"], ascending=[True, False]
        )
        # Approximate exit date as decision_date_T + 30 days (T-14 to T+~14
        # given typical earnings cycle); good enough for overlap detection.
        for idx in long_cells.index:
            entry = pd.to_datetime(long_cells.at[idx, "decision_date_T"])
            window_open = entry
            window_close = entry + pd.Timedelta(days=30)
            # Count concurrently open longs at this point
            concurrent = (
                (pd.to_datetime(long_cells["decision_date_T"]) >= window_open
                 - pd.Timedelta(days=30))
                & (pd.to_datetime(long_cells["decision_date_T"]) <= window_close)
                & (long_cells.index <= idx)
                & (long_cells["decision"] == "long")
            ).sum()
            if concurrent > max_simultaneous:
                # Drop this position
                long_cells.at[idx, "decision"] = "no_trade"
                long_cells.at[idx, "conviction_tier"] = "none"
                long_cells.at[idx, "final_size_pct"] = 0.0
                df.at[idx, "decision"] = "no_trade"
                df.at[idx, "conviction_tier"] = "none"
                df.at[idx, "final_size_pct"] = 0.0
                n_overridden += 1

    df = df.drop(columns=["_score", "_rank_in_cycle"])
    df.to_parquet(cell_path, index=False)

    n_long_final = int((df["decision"] == "long").sum())
    print(
        f"[trade-budget] K_PER_CYCLE={k_per_cycle}, min_score={min_score}, "
        f"max_simultaneous={max_simultaneous}: "
        f"{n_overridden} cells overridden to no_trade; "
        f"{n_long_final} long trades remain after budget"
    )


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

    # Apply the trade-selection layer (Agent 4+5 redesign): for Strategy 1,
    # read the per-cell parquet (which now includes Agent 5's conviction_score),
    # group by earnings cycle, pick top K_PER_CYCLE cells per cycle, and
    # override decisions in place. Strategies 2-10 don't use the multi-agent
    # pipeline so the budget layer is a no-op for them.
    if strategy == 1:
        _apply_trade_budget(
            run_dir=run_dir,
            k_per_cycle=TRADE_BUDGET_K_PER_CYCLE,
            min_score=TRADE_BUDGET_MIN_SCORE,
            max_simultaneous=MAX_SIMULTANEOUS_POSITIONS,
        )
        # After budget application, re-read cell_results.parquet (which has the
        # FINAL post-budget decisions) and rebuild the summary from it. This
        # keeps cell_results_summary.parquet consistent with cell_results.parquet.
        post_budget = run_dir / "strategy_01" / "cell_results.parquet"
        if post_budget.exists():
            pb_df = pd.read_parquet(post_budget)
            cell_records = pb_df[
                ["ticker", "fiscal_quarter_end", "decision_date_T",
                 "decision", "final_size_pct"]
            ].rename(columns={"decision": "direction", "final_size_pct": "size_pct"}).to_dict("records")

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
