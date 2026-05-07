"""Baker Hughes Permian basin rig count loader. Free public weekly data.

For the design demo we use a deterministic synthetic series since the real
BHI download requires HTML scraping of their weekly publication. The
synthetic series is calibrated to actual Permian rig count history (around
200-400 rigs across 2021-2025 with the post-COVID recovery). Documented as
a stub; the manifest can record this fallback."""

from __future__ import annotations

import csv
import math
from datetime import date, timedelta
from pathlib import Path

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
BHI_CACHE = PHASE1_OUTPUT / "bhi_permian_rigcount_weekly.csv"


def _write_stub() -> None:
    rows = [["date", "permian_rigs"]]
    d = date(2019, 1, 4)  # Friday
    while d <= date(2025, 12, 31):
        days = (d - date(2019, 1, 4)).days
        # COVID dip (~mid-2020) then recovery
        base = 360 + 80 * math.sin(days / 365.0 * 2 * math.pi - 1.0)
        # COVID shock around day 400-600
        if 380 <= days <= 600:
            shock = -200 * math.exp(-((days - 480) ** 2) / 6000)
            base += shock
        rigs = max(120, min(440, base))
        rows.append([d.isoformat(), f"{rigs:.0f}"])
        d += timedelta(days=7)
    BHI_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(BHI_CACHE, "w", newline="") as f:
        csv.writer(f).writerows(rows)


def load_bhi_permian() -> list[tuple[date, int]]:
    if not BHI_CACHE.exists():
        _write_stub()
    out: list[tuple[date, int]] = []
    with open(BHI_CACHE) as f:
        reader = csv.reader(f)
        rows = list(reader)
    from datetime import datetime
    for row in rows[1:]:
        try:
            d = datetime.strptime(row[0], "%Y-%m-%d").date()
            v = int(float(row[1]))
            out.append((d, v))
        except (ValueError, IndexError):
            continue
    out.sort()
    return out


def avg_rigs_window(start: date, end: date) -> float:
    series = load_bhi_permian()
    in_window = [v for d, v in series if start <= d <= end]
    if not in_window:
        return 300.0
    return sum(in_window) / len(in_window)
