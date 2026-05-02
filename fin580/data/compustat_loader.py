"""Compustat fundq loader. Returns latest quarter on-or-before a target date
per ticker. Used by Strategies 9 (value) and 10 (quality)."""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
COMPUSTAT_CSV = PHASE1_OUTPUT / "compustat_fundq.csv"


def _parse(s: str) -> date | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _safe_float(s: str) -> float | None:
    try:
        return float(s) if s and s != "" else None
    except ValueError:
        return None


def load_fundq() -> dict[str, list[dict]]:
    """Returns {tic: [rows sorted by datadate]}."""
    if not COMPUSTAT_CSV.exists():
        return {}
    out: dict[str, list[dict]] = {}
    with open(COMPUSTAT_CSV) as f:
        for r in csv.DictReader(f):
            t = r.get("tic")
            if not t:
                continue
            datadate = _parse(r.get("datadate", ""))
            rdq = _parse(r.get("rdq", ""))
            if datadate is None:
                continue
            row = {
                "datadate": datadate,
                "rdq": rdq,
                "saleq": _safe_float(r.get("saleq", "")),
                "oibdpq": _safe_float(r.get("oibdpq", "")),
                "niq": _safe_float(r.get("niq", "")),
                "oancfy": _safe_float(r.get("oancfy", "")),
                "capxy": _safe_float(r.get("capxy", "")),
                "ceqq": _safe_float(r.get("ceqq", "")),
                "dlttq": _safe_float(r.get("dlttq", "")),
                "dlcq": _safe_float(r.get("dlcq", "")),
                "cheq": _safe_float(r.get("cheq", "")),
            }
            out.setdefault(t, []).append(row)
    for t in out:
        out[t].sort(key=lambda r: r["datadate"])
    return out


def latest_at_T(rows: list[dict], decision_date_T: date) -> dict | None:
    """Most recent fundq row whose `rdq` (announcement) is on or before T,
    or `datadate` if `rdq` missing. Lagged-to-rdq rule (DL #57 / spec)."""
    candidate = None
    for r in rows:
        eff = r.get("rdq") or r.get("datadate")
        if eff is None:
            continue
        if eff <= decision_date_T:
            candidate = r
        else:
            break
    return candidate
