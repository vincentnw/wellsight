"""CRSP 2025 supplementation via yfinance (spec DL #52, locked decision).

Pulls Adj Close + Open + Volume for each ticker for dates after 2024-12-31.
Combined with CRSP daily for a continuous price series across the full backtest
window."""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
YAHOO_2025_CACHE = PHASE1_OUTPUT / "yahoo_2025_supplement.csv"

UNIVERSE = [
    "FANG", "EOG", "DVN", "CTRA", "OXY", "MTDR", "PR", "OVV", "SM", "CRGY",
    "XLE", "BIL",
]


def fetch_2025() -> None:
    """Run once. Persists cached supplement as CSV."""
    if YAHOO_2025_CACHE.exists():
        return
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        # Cannot fetch without yfinance; persist empty cache so callers see no rows.
        YAHOO_2025_CACHE.parent.mkdir(parents=True, exist_ok=True)
        with open(YAHOO_2025_CACHE, "w", newline="") as f:
            csv.writer(f).writerows([["ticker", "date", "adj_close", "ret"]])
        return
    rows: list[list[str]] = [["ticker", "date", "adj_close", "ret"]]
    for t in UNIVERSE:
        try:
            df = yf.download(
                t, start="2024-12-15", end="2026-01-01",
                auto_adjust=False, progress=False,
            )
        except Exception:
            continue
        if df is None or df.empty:
            continue
        # Flatten possible MultiIndex columns from newer yfinance
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)
        if "Adj Close" not in df.columns:
            continue
        adj = df["Adj Close"].astype(float)
        ret_series = adj.pct_change()
        for idx, ac_val in adj.items():
            d = idx.date() if hasattr(idx, "date") else None
            if d is None:
                continue
            ret_val = ret_series.loc[idx]
            try:
                ac_f = float(ac_val)
            except (TypeError, ValueError):
                continue
            try:
                ret_f = float(ret_val)
                ret_s = "" if ret_f != ret_f else f"{ret_f:.6f}"  # NaN check
            except (TypeError, ValueError):
                ret_s = ""
            rows.append([t, d.isoformat(), f"{ac_f:.4f}", ret_s])
    YAHOO_2025_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(YAHOO_2025_CACHE, "w", newline="") as f:
        csv.writer(f).writerows(rows)


def load_supplement() -> dict[str, list[tuple[date, float, float | None]]]:
    """Returns {ticker: [(date, adj_close, ret)]}."""
    if not YAHOO_2025_CACHE.exists():
        fetch_2025()
    if not YAHOO_2025_CACHE.exists():
        return {}
    out: dict[str, list[tuple[date, float, float | None]]] = {}
    with open(YAHOO_2025_CACHE) as f:
        for r in csv.DictReader(f):
            try:
                d = datetime.strptime(r["date"], "%Y-%m-%d").date()
                ac = float(r["adj_close"])
            except (ValueError, KeyError):
                continue
            ret = float(r["ret"]) if r["ret"] else None
            out.setdefault(r["ticker"], []).append((d, ac, ret))
    for t in out:
        out[t].sort()
    return out
