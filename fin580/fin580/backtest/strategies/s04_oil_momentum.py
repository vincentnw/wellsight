"""Strategy 4 — WTI 3-month momentum (deterministic macro baseline).

Long all eligible names when WTI 3-month return at T-14 is positive."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from fin580.agents.schemas import TradeDecision
from fin580.data.wti_loader import avg_wti_window, load_wti


def _wti_at(d: date) -> float | None:
    series = load_wti()
    valid = [(dt, v) for dt, v in series if dt <= d]
    if not valid:
        return None
    return valid[-1][1]


def signal(
    *,
    ticker: str,
    fiscal_quarter_end: date,
    decision_date_T: date,
    **_,
) -> TradeDecision:
    wti_now = _wti_at(decision_date_T)
    wti_3m_ago = _wti_at(decision_date_T - timedelta(days=90))
    if wti_now is None or wti_3m_ago is None or wti_3m_ago == 0:
        return TradeDecision(
            ticker=ticker, decision_date_T=decision_date_T,
            direction="no_trade", size_pct=0.0,
        )
    momentum_pos = wti_now > wti_3m_ago
    return TradeDecision(
        ticker=ticker, decision_date_T=decision_date_T,
        direction="long" if momentum_pos else "no_trade",
        size_pct=0.10 if momentum_pos else 0.0,
    )
