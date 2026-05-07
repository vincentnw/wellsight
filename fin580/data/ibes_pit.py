"""Point-in-time IBES revenue consensus reconstruction at T-14 (spec Section
4.1 inputs to Agent 3, derived from raw tr_ibes panel pulled in Phase 1)."""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from statistics import median, stdev

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
RAW_IBES = PHASE1_OUTPUT / "ibes_tr_ibes_sal_query11220958.csv"

TICKER_NAME_MAP = {
    "FANG": ["diamondback"],
    "EOG": ["eog resources"],
    "DVN": ["devon energy"],
    "CTRA": ["coterra energy"],
    "OXY": ["occidental"],
    "MTDR": ["matador resource"],
    "PR": ["permian resource"],
    "OVV": ["ovintiv"],
    "SM": ["sm energy"],
    "CRGY": ["crescent energy"],
}


def _matches(oftic: str, cname: str) -> bool:
    cname_lc = (cname or "").lower()
    return any(cname_lc.startswith(p) for p in TICKER_NAME_MAP.get(oftic, []))


def _parse(s: str) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def consensus_at_T(
    ticker: str,
    fiscal_quarter_end: date,
    decision_date_T: date,
) -> dict:
    """Reconstruct active analyst panel at T = decision_date_T. Returns
    median consensus + dispersion + n_analysts (using each analyst's most
    recent estimate as of T)."""
    if not RAW_IBES.exists():
        return {"n_analysts": 0, "median_usd_m": None, "dispersion_usd_m": None}

    # IBES PIT rule (post-Codex Round-2 correction):
    # In IBES Detail-History, REVDATS = ANNDATS for un-revised estimates and
    # REVDATS > ANNDATS only when the estimate was revised, replaced, or
    # withdrawn. An estimate is active at T iff:
    #   (a) ANNDATS ≤ T (announced by T), AND
    #   (b) REVDATS == ANNDATS (never revised), OR REVDATS > T (still active at T).
    # Equivalently: keep iff ANNDATS ≤ T AND (REVDATS == ANNDATS OR REVDATS > T).
    # Bonus survivorship guard: pick the LATEST surviving estimate per analyst.
    latest_per_analyst: dict[str, tuple[date, float]] = {}
    with open(RAW_IBES) as f:
        for r in csv.DictReader(f):
            if not _matches(r["OFTIC"], r["CNAME"]):
                continue
            if r["OFTIC"] != ticker:
                continue
            fpe = _parse(r["FPEDATS"])
            if fpe != fiscal_quarter_end:
                continue
            anndats = _parse(r["ANNDATS"])
            if anndats is None or anndats > decision_date_T:
                continue
            revdats_raw = r.get("REVDATS", "").strip()
            if revdats_raw:
                revdats = _parse(revdats_raw)
                # Active at T iff REVDATS == ANNDATS (unchanged) or REVDATS > T.
                if revdats is not None and revdats != anndats and revdats <= decision_date_T:
                    continue
            try:
                v = float(r["VALUE"])
            except (ValueError, KeyError):
                continue
            analyst = r.get("ANALYS", "")
            cur = latest_per_analyst.get(analyst)
            if cur is None or anndats > cur[0]:
                latest_per_analyst[analyst] = (anndats, v)

    values = [v for _, v in latest_per_analyst.values()]
    n = len(values)
    if n == 0:
        return {"n_analysts": 0, "median_usd_m": None, "dispersion_usd_m": None}
    return {
        "n_analysts": n,
        "median_usd_m": median(values),
        "mean_usd_m": sum(values) / n,
        "dispersion_usd_m": stdev(values) if n > 1 else 0.0,
    }
