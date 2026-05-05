"""Revenue-mechanism diagnostics for Strategy 1.

These diagnostics are instrumentation only: they explain whether Agent 2's
satellite-adjusted revenue forecast lined up with actual reported revenue.
They do not change the H1 headline metric, trade eligibility, or sizing.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from fin580.inference.pnl import (
    RUNS_DIR,
    PHASE1_OUTPUT,
    STRATEGY1_YEARLY_RUNS,
    compute_pnl_strategy1_combined,
)


def _load_strategy1_cells() -> pd.DataFrame:
    parts = []
    for run_name in STRATEGY1_YEARLY_RUNS:
        p = RUNS_DIR / run_name / "strategy_01" / "cell_results.parquet"
        if p.exists():
            df = pd.read_parquet(p)
            df["run_id"] = run_name
            parts.append(df)
    if not parts:
        return pd.DataFrame()
    return (
        pd.concat(parts, ignore_index=True)
        .drop_duplicates(subset=["ticker", "fiscal_quarter_end"], keep="last")
        .sort_values(["fiscal_quarter_end", "ticker"])
        .reset_index(drop=True)
    )


def _load_actual_revenue() -> pd.DataFrame:
    p = PHASE1_OUTPUT / "compustat_fundq.csv"
    if not p.exists():
        return pd.DataFrame(columns=["ticker", "fiscal_quarter_end", "actual_revenue_usd"])
    df = pd.read_csv(p)
    out = df[["tic", "datadate", "saleq"]].copy()
    out = out.rename(
        columns={
            "tic": "ticker",
            "datadate": "fiscal_quarter_end",
            "saleq": "actual_revenue_usd_m",
        }
    )
    out["actual_revenue_usd"] = out["actual_revenue_usd_m"] * 1_000_000.0
    return out[["ticker", "fiscal_quarter_end", "actual_revenue_usd"]]


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def _agent_outputs(row: pd.Series) -> dict:
    base = f"{row['ticker']}_{row['fiscal_quarter_end']}"
    out_dir = RUNS_DIR / row["run_id"] / "strategy_01" / "agent_outputs"
    a1 = _read_json(out_dir / f"{base}_agent1.json")
    a2 = _read_json(out_dir / f"{base}_agent2.json")
    a3 = _read_json(out_dir / f"{base}_agent3.json")

    components = a2.get("components", {}) if isinstance(a2.get("components"), dict) else {}
    return {
        "n_newly_active": a1.get("n_newly_active"),
        "n_continuously_active": a1.get("n_continuously_active"),
        "n_idle": a1.get("n_idle"),
        "absolute_active": a1.get("absolute_active"),
        "share_active": a1.get("share_active"),
        "relative_activity_delta": a1.get("relative_activity_delta"),
        "revenue_forecast_usd": a2.get("revenue_forecast_usd"),
        "alpha": components.get("alpha"),
        "drilling_signal_raw": components.get("drilling_signal_raw"),
        "drilling_signal_clipped": components.get("drilling_signal_clipped"),
        "consensus_median_usd": a3.get("consensus_median_usd"),
        "consensus_dispersion_usd": a3.get("consensus_dispersion_usd"),
        "n_analysts_at_T_minus_14": a3.get("n_analysts_at_T_minus_14"),
        "forecast_divergence_pct": a3.get("divergence_pct"),
        "divergence_class": a3.get("divergence_class"),
        "agent3_confidence": a3.get("confidence"),
    }


def _forecast_direction(divergence_class: str | None) -> str | None:
    if divergence_class in ("modest_beat", "strong_beat"):
        return "beat"
    if divergence_class in ("modest_miss", "strong_miss"):
        return "miss"
    if divergence_class == "in_line":
        return "in_line"
    return None


def build_revenue_diagnostics() -> pd.DataFrame:
    """Build per-cell revenue diagnostics for the canonical Strategy 1 window."""
    cells = _load_strategy1_cells()
    if cells.empty:
        return pd.DataFrame()

    agent_rows = []
    for _, row in cells.iterrows():
        agent_rows.append(_agent_outputs(row))
    diag = pd.concat([cells.reset_index(drop=True), pd.DataFrame(agent_rows)], axis=1)
    diag = diag.merge(
        _load_actual_revenue(),
        on=["ticker", "fiscal_quarter_end"],
        how="left",
    )

    consensus = pd.to_numeric(diag["consensus_median_usd"], errors="coerce")
    actual = pd.to_numeric(diag["actual_revenue_usd"], errors="coerce")
    diag["actual_surprise_pct"] = (actual - consensus) / consensus * 100.0
    valid_actual = actual.notna() & consensus.notna() & (consensus != 0)
    diag["actual_revenue_beat"] = pd.Series(pd.NA, index=diag.index, dtype="boolean")
    diag.loc[valid_actual, "actual_revenue_beat"] = (
        actual[valid_actual] > consensus[valid_actual]
    ).astype("boolean")

    diag["forecast_direction"] = diag["divergence_class"].map(_forecast_direction)
    diag["actual_direction"] = diag["actual_revenue_beat"].map(
        {True: "beat", False: "miss"}
    )
    valid_direction = (
        diag["forecast_direction"].notna()
        & (diag["forecast_direction"] != "in_line")
        & diag["actual_direction"].notna()
    )
    diag["revenue_direction_correct"] = pd.Series(pd.NA, index=diag.index, dtype="boolean")
    diag.loc[valid_direction, "revenue_direction_correct"] = (
        diag.loc[valid_direction, "forecast_direction"]
        == diag.loc[valid_direction, "actual_direction"]
    ).astype("boolean")

    trades = compute_pnl_strategy1_combined()
    if len(trades):
        trade_cols = [
            "ticker", "fiscal_quarter_end", "entry_price", "exit_price",
            "gross_return_pct", "net_return_pct", "net_pnl_usd",
        ]
        diag = diag.merge(
            trades[trade_cols],
            on=["ticker", "fiscal_quarter_end"],
            how="left",
        )
        valid_trade = diag["net_return_pct"].notna()
        diag["trade_win"] = pd.Series(pd.NA, index=diag.index, dtype="boolean")
        diag.loc[valid_trade, "trade_win"] = (
            diag.loc[valid_trade, "net_return_pct"] > 0
        ).astype("boolean")
    else:
        diag["trade_win"] = pd.NA

    ordered_cols = [
        "ticker", "fiscal_quarter_end", "decision_date_T", "decision",
        "conviction_tier", "final_size_pct", "low_quality_flag", "run_id",
        "n_newly_active", "n_continuously_active", "n_idle", "absolute_active",
        "share_active", "relative_activity_delta", "drilling_signal_raw",
        "drilling_signal_clipped", "alpha", "revenue_forecast_usd",
        "consensus_median_usd", "consensus_dispersion_usd",
        "n_analysts_at_T_minus_14", "forecast_divergence_pct",
        "divergence_class", "agent3_confidence", "actual_revenue_usd",
        "actual_surprise_pct", "actual_revenue_beat", "forecast_direction",
        "actual_direction", "revenue_direction_correct", "entry_price",
        "exit_price", "gross_return_pct", "net_return_pct", "net_pnl_usd",
        "trade_win", "error",
    ]
    existing = [c for c in ordered_cols if c in diag.columns]
    return diag[existing].reset_index(drop=True)


def revenue_diagnostic_summary(diag: pd.DataFrame) -> dict:
    """Small summary for evidence_pack.json, kept separate from H1 metrics."""
    if diag.empty:
        return {
            "n_cells": 0,
            "n_cells_with_actual_and_consensus": 0,
            "n_long_trades_with_actual": 0,
            "long_trade_actual_revenue_beat_rate": None,
            "long_trade_win_rate_when_actual_revenue_beat": None,
            "generated_at": datetime.now().isoformat(),
        }

    valid = diag.dropna(subset=["actual_revenue_beat", "consensus_median_usd"])
    longs = valid[valid["decision"] == "long"]
    long_beats = longs[longs["actual_revenue_beat"] == True]
    beat_rate = float(longs["actual_revenue_beat"].mean()) if len(longs) else None
    win_when_beat = float(long_beats["trade_win"].mean()) if len(long_beats) else None
    direction_valid = valid.dropna(subset=["revenue_direction_correct"])
    return {
        "n_cells": int(len(diag)),
        "n_cells_with_actual_and_consensus": int(len(valid)),
        "n_long_trades_with_actual": int(len(longs)),
        "long_trade_actual_revenue_beat_rate": beat_rate,
        "long_trade_win_rate_when_actual_revenue_beat": win_when_beat,
        "diagnostic_revenue_direction_accuracy_non_neutral": (
            float(direction_valid["revenue_direction_correct"].mean())
            if len(direction_valid) else None
        ),
        "generated_at": datetime.now().isoformat(),
    }
