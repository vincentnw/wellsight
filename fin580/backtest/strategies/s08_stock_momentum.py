"""Strategy 8 — Cross-sectional 12-1 momentum baseline.

Long the 4 names with highest trailing 12-1-month total return at T-14.
Equal-weighted within the top-4 selection at 10% per name."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from fin580.agents.schemas import TradeDecision
from fin580.data.crsp_loader import load_combined, trailing_return

UNIVERSE = ["FANG", "EOG", "DVN", "CTRA", "OXY", "MTDR", "PR", "OVV", "SM", "CRGY"]


def _rank_at_T(decision_date_T: date) -> dict[str, float]:
    """12-1 momentum = return from T-14-12mo to T-14-1mo, per ticker."""
    series_by_t = load_combined()
    out: dict[str, float] = {}
    for t in UNIVERSE:
        s = series_by_t.get(t, [])
        if not s:
            continue
        # 12-1: skip the most recent month, look back 12 months
        end = decision_date_T - timedelta(days=30)
        ret = trailing_return(s, end, lookback_days=11 * 30)
        if ret is not None:
            out[t] = ret
    return out


def signal(
    *,
    ticker: str,
    fiscal_quarter_end: date,
    decision_date_T: date,
    **_,
) -> TradeDecision:
    ranks = _rank_at_T(decision_date_T)
    if not ranks or ticker not in ranks:
        return TradeDecision(
            ticker=ticker, decision_date_T=decision_date_T,
            direction="no_trade", size_pct=0.0,
        )
    sorted_tickers = sorted(ranks.items(), key=lambda kv: -kv[1])
    top_4 = {t for t, _ in sorted_tickers[:4]}
    if ticker in top_4:
        return TradeDecision(
            ticker=ticker, decision_date_T=decision_date_T,
            direction="long", size_pct=0.10,
        )
    return TradeDecision(
        ticker=ticker, decision_date_T=decision_date_T,
        direction="no_trade", size_pct=0.0,
    )
