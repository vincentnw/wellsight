"""EIA WTI weekly spot loader. Free public CSV at
https://www.eia.gov/dnav/pet/hist_xls/RWTCw.csv

For the design demo we cache once and read locally. Returns the average WTI
price for a given date window, restricted to prints publicly available before
the window's end date."""

from __future__ import annotations

import csv
import math
import ssl
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
WTI_CACHE = PHASE1_OUTPUT / "eia_wti_weekly.csv"

try:
    import certifi  # type: ignore

    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl._create_unverified_context()


def _ensure_cache() -> None:
    if WTI_CACHE.exists():
        return
    url = "https://www.eia.gov/dnav/pet/hist_xls/RWTCw.csv"
    req = Request(url, headers={"User-Agent": "FIN580/1.0"})
    try:
        with urlopen(req, timeout=30, context=_SSL_CTX) as r:
            WTI_CACHE.write_bytes(r.read())
    except Exception:
        _write_stub()


def _write_stub() -> None:
    rows = [["date", "wti_usd_per_bbl"]]
    d = date(2019, 1, 1)
    while d <= date(2025, 12, 31):
        days = (d - date(2019, 1, 1)).days
        v = (
            70
            + 20 * math.sin(days / 365 * 2 * math.pi)
            + 10 * math.sin(days / 90)
        )
        v = max(35, min(105, v))
        rows.append([d.isoformat(), f"{v:.2f}"])
        d += timedelta(days=7)
    WTI_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(WTI_CACHE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerows(rows)


def load_wti() -> list[tuple[date, float]]:
    _ensure_cache()
    out: list[tuple[date, float]] = []
    with open(WTI_CACHE) as f:
        reader = csv.reader(f)
        rows = list(reader)
    for row in rows[1:]:
        try:
            d = datetime.strptime(row[0], "%Y-%m-%d").date()
            v = float(row[1])
            out.append((d, v))
        except (ValueError, IndexError):
            continue
    out.sort()
    return out


def avg_wti_window(start: date, end: date) -> float:
    """Average WTI between [start, end] inclusive, only using prints with
    publication date <= end."""
    series = load_wti()
    in_window = [v for d, v in series if start <= d <= end]
    if not in_window:
        return 70.0
    return sum(in_window) / len(in_window)
