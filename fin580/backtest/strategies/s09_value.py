"""Strategy 9 — Value composite baseline.

Long top-4 names by composite z-score of (-EV/EBITDA, -P/B, +FCF yield).
For the design demo, EV is approximated as market cap + total debt - cash;
P/B is approximated using the latest market cap / common equity.
Equal-weight 10% per name."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fin580.agents.schemas import TradeDecision
from fin580.data.compustat_loader import latest_at_T, load_fundq
from fin580.data.crsp_loader import load_combined, price_at

UNIVERSE = ["FANG", "EOG", "DVN", "CTRA", "OXY", "MTDR", "PR", "OVV", "SM", "CRGY"]

# Approximate shares outstanding (millions) per ticker for market-cap estimate.
# Defaults; fine for design-demo magnitude work.
SHARES_OUTSTANDING_M = {
    "FANG": 290, "EOG": 580, "DVN": 660, "CTRA": 740, "OXY": 940,
    "MTDR": 125, "PR": 800, "OVV": 270, "SM": 115, "CRGY": 220,
}


def _zscore(values: list[float]) -> list[float]:
    if not values or len(values) < 2:
        return [0.0] * len(values)
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    std = var ** 0.5
    if std == 0:
        return [0.0] * len(values)
    return [(v - mean) / std for v in values]


def _composite_at_T(decision_date_T: date) -> dict[str, float]:
    fundq = load_fundq()
    crsp = load_combined()
    raw: dict[str, dict] = {}
    for t in UNIVERSE:
        rows = fundq.get(t, [])
        latest = latest_at_T(rows, decision_date_T)
        if latest is None:
            continue
        prc = price_at(crsp.get(t, []), decision_date_T)
        if prc is None or prc <= 0:
            continue
        market_cap = prc * SHARES_OUTSTANDING_M.get(t, 200) * 1e6
        ebitda = latest.get("oibdpq")  # quarterly
        if not ebitda or ebitda <= 0:
            continue
        debt = (latest.get("dlttq") or 0) + (latest.get("dlcq") or 0)
        cash = latest.get("cheq") or 0
        ev = market_cap + debt * 1e6 - cash * 1e6
        ev_ebitda = ev / (ebitda * 4 * 1e6) if ebitda * 4 > 0 else None
        ceqq = latest.get("ceqq")
        pb = (market_cap / (ceqq * 1e6)) if ceqq and ceqq > 0 else None
        ocf = latest.get("oancfy")  # YTD; use as proxy for trailing
        capx = latest.get("capxy")
        fcf = (ocf or 0) - (capx or 0)
        fcf_yield = (fcf * 1e6 / market_cap) if market_cap else None
        if ev_ebitda is None or pb is None or fcf_yield is None:
            continue
        raw[t] = {"ev_ebitda": ev_ebitda, "pb": pb, "fcf_yield": fcf_yield}

    if len(raw) < 2:
        return {}

    tickers = list(raw.keys())
    ev_ebitdas = [-raw[t]["ev_ebitda"] for t in tickers]   # invert (lower is better)
    pbs = [-raw[t]["pb"] for t in tickers]
    fcfs = [raw[t]["fcf_yield"] for t in tickers]
    z1 = _zscore(ev_ebitdas)
    z2 = _zscore(pbs)
    z3 = _zscore(fcfs)
    composite = {tickers[i]: (z1[i] + z2[i] + z3[i]) / 3 for i in range(len(tickers))}
    return composite


def signal(
    *,
    ticker: str,
    fiscal_quarter_end: date,
    decision_date_T: date,
    **_,
) -> TradeDecision:
    ranks = _composite_at_T(decision_date_T)
    if ticker not in ranks:
        return TradeDecision(
            ticker=ticker, decision_date_T=decision_date_T,
            direction="no_trade", size_pct=0.0,
        )
    top_4 = {t for t, _ in sorted(ranks.items(), key=lambda kv: -kv[1])[:4]}
    if ticker in top_4:
        return TradeDecision(
            ticker=ticker, decision_date_T=decision_date_T,
            direction="long", size_pct=0.10,
        )
    return TradeDecision(
        ticker=ticker, decision_date_T=decision_date_T,
        direction="no_trade", size_pct=0.0,
    )
