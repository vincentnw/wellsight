"""Strategy 7 — XLE buy-and-hold benchmark.

Always returns no_trade for individual names (the portfolio is 100% XLE held
continuously, computed at the P&L aggregation layer rather than per-cell)."""

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
    # Strategy 7 doesn't operate at the per-cell level; it's a buy-hold of
    # XLE for the whole window. Return no_trade for every cell. The P&L
    # engine knows to compute Strategy 7's return separately from per-cell
    # signals (XLE total return Q1 2021 -> Q4 2025 with monthly rebalance).
    return TradeDecision(
        ticker=ticker, decision_date_T=decision_date_T,
        direction="no_trade", size_pct=0.0,
    )
