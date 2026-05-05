"""Deterministic point-in-time feature builders for the v2.6 Investment
Committee Brief (Agent 5_brief). Every function returns numerical fields
computed strictly from data observable at the cell's decision date T.
The LLM never computes any of these numbers; it only reads them.

Sections, frozen per docs/v2/v2_6_pre_registration.md:
  - reaction_history: prior earnings reactions for the same ticker
  - fundamentals: Compustat oibdpq/saleq/niq/capex trend (rdq <= T)
  - regime: WTI 4w/12w return, XES 4w return, stock beta to WTI
  - positioning: 3-month momentum, 52-week distance
"""

from __future__ import annotations

import csv
import math
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
EARNINGS_CSV = PHASE1_OUTPUT / "earnings_dates.csv"
COMPUSTAT_CSV = PHASE1_OUTPUT / "compustat_fundq.csv"
BENCHMARK_CSV = PHASE1_OUTPUT / "benchmark_prices.csv"
WTI_CSV = PHASE1_OUTPUT / "eia_wti_weekly.csv"


# ---------------------------------------------------------------------------
# Data loaders (cached at module level)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _earnings_table() -> list[dict]:
    if not EARNINGS_CSV.exists():
        return []
    with open(EARNINGS_CSV) as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def _compustat_table() -> list[dict]:
    if not COMPUSTAT_CSV.exists():
        return []
    with open(COMPUSTAT_CSV) as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def _benchmark_table() -> list[dict]:
    if not BENCHMARK_CSV.exists():
        return []
    with open(BENCHMARK_CSV) as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def _wti_table() -> list[tuple[date, float]]:
    if not WTI_CSV.exists():
        return []
    out: list[tuple[date, float]] = []
    with open(WTI_CSV) as f:
        for r in csv.DictReader(f):
            try:
                d = datetime.strptime(r["date"], "%Y-%m-%d").date()
                v = float(r["wti_usd_per_bbl"])
            except (KeyError, ValueError):
                continue
            out.append((d, v))
    out.sort()
    return out


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _latest_on_or_before(
    series: list[tuple[date, float]], target: date
) -> tuple[date, float] | None:
    """Return the (date, value) row with the latest date <= target, or None."""
    last = None
    for d, v in series:
        if d > target:
            break
        last = (d, v)
    return last


# ---------------------------------------------------------------------------
# Section 1: reaction_history
# ---------------------------------------------------------------------------

def build_reaction_history(
    ticker: str,
    T: date,
    n_priors_max: int = 8,
) -> dict:
    """For the same ticker, summarize prior earnings reactions strictly
    before T. Returns aggregate stats and a list of per-quarter records.
    """
    from fin580.data.crsp_loader import load_combined, price_at

    # 1. Pull prior earnings dates strictly before T
    rows = _earnings_table()
    priors: list[dict] = []
    for r in rows:
        if r.get("ticker") != ticker:
            continue
        ed = _parse_date(r.get("earnings_date_actual"))
        fpe = _parse_date(r.get("fiscal_quarter_end"))
        if ed is None or fpe is None or ed >= T:
            continue
        priors.append({"fpe": fpe, "earnings_date": ed})
    priors.sort(key=lambda x: x["earnings_date"])
    priors = priors[-n_priors_max:]  # most-recent N

    if not priors:
        return {
            "n_priors": 0,
            "data_sufficient": False,
            "priors": [],
        }

    # 2. For each prior earnings, compute 2-trading-day post-earnings return
    crsp = load_combined()
    series = crsp.get(ticker, [])

    def _exit_price_after(
        ts: list[tuple[date, float, float | None]],
        ed: date,
        days_after: int = 2,
    ) -> float | None:
        forward = sorted(d for d, _, _ in ts if d > ed)
        if len(forward) < days_after:
            return None
        return price_at(ts, forward[days_after - 1])

    # 3. Compustat actual revenue (where rdq exists)
    comp = _compustat_table()
    comp_by_key: dict[tuple[str, str], dict] = {}
    for c in comp:
        comp_by_key[(c.get("tic", ""), c.get("datadate", ""))] = c

    enriched: list[dict] = []
    for p in priors:
        fpe = p["fpe"]
        ed = p["earnings_date"]
        # Entry T-14, exit T+2 trading days (same as the primary backtest)
        entry_T = ed - timedelta(days=14)
        entry_p = price_at(series, entry_T) if series else None
        exit_p = _exit_price_after(series, ed) if series else None
        if entry_p is None or exit_p is None or entry_p <= 0:
            ret = None
        else:
            ret = exit_p / entry_p - 1.0

        # PIT consensus revenue at the prior T-14 (uses the existing IBES
        # PIT helper); compare to Compustat actual saleq for that fpe.
        from fin580.data.ibes_pit import consensus_at_T
        cons = consensus_at_T(ticker, fpe, entry_T)
        cons_med_usd = (
            cons.get("median_usd_m") * 1_000_000.0
            if cons.get("median_usd_m") is not None else None
        )
        actual_saleq = comp_by_key.get((ticker, fpe.isoformat()), {}).get("saleq")
        try:
            actual_usd = float(actual_saleq) * 1_000_000.0 if actual_saleq else None
        except (ValueError, TypeError):
            actual_usd = None

        if cons_med_usd is not None and actual_usd is not None:
            beat = bool(actual_usd > cons_med_usd)
            surprise_pct = (actual_usd - cons_med_usd) / cons_med_usd * 100.0
        else:
            beat = None
            surprise_pct = None

        enriched.append({
            "fpe": fpe.isoformat(),
            "earnings_date": ed.isoformat(),
            "two_day_return_pct": (ret * 100.0) if ret is not None else None,
            "revenue_beat": beat,
            "revenue_surprise_pct": surprise_pct,
        })

    # 4. Aggregate
    rets = [r["two_day_return_pct"] for r in enriched if r["two_day_return_pct"] is not None]
    beats = [r for r in enriched if r["revenue_beat"] is True]
    misses = [r for r in enriched if r["revenue_beat"] is False]

    def _mean(xs: list[float]) -> float | None:
        return float(sum(xs) / len(xs)) if xs else None

    def _std(xs: list[float]) -> float | None:
        if len(xs) < 2:
            return None
        m = sum(xs) / len(xs)
        v = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
        return float(math.sqrt(v))

    beat_rets = [r["two_day_return_pct"] for r in beats if r["two_day_return_pct"] is not None]
    miss_rets = [r["two_day_return_pct"] for r in misses if r["two_day_return_pct"] is not None]

    # Cohen's d-style effect size between beat and miss returns
    if beat_rets and miss_rets:
        m_b, m_m = _mean(beat_rets), _mean(miss_rets)
        beat_minus_miss_pct = (m_b or 0) - (m_m or 0)
    else:
        beat_minus_miss_pct = None

    return {
        "n_priors": len(enriched),
        "data_sufficient": len(rets) >= 3,
        "mean_two_day_return_pct": _mean(rets),
        "std_two_day_return_pct": _std(rets),
        "n_revenue_beats": len(beats),
        "n_revenue_misses": len(misses),
        "n_revenue_neutral": len(enriched) - len(beats) - len(misses),
        "mean_return_when_beat_pct": _mean(beat_rets) if beat_rets else None,
        "mean_return_when_miss_pct": _mean(miss_rets) if miss_rets else None,
        "beat_vs_miss_return_gap_pct": beat_minus_miss_pct,
        "priors": enriched,
    }


# ---------------------------------------------------------------------------
# Section 2: fundamentals (Compustat-only; no IBES EPS available)
# ---------------------------------------------------------------------------

def build_fundamentals(ticker: str, T: date, n_quarters: int = 4) -> dict:
    """Last `n_quarters` Compustat quarters where `rdq <= T`. Returns
    operating-margin trend, net-income trend, and capex intensity."""
    rows = _compustat_table()
    matches: list[dict] = []
    for r in rows:
        if r.get("tic") != ticker:
            continue
        rdq = _parse_date(r.get("rdq"))
        if rdq is None or rdq > T:
            continue
        matches.append(r)

    if not matches:
        return {
            "n_quarters": 0,
            "data_sufficient": False,
            "eps_data_available": False,
        }

    # Sort by datadate ascending, take most recent n_quarters
    def _datadate(r: dict) -> date:
        return _parse_date(r.get("datadate")) or date.min
    matches.sort(key=_datadate)
    recent = matches[-n_quarters:]

    quarters: list[dict] = []
    capxy_by_year: dict[int, list[tuple[int, float]]] = {}
    for r in recent:
        try:
            saleq = float(r.get("saleq") or 0) or None
            oibdpq = float(r.get("oibdpq") or 0) or None
            niq = float(r.get("niq") or 0) or None
            capxy = float(r.get("capxy") or 0) or None
        except (ValueError, TypeError):
            continue
        fyearq = int(r.get("fyearq") or 0) or None
        fqtr = int(r.get("fqtr") or 0) or None
        rdq = _parse_date(r.get("rdq"))
        margin_pct = (oibdpq / saleq * 100.0) if (saleq and oibdpq is not None) else None
        if fyearq is not None and fqtr is not None and capxy is not None:
            capxy_by_year.setdefault(fyearq, []).append((fqtr, capxy))
        quarters.append({
            "fyearq": fyearq,
            "fqtr": fqtr,
            "datadate": (_parse_date(r.get("datadate")) or date.min).isoformat(),
            "rdq": rdq.isoformat() if rdq else None,
            "saleq_usd_m": saleq,
            "oibdpq_usd_m": oibdpq,
            "niq_usd_m": niq,
            "operating_margin_pct": margin_pct,
            "capxy_ytd_usd_m": capxy,
        })

    # Convert capxy (YTD) to quarterly capex via diff within fiscal year
    for q in quarters:
        if q["fyearq"] is None or q["fqtr"] is None:
            q["capex_quarterly_usd_m"] = None
            q["capex_intensity_pct"] = None
            continue
        same_year = sorted(capxy_by_year.get(q["fyearq"], []))
        prior_capxy = None
        for fq, c in same_year:
            if fq < q["fqtr"] and (prior_capxy is None or fq > prior_capxy[0]):
                prior_capxy = (fq, c)
        cur = q["capxy_ytd_usd_m"]
        if cur is None:
            q["capex_quarterly_usd_m"] = None
            q["capex_intensity_pct"] = None
            continue
        if q["fqtr"] == 1 or prior_capxy is None:
            q["capex_quarterly_usd_m"] = cur
        else:
            q["capex_quarterly_usd_m"] = cur - prior_capxy[1]
        if q["saleq_usd_m"]:
            q["capex_intensity_pct"] = (
                q["capex_quarterly_usd_m"] / q["saleq_usd_m"] * 100.0
            )
        else:
            q["capex_intensity_pct"] = None

    # Trend deltas (latest - prior)
    margins = [q["operating_margin_pct"] for q in quarters if q["operating_margin_pct"] is not None]
    nis = [q["niq_usd_m"] for q in quarters if q["niq_usd_m"] is not None]
    capex_ints = [q["capex_intensity_pct"] for q in quarters if q["capex_intensity_pct"] is not None]

    def _delta(xs: list[float]) -> float | None:
        return (xs[-1] - xs[0]) if len(xs) >= 2 else None

    return {
        "n_quarters": len(quarters),
        "data_sufficient": len(quarters) >= 2,
        "eps_data_available": False,
        "quarters": quarters,
        "margin_trend_delta_pp": _delta(margins),
        "netincome_trend_delta_usd_m": _delta(nis),
        "capex_intensity_trend_delta_pp": _delta(capex_ints),
        "latest_operating_margin_pct": margins[-1] if margins else None,
        "latest_capex_intensity_pct": capex_ints[-1] if capex_ints else None,
    }


# ---------------------------------------------------------------------------
# Section 3: regime
# ---------------------------------------------------------------------------

def _wti_return(at: date, lookback_days: int) -> dict:
    series = _wti_table()
    cur = _latest_on_or_before(series, at)
    prev = _latest_on_or_before(series, at - timedelta(days=lookback_days))
    if cur is None or prev is None or prev[1] == 0:
        return {"return_pct": None, "asof": None, "prev_asof": None}
    return {
        "return_pct": (cur[1] / prev[1] - 1.0) * 100.0,
        "asof": cur[0].isoformat(),
        "prev_asof": prev[0].isoformat(),
    }


def _xes_return(at: date, lookback_days: int) -> dict:
    rows = _benchmark_table()
    series: list[tuple[date, float]] = []
    for r in rows:
        d = _parse_date(r.get("date"))
        try:
            v = float(r.get("XES") or 0)
        except (ValueError, TypeError):
            continue
        if d and v > 0:
            series.append((d, v))
    series.sort()
    cur = _latest_on_or_before(series, at)
    prev = _latest_on_or_before(series, at - timedelta(days=lookback_days))
    if cur is None or prev is None or prev[1] == 0:
        return {"return_pct": None}
    return {"return_pct": (cur[1] / prev[1] - 1.0) * 100.0}


def _stock_beta_to_wti(ticker: str, at: date, n_trading_days: int = 60) -> dict:
    """OLS beta of daily stock returns on daily WTI returns over the last
    `n_trading_days` strictly before `at`."""
    from fin580.data.crsp_loader import load_combined
    crsp = load_combined()
    series = crsp.get(ticker, [])
    if not series:
        return {"beta_to_wti": None, "n_obs": 0}

    # Daily stock returns
    sorted_series = sorted([(d, p) for d, p, _ in series if d < at])[-(n_trading_days + 1):]
    if len(sorted_series) < 30:
        return {"beta_to_wti": None, "n_obs": 0}
    stock_dates = [d for d, _ in sorted_series]
    stock_rets: list[tuple[date, float]] = []
    for i in range(1, len(sorted_series)):
        p_prev = sorted_series[i - 1][1]
        p_cur = sorted_series[i][1]
        if p_prev > 0:
            stock_rets.append((sorted_series[i][0], p_cur / p_prev - 1.0))

    # Match WTI weekly returns by mapping each stock-date to the most recent
    # WTI-on-or-before-stock-date and computing the WTI WoW change.
    wti = _wti_table()
    pairs: list[tuple[float, float]] = []
    for d, sret in stock_rets:
        cur_wti = _latest_on_or_before(wti, d)
        prev_wti = _latest_on_or_before(wti, d - timedelta(days=7))
        if cur_wti is None or prev_wti is None or prev_wti[1] == 0:
            continue
        # Skip if same anchor (no fresh weekly data)
        if cur_wti[0] == prev_wti[0]:
            continue
        wret = cur_wti[1] / prev_wti[1] - 1.0
        pairs.append((sret, wret))

    if len(pairs) < 20:
        return {"beta_to_wti": None, "n_obs": len(pairs)}

    # OLS: beta = cov(s, w) / var(w)
    n = len(pairs)
    s_mean = sum(p[0] for p in pairs) / n
    w_mean = sum(p[1] for p in pairs) / n
    cov = sum((s - s_mean) * (w - w_mean) for s, w in pairs) / (n - 1)
    var_w = sum((w - w_mean) ** 2 for _, w in pairs) / (n - 1)
    beta = cov / var_w if var_w > 0 else None
    return {"beta_to_wti": float(beta) if beta is not None else None, "n_obs": n}


def build_regime(ticker: str, T: date) -> dict:
    """WTI 4w/12w return at T, XES 4w return at T, stock beta to WTI."""
    return {
        "wti_4w": _wti_return(T, 28),
        "wti_12w": _wti_return(T, 84),
        "xes_4w": _xes_return(T, 28),
        "stock_beta_to_wti": _stock_beta_to_wti(ticker, T),
    }


# ---------------------------------------------------------------------------
# Section 4: positioning
# ---------------------------------------------------------------------------

def build_positioning(ticker: str, T: date) -> dict:
    """3-month momentum, 52-week high/low distance from CRSP series, all
    strictly on or before T."""
    from fin580.data.crsp_loader import load_combined, price_at
    crsp = load_combined()
    series = crsp.get(ticker, [])
    if not series:
        return {
            "n_obs": 0,
            "data_sufficient": False,
        }

    p_T = price_at(series, T)
    p_3m = price_at(series, T - timedelta(days=90))
    if p_T is None:
        return {
            "n_obs": 0,
            "data_sufficient": False,
        }

    momentum_3m = ((p_T / p_3m - 1.0) * 100.0) if (p_3m and p_3m > 0) else None

    # 52-week window strictly on or before T
    cutoff_lo = T - timedelta(days=365)
    window = [p for d, p, _ in series if cutoff_lo <= d <= T and p > 0]
    if window:
        hi_52w = max(window)
        lo_52w = min(window)
        dist_high_pct = ((p_T / hi_52w - 1.0) * 100.0) if hi_52w > 0 else None
        dist_low_pct = ((p_T / lo_52w - 1.0) * 100.0) if lo_52w > 0 else None
    else:
        hi_52w = lo_52w = None
        dist_high_pct = dist_low_pct = None

    return {
        "n_obs": len(window),
        "data_sufficient": len(window) >= 200,
        "price_at_T": p_T,
        "price_3m_ago": p_3m,
        "momentum_3m_pct": momentum_3m,
        "high_52w": hi_52w,
        "low_52w": lo_52w,
        "distance_to_52w_high_pct": dist_high_pct,
        "distance_to_52w_low_pct": dist_low_pct,
    }


# ---------------------------------------------------------------------------
# Top-level builder
# ---------------------------------------------------------------------------

def build_brief_features(
    ticker: str,
    fiscal_quarter_end: date,
    decision_date_T: date,
) -> dict:
    """Compose all four sections into one dict for the brief LLM prompt."""
    return {
        "ticker": ticker,
        "fiscal_quarter_end": fiscal_quarter_end.isoformat(),
        "decision_date_T": decision_date_T.isoformat(),
        "reaction_history": build_reaction_history(ticker, decision_date_T),
        "fundamentals": build_fundamentals(ticker, decision_date_T),
        "regime": build_regime(ticker, decision_date_T),
        "positioning": build_positioning(ticker, decision_date_T),
    }
