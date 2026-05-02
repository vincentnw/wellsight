"""SAR-only fetch helper for collaborative data download.

Runs only the Sentinel-1 SAR ingestion stage of the pipeline — no LLM calls,
no API keys, no WRDS access. Designed for friends helping pre-cache SAR for
additional years.

Usage:
    python3 scripts/fetch_sar_for_window.py --start 2022Q1 --end 2022Q4
    python3 scripts/fetch_sar_for_window.py --start 2023Q1 --end 2023Q4 --firms FANG,EOG,DVN
    python3 scripts/fetch_sar_for_window.py --start 2025Q3 --end 2025Q3 --pads-per-firm 5

Output is two cache subtrees in phase1/output/sentinel1_cache/. Ship the zip
back to the lead author. See docs/SAR_DATA_DOWNLOAD.md for the full guide.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fin580.data.sentinel1_firm_quarter import aggregate_firm_quarter

PHASE1 = ROOT / "phase1" / "output"

UNIVERSE_DEFAULT = [
    "FANG", "EOG", "DVN", "CTRA", "OXY",
    "MTDR", "PR", "OVV", "SM", "CRGY",
]


def parse_quarter(label: str):
    """e.g. '2024Q3' -> (year=2024, fpe=date(2024, 9, 30))."""
    y = int(label[:4])
    q = int(label[5:])
    m = {1: 3, 2: 6, 3: 9, 4: 12}[q]
    d = {3: 31, 6: 30, 9: 30, 12: 31}[m]
    from datetime import date as _date
    return _date(y, m, d)


def enumerate_quarters(start: str, end: str):
    s_y, s_q = int(start[:4]), int(start[5:])
    e_y, e_q = int(end[:4]), int(end[5:])
    out = []
    y, q = s_y, s_q
    while (y, q) <= (e_y, e_q):
        out.append(f"{y}Q{q}")
        q += 1
        if q > 4:
            q, y = 1, y + 1
    return out


def load_earnings_dates():
    out = {}
    with open(PHASE1 / "earnings_dates.csv") as f:
        for r in csv.DictReader(f):
            t = r["ticker"]
            fpe = datetime.strptime(r["fiscal_quarter_end"], "%Y-%m-%d").date()
            ed = datetime.strptime(r["earnings_date_actual"], "%Y-%m-%d").date()
            out[(t, fpe)] = ed
    return out


def main():
    ap = argparse.ArgumentParser(description="Fetch Sentinel-1 SAR for a window.")
    ap.add_argument("--start", required=True, help="Start quarter, e.g. 2022Q1")
    ap.add_argument("--end", required=True, help="End quarter, e.g. 2023Q4")
    ap.add_argument(
        "--firms",
        default=",".join(UNIVERSE_DEFAULT),
        help="Comma-separated tickers to include (default: all 10).",
    )
    ap.add_argument(
        "--pads-per-firm",
        type=int,
        default=5,
        help="Representative pads sampled per firm per quarter (default: 5).",
    )
    args = ap.parse_args()

    firms = [t.strip().upper() for t in args.firms.split(",") if t.strip()]
    quarters = enumerate_quarters(args.start, args.end)
    eds = load_earnings_dates()

    print(f"SAR helper: {len(firms)} firms × {len(quarters)} quarters = "
          f"{len(firms) * len(quarters)} cells max")
    print(f"Pads per firm: {args.pads_per_firm}")
    print(f"Cache: {PHASE1 / 'sentinel1_cache'}")
    print()

    os.environ["FIN580_SAR_PADS_PER_OP"] = str(args.pads_per_firm)

    n_done = 0
    n_skipped = 0
    n_error = 0
    t0 = time.time()
    for q_label in quarters:
        fpe = parse_quarter(q_label)
        for ticker in firms:
            ed = eds.get((ticker, fpe))
            if ed is None:
                print(f"  SKIP {ticker} {q_label} — no earnings date in CSV")
                n_skipped += 1
                continue
            T = ed - timedelta(days=14)
            cell_t0 = time.time()
            try:
                sig = aggregate_firm_quarter(
                    ticker=ticker, fiscal_quarter_end=fpe, decision_date_T=T,
                )
                elapsed = time.time() - cell_t0
                print(
                    f"  OK   {ticker} {q_label}: pads={sig.n_pads_sampled} "
                    f"obs={sig.n_observations_total} "
                    f"(new={sig.n_newly_active} cont={sig.n_continuously_active} "
                    f"idle={sig.n_idle}) {elapsed:.1f}s"
                )
                n_done += 1
            except Exception as e:
                print(f"  ERR  {ticker} {q_label}: {type(e).__name__}: {e}")
                n_error += 1

    total = time.time() - t0
    print()
    print(f"Done: {n_done} cells cached, {n_skipped} skipped (no earnings), "
          f"{n_error} errored. Total wall time: {total/60:.1f} min")
    print()
    print("Next steps:")
    print("  1. Run scripts/validate_sar_cache.py")
    print(f"  2. Zip up phase1/output/sentinel1_cache/ and send to the lead author.")


if __name__ == "__main__":
    main()
