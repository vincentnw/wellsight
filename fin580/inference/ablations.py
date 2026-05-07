"""M6/M7 ablation + confusion-matrix comparison tables (spec Section 7).

Compares Strategy 1 metrics across:
- M6 confusion-matrix sweep: target vs optimistic vs pessimistic
- M7 ablations: alpha=0 (no satellite weight), no_satellite (Agent 1 emits idle)

Each row = one variant. Metrics from per-trade P&L using CRSP+Yahoo prices.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from fin580.backtest.pnl_engine import compute_trade_pnl
from fin580.data.crsp_loader import load_combined, price_at
from fin580.inference.bootstrap import primary_test
from fin580.inference.pnl import _earnings_dates, _exit_price, strategy_metrics

RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"

VARIANTS = [
    ("baseline_target", "2026-04-29-strategy1-2021Q1_2025Q4-target"),
    ("cm_optimistic", "2026-04-29-strategy1-2021Q1_2025Q4-optimistic"),
    ("cm_pessimistic", "2026-04-29-strategy1-2021Q1_2025Q4-pessimistic"),
    ("alpha0", "2026-04-29-strategy1-2021Q1_2025Q4-target-alpha0"),
    ("no_satellite", "2026-04-29-strategy1-2021Q1_2025Q4-target-nosat"),
]


def _load_variant_trades(run_dir_name: str) -> pd.DataFrame:
    run_dir = RUNS_DIR / run_dir_name
    cell_path = run_dir / "strategy_01" / "cell_results.parquet"
    if not cell_path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(cell_path)
    longs = df[df["decision"] == "long"].copy()
    if len(longs) == 0:
        return pd.DataFrame()

    crsp = load_combined()
    eds = _earnings_dates()
    rows = []
    for _, r in longs.iterrows():
        ticker = r["ticker"]
        fpe = datetime.strptime(r["fiscal_quarter_end"], "%Y-%m-%d").date()
        T_str = r.get("decision_date_T")
        if T_str:
            T = datetime.strptime(T_str, "%Y-%m-%d").date() if isinstance(T_str, str) else T_str
        else:
            T = None
        size = float(r.get("final_size_pct", r.get("size_pct", 0.10)))
        ed = eds.get((ticker, fpe))
        if ed is None or T is None:
            continue
        series = crsp.get(ticker, [])
        if not series:
            continue
        entry_p = price_at(series, T)
        exit_p = _exit_price(series, ed, days_after=2)
        if entry_p is None or exit_p is None:
            continue
        pnl = compute_trade_pnl(
            entry_price=entry_p, exit_price=exit_p, size_pct=size,
            capital_usd=1_000_000, cost_bps=30,
        )
        rows.append({
            "ticker": ticker,
            "fiscal_quarter_end": fpe.isoformat(),
            "entry_date_T": T.isoformat(),
            "size_pct": size,
            "gross_return_pct": pnl["gross_return_pct"],
            "net_return_pct": pnl["net_return_pct"],
        })
    return pd.DataFrame(rows)


def _variant_status(run_dir_name: str) -> dict:
    """How many cells, completed, still erroring."""
    run_dir = RUNS_DIR / run_dir_name
    cell_path = run_dir / "strategy_01" / "cell_results.parquet"
    if not cell_path.exists():
        return {"n_cells_total": 0, "n_long": 0, "n_no_trade": 0, "n_error": 0}
    df = pd.read_parquet(cell_path)
    error_mask = df["error"].notna() & (df["error"].astype(str) != "")
    return {
        "n_cells_total": len(df),
        "n_long": int((df["decision"] == "long").sum()),
        "n_no_trade": int((df["decision"] == "no_trade").sum()),
        "n_error": int(error_mask.sum()),
    }


def build_ablation_table() -> pd.DataFrame:
    rows = []
    for variant, run_dir_name in VARIANTS:
        trades = _load_variant_trades(run_dir_name)
        m = strategy_metrics(trades) if len(trades) else {
            "n_trades": 0, "hit_rate": None, "mean_net_return_pct": None,
            "median_net_return_pct": None, "sharpe_quarterly": None,
            "max_drawdown_pct": None,
        }
        if len(trades) >= 5:
            pt = primary_test(trades, n_iter=1000, seed=0)
            m["primary_p_one_sided"] = pt["p_value_one_sided"]
            m["primary_reject_50"] = pt["reject_50"]
            ci = pt["ci_95"]
            m["hit_rate_ci_low"] = ci[0] if ci else None
            m["hit_rate_ci_high"] = ci[1] if ci else None
        else:
            m["primary_p_one_sided"] = None
            m["primary_reject_50"] = None
            m["hit_rate_ci_low"] = None
            m["hit_rate_ci_high"] = None
        m["variant"] = variant
        m.update(_variant_status(run_dir_name))
        rows.append(m)
    cols = [
        "variant", "n_cells_total", "n_long", "n_no_trade", "n_error",
        "n_trades", "hit_rate", "hit_rate_ci_low", "hit_rate_ci_high",
        "primary_p_one_sided", "primary_reject_50",
        "mean_net_return_pct", "median_net_return_pct",
        "sharpe_quarterly", "max_drawdown_pct",
    ]
    return pd.DataFrame(rows)[cols]


if __name__ == "__main__":
    out_dir = RUNS_DIR / "inference"
    out_dir.mkdir(exist_ok=True)
    tbl = build_ablation_table()
    tbl.to_parquet(out_dir / "ablation_table.parquet")
    tbl.to_csv(out_dir / "ablation_table.csv", index=False)
    print(tbl.to_string(index=False))
    print(f"\nWrote {out_dir / 'ablation_table.csv'}")
