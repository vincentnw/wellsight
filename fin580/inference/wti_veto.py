"""WTI stress-veto sensitivity for Strategy 1.

This module implements a portfolio-construction sensitivity only. It does not
change the canonical H1 ledger, trade eligibility, Agent 3 gate, or sizing.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from fin580.inference.bootstrap import firm_clustered_bootstrap, primary_test
from fin580.inference.pnl import PHASE1_OUTPUT, strategy_metrics

WTI_PATH = PHASE1_OUTPUT / "eia_wti_weekly.csv"
WTI_VETO_THRESHOLD = -0.10


def _load_wti(path: Path = WTI_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    return df


def _latest_wti_on_or_before(wti: pd.DataFrame, target: pd.Timestamp) -> pd.Series | None:
    rows = wti[wti["date"] <= target]
    if rows.empty:
        return None
    return rows.iloc[-1]


def wti_4w_return_at_T(
    entry_date_T: str | pd.Timestamp,
    *,
    wti: pd.DataFrame | None = None,
) -> dict:
    """Return point-in-time 4-week WTI return and as-of metadata."""
    if wti is None:
        wti = _load_wti()
    t = pd.Timestamp(entry_date_T)
    cur = _latest_wti_on_or_before(wti, t)
    prev = _latest_wti_on_or_before(wti, t - pd.Timedelta(days=28))
    if cur is None or prev is None or prev["wti_usd_per_bbl"] == 0:
        return {
            "wti_asof_date": None,
            "wti_asof": None,
            "wti_prev_date": None,
            "wti_prev": None,
            "wti_4w_return_pct": None,
            "wti_veto": False,
            "wti_veto_reason": "wti_unavailable",
        }
    ret = float(cur["wti_usd_per_bbl"] / prev["wti_usd_per_bbl"] - 1.0)
    veto = ret <= WTI_VETO_THRESHOLD
    return {
        "wti_asof_date": cur["date"].date().isoformat(),
        "wti_asof": float(cur["wti_usd_per_bbl"]),
        "wti_prev_date": prev["date"].date().isoformat(),
        "wti_prev": float(prev["wti_usd_per_bbl"]),
        "wti_4w_return_pct": ret * 100.0,
        "wti_veto": bool(veto),
        "wti_veto_reason": (
            "wti_4w_return_le_minus_10pct" if veto else "no_stress_veto"
        ),
    }


def apply_wti_veto(trades: pd.DataFrame) -> pd.DataFrame:
    """Annotate canonical Strategy 1 long trades and zero out vetoed rows."""
    if trades.empty:
        return trades.copy()
    wti = _load_wti()
    rows = []
    for _, trade in trades.iterrows():
        meta = wti_4w_return_at_T(trade["entry_date_T"], wti=wti)
        row = trade.to_dict()
        row.update(meta)
        row["baseline_net_return_pct"] = row.get("net_return_pct")
        row["baseline_net_pnl_usd"] = row.get("net_pnl_usd")
        if meta["wti_veto"]:
            row["direction_after_veto"] = "no_trade"
            row["size_pct_after_veto"] = 0.0
            row["gross_return_pct"] = 0.0
            row["net_return_pct"] = 0.0
            row["gross_pnl_usd"] = 0.0
            row["net_pnl_usd"] = 0.0
        else:
            row["direction_after_veto"] = "long"
            row["size_pct_after_veto"] = row.get("size_pct")
        rows.append(row)
    return pd.DataFrame(rows)


def kept_trade_ledger(veto_ledger: pd.DataFrame) -> pd.DataFrame:
    """Return only post-veto long trades for metrics/bootstrap."""
    if veto_ledger.empty:
        return veto_ledger.copy()
    return veto_ledger[veto_ledger["direction_after_veto"] == "long"].copy()


def wti_veto_summary(
    *,
    baseline_trades: pd.DataFrame,
    veto_ledger: pd.DataFrame,
) -> dict:
    kept = kept_trade_ledger(veto_ledger)
    baseline_metrics = strategy_metrics(baseline_trades)
    veto_metrics = strategy_metrics(kept)
    blocked = veto_ledger[veto_ledger.get("wti_veto", False) == True]
    primary = primary_test(kept, n_iter=1000, seed=0) if len(kept) else {}
    fc_hit = (
        firm_clustered_bootstrap(kept, n_iter=1000, metric="hit_rate", seed=0)
        if len(kept) else {}
    )
    return {
        "scope": "sensitivity_only",
        "threshold_wti_4w_return_pct": WTI_VETO_THRESHOLD * 100.0,
        "baseline_n_trades": int(baseline_metrics["n_trades"]),
        "baseline_hit_rate": baseline_metrics["hit_rate"],
        "baseline_total_net_pnl_usd": (
            float(baseline_trades["net_pnl_usd"].sum()) if len(baseline_trades) else 0.0
        ),
        "post_veto_n_trades": int(veto_metrics["n_trades"]),
        "post_veto_hit_rate": veto_metrics["hit_rate"],
        "post_veto_mean_net_return_pct": veto_metrics["mean_net_return_pct"],
        "post_veto_total_net_pnl_usd": (
            float(kept["net_pnl_usd"].sum()) if len(kept) else 0.0
        ),
        "n_vetoed": int(len(blocked)),
        "vetoed_trades": blocked[
            [
                "ticker",
                "fiscal_quarter_end",
                "entry_date_T",
                "wti_4w_return_pct",
                "baseline_net_pnl_usd",
            ]
        ].to_dict(orient="records") if len(blocked) else [],
        "post_veto_primary_test_H1": {
            "p_value_one_sided": primary.get("p_value_one_sided"),
            "reject_50": primary.get("reject_50"),
            "ci_95": primary.get("ci_95"),
            "n_iter": primary.get("n_iter"),
        },
        "post_veto_firm_clustered_hit_rate_ci": {
            "mean": fc_hit.get("mean"),
            "ci_low": fc_hit.get("ci_low"),
            "ci_high": fc_hit.get("ci_high"),
            "n_iter": fc_hit.get("n_iter"),
        },
        "generated_at": datetime.now().isoformat(),
    }
