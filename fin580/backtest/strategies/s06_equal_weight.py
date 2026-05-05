"""Strategy 6 — Equal-weighted universe baseline.
Always long every eligible name at 10%."""

from __future__ import annotations

from datetime import date

from fin580.agents.schemas import TradeDecision


def signal(
    *,
    ticker: str,
    fiscal_quarter_end: date,
    decision_date_T: date,
    **_,
) -> TradeDecision:
    return TradeDecision(
        ticker=ticker, decision_date_T=decision_date_T,
        direction="long", size_pct=0.10,
    )
