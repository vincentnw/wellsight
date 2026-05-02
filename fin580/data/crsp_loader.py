"""CRSP daily loader (Phase 1 pull) + Yahoo 2025 supplement, presented as a
single per-ticker date-keyed series of (Adj Close, return)."""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
CRSP_CSV = PHASE1_OUTPUT / "crsp_daily.csv"

LEGACY_REMAP = {"COG": "CTRA", "CDEV": "PR", "ECA": "OVV"}
DROP = {"AMR"}

UNIVERSE = ["FANG", "EOG", "DVN", "CTRA", "OXY", "MTDR", "PR", "OVV", "SM", "CRGY",
            "XLE", "BIL"]


def _parse(s: str) -> date | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def load_combined() -> dict[str, list[tuple[date, float, float | None]]]:
    """Returns {ticker: [(date, adj_close_total_return_basis, daily_return)]}.

    CRSP through 2024-12-31 (using PRC × adjustment factors as adj close
    proxy, RET as the daily total return), Yahoo 2025 supplement appended."""
    from fin580.data.yahoo_supplement import load_supplement

    out: dict[str, list[tuple[date, float, float | None]]] = {t: [] for t in UNIVERSE}

    if CRSP_CSV.exists():
        with open(CRSP_CSV) as f:
            for r in csv.DictReader(f):
                t = r["TICKER"]
                if t in DROP:
                    continue
                t_current = LEGACY_REMAP.get(t, t)
                if t_current not in out:
                    continue
                d = _parse(r["date"])
                if d is None:
                    continue
                try:
                    prc = abs(float(r["PRC"]))
                    cfacpr = float(r.get("CFACPR", "1") or 1.0)
                    adj_close = prc / cfacpr if cfacpr else prc
                    ret_str = r.get("RET", "")
                    ret_val = float(ret_str) if ret_str and ret_str != "C" else None
                except (ValueError, KeyError):
                    continue
                out[t_current].append((d, adj_close, ret_val))

    # Append Yahoo 2025 supplement
    yahoo = load_supplement()
    for t, rows in yahoo.items():
        if t not in out:
            continue
        existing_dates = {d for d, _, _ in out[t]}
        for d, ac, ret in rows:
            if d > date(2024, 12, 31) and d not in existing_dates:
                out[t].append((d, ac, ret))

    for t in out:
        out[t].sort()
    return out


def price_at(series: list[tuple[date, float, float | None]],
             target: date) -> float | None:
    """Most recent close on or before target."""
    last = None
    for d, ac, _ in series:
        if d <= target:
            last = ac
        else:
            break
    return last


def trailing_return(series: list[tuple[date, float, float | None]],
                     end: date, lookback_days: int) -> float | None:
    """Total return from (end - lookback_days) to end."""
    p_end = price_at(series, end)
    from datetime import timedelta
    p_start = price_at(series, end - timedelta(days=lookback_days))
    if p_end is None or p_start is None or p_start == 0:
        return None
    return (p_end - p_start) / p_start
