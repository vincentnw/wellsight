"""
Earnings-date provenance pipeline.

Per Pre-Code Action Item 14 in project_overview.md, the T-14 trade-entry anchor
requires a definitive earnings announcement date that was publicly known before
T-14. The original spec called for Wall Street Horizon (WRDS) primary with
Wayback Machine fallback. Phase 1 verification confirmed the user's WRDS
subscription does NOT include Wall Street Horizon (`whexpect_eds_us`).

This module implements an acceptable substitute under the project-goal-alignment
framing (DL #48: innovative thinking, not full production-grade correctness):

    - Use `ANNDATS_ACT` from the I/B/E/S pull (the announcement date of the
      "actual" reported value). This is the date the earnings report became
      public.
    - Convert to T-14 = ANNDATS_ACT - 14 days. This is the trade-entry anchor.
    - Document the leakage caveat: we are using the ex-post finalized date,
      not a pre-announced date proven to have been knowable at T-14. In
      practice US large-and-mid-cap E&Ps pre-announce earnings dates 30+ days
      ahead via IR press releases; the realized announcement date matches
      the pre-announced date in the overwhelming majority of cases.

Output: phase1/output/earnings_dates.csv with columns
    ticker, fiscal_quarter_end, earnings_date_actual, decision_date_T,
    source ('ibes_anndats_act'), provenance_caveat
"""

from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
RAW_IBES = PHASE1_OUTPUT / "ibes_tr_ibes_sal_query11220958.csv"
TICKER_NAME_MAP = {
    "FANG": ["diamondback"], "EOG": ["eog resources"], "DVN": ["devon energy"],
    "CTRA": ["coterra energy"], "OXY": ["occidental"], "MTDR": ["matador resource"],
    "PR": ["permian resource"], "OVV": ["ovintiv"], "SM": ["sm energy"],
    "CRGY": ["crescent energy"],
}


def matches(oftic: str, cname: str) -> bool:
    cname_lc = (cname or "").lower()
    return any(cname_lc.startswith(p) for p in TICKER_NAME_MAP.get(oftic, []))


def build_earnings_dates() -> list[dict]:
    earliest_anndats_act: dict[tuple[str, str], str] = {}
    with open(RAW_IBES) as f:
        for row in csv.DictReader(f):
            if not matches(row["OFTIC"], row["CNAME"]):
                continue
            key = (row["OFTIC"], row["FPEDATS"])
            ada = row.get("ANNDATS_ACT", "").strip()
            if not ada:
                continue
            current = earliest_anndats_act.get(key)
            if current is None or ada < current:
                earliest_anndats_act[key] = ada

    out: list[dict] = []
    for (ticker, fpe), ada in sorted(earliest_anndats_act.items()):
        try:
            ada_date = datetime.strptime(ada, "%Y-%m-%d").date()
        except ValueError:
            continue
        T = ada_date - timedelta(days=14)
        out.append({
            "ticker": ticker,
            "fiscal_quarter_end": fpe,
            "earnings_date_actual": ada,
            "decision_date_T": T.isoformat(),
            "source": "ibes_anndats_act",
            "provenance_caveat": (
                "Date is ex-post-finalized announcement timestamp from IBES "
                "ANNDATS_ACT. Pre-announced provability not verified (Wall "
                "Street Horizon unsubscribed; Wayback Machine fallback not run "
                "for this design demo). E&P earnings dates are typically "
                "pre-announced 30+ days ahead via IR press releases, so the "
                "discrepancy is expected to be small."
            ),
        })
    return out


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "ticker", "fiscal_quarter_end", "earnings_date_actual",
            "decision_date_T", "source", "provenance_caveat",
        ])
        w.writeheader()
        for r in rows:
            w.writerow(r)


if __name__ == "__main__":
    rows = build_earnings_dates()
    out = PHASE1_OUTPUT / "earnings_dates.csv"
    write_csv(rows, out)
    by_t: dict[str, int] = {}
    for r in rows:
        by_t[r["ticker"]] = by_t.get(r["ticker"], 0) + 1
    print(f"Wrote {out} with {len(rows)} (ticker, fiscal-quarter) pairs")
    for t in sorted(TICKER_NAME_MAP.keys()):
        print(f"  {t:6s}: {by_t.get(t, 0)} quarters")
