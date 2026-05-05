"""Strategy 3 — Analyst-revision follower (deterministic baseline).

Long if 4-week change in IBES median consensus is positive at T-14."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from fin580.agents.schemas import TradeDecision
from fin580.data.ibes_pit import consensus_at_T


def signal(
    *,
    ticker: str,
    fiscal_quarter_end: date,
    decision_date_T: date,
    **_,
) -> TradeDecision:
    cur = consensus_at_T(ticker, fiscal_quarter_end, decision_date_T)
    prior = consensus_at_T(
        ticker, fiscal_quarter_end, decision_date_T - timedelta(days=28)
    )
    if cur["median_usd_m"] is None or prior["median_usd_m"] is None:
        return TradeDecision(
            ticker=ticker, decision_date_T=decision_date_T,
            direction="no_trade", size_pct=0.0,
        )
    revised_up = cur["median_usd_m"] > prior["median_usd_m"]
    return TradeDecision(
        ticker=ticker, decision_date_T=decision_date_T,
        direction="long" if revised_up else "no_trade",
        size_pct=0.10 if revised_up else 0.0,
    )
