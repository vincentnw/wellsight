"""Strategy 5 — Baker Hughes Permian basin rig count baseline.

Long the equal-weighted universe when 4-week-on-4-week Permian rig count
change at T-14 is positive."""

from __future__ import annotations

from datetime import date, timedelta

from fin580.agents.schemas import TradeDecision
from fin580.data.bhi_loader import avg_rigs_window


def signal(
    *,
    ticker: str,
    fiscal_quarter_end: date,
    decision_date_T: date,
    **_,
) -> TradeDecision:
    cur = avg_rigs_window(decision_date_T - timedelta(days=28), decision_date_T)
    prior = avg_rigs_window(
        decision_date_T - timedelta(days=56),
        decision_date_T - timedelta(days=28),
    )
    if cur == 0 or prior == 0:
        return TradeDecision(
            ticker=ticker, decision_date_T=decision_date_T,
            direction="no_trade", size_pct=0.0,
        )
    rising = cur > prior
    return TradeDecision(
        ticker=ticker, decision_date_T=decision_date_T,
        direction="long" if rising else "no_trade",
        size_pct=0.10 if rising else 0.0,
    )
