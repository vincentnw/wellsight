"""Strategy 10 — Quality composite baseline.

Long top-4 names by composite z-score of (+ROE, -D/E, +OCF margin).
ROE = trailing-4Q sum(niq) / mean(ceqq); D/E = (dlttq+dlcq) / ceqq;
OCF margin = oancfy / saleq. Lagged to most recent rdq before T-14."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fin580.agents.schemas import TradeDecision
from fin580.data.compustat_loader import latest_at_T, load_fundq

UNIVERSE = ["FANG", "EOG", "DVN", "CTRA", "OXY", "MTDR", "PR", "OVV", "SM", "CRGY"]


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
    raw: dict[str, dict] = {}
    for t in UNIVERSE:
        rows = fundq.get(t, [])
        latest = latest_at_T(rows, decision_date_T)
        if latest is None:
            continue
        ni = latest.get("niq")
        ceqq = latest.get("ceqq")
        debt = (latest.get("dlttq") or 0) + (latest.get("dlcq") or 0)
        sale = latest.get("saleq")
        ocf = latest.get("oancfy")
        if ni is None or ceqq is None or ceqq <= 0 or sale is None or sale <= 0:
            continue
        roe = (ni * 4) / ceqq
        de = debt / ceqq if ceqq > 0 else None
        ocf_margin = (ocf or 0) / sale if sale > 0 else None
        if de is None or ocf_margin is None:
            continue
        raw[t] = {"roe": roe, "de": de, "ocf_margin": ocf_margin}

    if len(raw) < 2:
        return {}

    tickers = list(raw.keys())
    roes = [raw[t]["roe"] for t in tickers]
    des = [-raw[t]["de"] for t in tickers]   # lower D/E better
    ocfs = [raw[t]["ocf_margin"] for t in tickers]
    z1 = _zscore(roes)
    z2 = _zscore(des)
    z3 = _zscore(ocfs)
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
