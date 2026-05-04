"""Diagnostic-only signal-confidence score for Strategy 1 cells.

This is **annotation, not signal**. The score does not change H1, trade
eligibility, sizing, or any pre-registered test. It exists so that readers of
the per-cell diagnostics can see, alongside Agent 3's binary divergence class,
how well-supported the underlying inputs were.

Composite is 0-100, built from five 0-20 sub-scores on inputs already exposed
by `revenue_diagnostics.py`:

  1. SAR activity strength      (share_active)
  2. SAR signal newness         (n_newly_active / absolute_active)
  3. SAR qoq activity delta     (relative_activity_delta)
  4. Consensus tightness        (1 / (consensus_dispersion / consensus_median))
  5. Analyst panel breadth      (n_analysts_at_T_minus_14)

WTI / market regime is intentionally NOT in this score; it lives in v2.4 as a
separate portfolio-construction veto so the two layers do not double-count.

The score is written to `runs/inference/signal_confidence.csv` and a small
summary lands in `evidence_pack.json` under `signal_confidence_summary`.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd


def _bin_score(value: float | None, edges: list[float], scores: list[float]) -> float:
    """Discrete tier scorer. `edges` are the upper bounds of each tier (last
    bin is open-ended). Returns the matching score, or the midpoint of the
    range if value is missing/NaN.
    """
    if value is None or pd.isna(value):
        return float(sum(scores)) / len(scores) / 2.0  # neutral fallback
    for edge, s in zip(edges, scores[:-1]):
        if value <= edge:
            return float(s)
    return float(scores[-1])


def _activity_strength_score(share_active: float | None) -> float:
    # Higher share of sampled pads active → stronger signal. 5/5 active = 20.
    return _bin_score(
        share_active,
        edges=[0.0, 0.20, 0.40, 0.60, 0.80],
        scores=[0, 4, 8, 12, 16, 20],
    )


def _newness_score(n_newly: float | None, n_active: float | None) -> float:
    # Newly-active pads (genuine new drilling) carry more forward signal than
    # continuously-active pads. Score is share-of-active-that-is-new.
    if n_active is None or pd.isna(n_active) or n_active == 0:
        return 10.0  # neutral when nothing is active
    if n_newly is None or pd.isna(n_newly):
        return 10.0
    share_new = n_newly / n_active
    return _bin_score(
        share_new,
        edges=[0.0, 0.20, 0.40, 0.60, 0.80],
        scores=[0, 4, 8, 12, 16, 20],
    )


def _qoq_delta_score(rel_delta: float | None) -> float:
    # QoQ activity delta. Positive deltas (acceleration) score higher.
    return _bin_score(
        rel_delta,
        edges=[-0.5, 0.0, 0.5, 1.0, 1.5],
        scores=[0, 4, 8, 12, 16, 20],
    )


def _dispersion_score(disp_usd: float | None, med_usd: float | None) -> float:
    # Lower coefficient-of-dispersion → tighter analyst consensus → score higher.
    if (
        disp_usd is None or med_usd is None
        or pd.isna(disp_usd) or pd.isna(med_usd) or med_usd == 0
    ):
        return 10.0
    cov = abs(disp_usd) / abs(med_usd)
    return _bin_score(
        cov,
        edges=[0.02, 0.05, 0.10, 0.20, 0.40],
        scores=[20, 16, 12, 8, 4, 0],  # inverted: lower CoV → higher score
    )


def _analyst_breadth_score(n_analysts: float | None) -> float:
    return _bin_score(
        n_analysts,
        edges=[3, 6, 10, 15, 20],
        scores=[0, 4, 8, 12, 16, 20],
    )


def _tier_label(score: float) -> str:
    if score >= 70: return "high"
    if score >= 40: return "medium"
    return "low"


def attach_signal_confidence(diag: pd.DataFrame) -> pd.DataFrame:
    """Append signal_confidence_score (0-100) and tier columns to a copy of
    the revenue_diagnostics frame. Pure post-processing — no I/O, no model.
    """
    if diag.empty:
        return diag

    out = diag.copy()
    out["sc_activity_strength"] = out["share_active"].apply(_activity_strength_score)
    out["sc_newness"] = [
        _newness_score(n, a)
        for n, a in zip(out["n_newly_active"], out["absolute_active"])
    ]
    out["sc_qoq_delta"] = out["relative_activity_delta"].apply(_qoq_delta_score)
    out["sc_dispersion"] = [
        _dispersion_score(d, m)
        for d, m in zip(out["consensus_dispersion_usd"], out["consensus_median_usd"])
    ]
    out["sc_analyst_breadth"] = out["n_analysts_at_T_minus_14"].apply(
        _analyst_breadth_score
    )
    out["signal_confidence_score"] = (
        out["sc_activity_strength"]
        + out["sc_newness"]
        + out["sc_qoq_delta"]
        + out["sc_dispersion"]
        + out["sc_analyst_breadth"]
    )
    out["signal_confidence_tier"] = out["signal_confidence_score"].apply(_tier_label)
    return out


def signal_confidence_summary(diag_with_sc: pd.DataFrame) -> dict:
    """Compact summary for evidence_pack.json. Diagnostic, no headline value."""
    if diag_with_sc.empty or "signal_confidence_score" not in diag_with_sc.columns:
        return {"n_cells": 0, "generated_at": datetime.now().isoformat()}

    scores = diag_with_sc["signal_confidence_score"]
    longs = diag_with_sc[diag_with_sc["decision"] == "long"]
    long_scores = longs["signal_confidence_score"]

    win_by_tier = {}
    if "trade_win" in longs.columns and len(longs):
        for tier, grp in longs.groupby("signal_confidence_tier"):
            wins = grp["trade_win"].dropna()
            if len(wins):
                win_by_tier[str(tier)] = {
                    "n_trades": int(len(wins)),
                    "win_rate": float(wins.astype(float).mean()),
                }

    return {
        "n_cells": int(len(diag_with_sc)),
        "score_mean_all_cells": float(scores.mean()),
        "score_mean_long_trades": float(long_scores.mean()) if len(long_scores) else None,
        "tier_counts_all_cells": {
            k: int(v) for k, v in
            diag_with_sc["signal_confidence_tier"].value_counts().to_dict().items()
        },
        "tier_counts_long_trades": {
            k: int(v) for k, v in
            longs["signal_confidence_tier"].value_counts().to_dict().items()
        } if len(longs) else {},
        "long_trade_win_rate_by_tier": win_by_tier,
        "scope": "diagnostic_only",
        "generated_at": datetime.now().isoformat(),
    }
