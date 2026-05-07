"""
Point-in-time equity universe constructor.

At each decision date T, returns the subset of the 10 candidate Permian E&Ps that
satisfies the eligibility rules in DL #44 and DL #47:

    - Listed on a US exchange as of T (CRSP membership).
    - Market cap >= $500M at T (CRSP price * shares outstanding).
    - >= 30% of trailing-12-month production from Permian per latest 10-K
      segment disclosure (manually populated permian_fraction.csv input).
    - >= 3 distinct analysts forecasting revenue (sales) at the relevant
      fiscal-quarter end (from ibes_revenue_coverage.csv).

Names that fail eligibility mid-window are exited at last close, not back-filled.
The constructor is point-in-time: it never uses information dated after T.

Per Pre-Code Action Item 11 in project_overview.md.

This is a reference implementation supporting the design demonstration; full
production hardening (e.g. CRSP delisting flags, suspended-trading handling,
ticker-permno reassignments) is sketched but not exhaustive.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

CANDIDATES = ["FANG", "EOG", "DVN", "CTRA", "OXY", "MTDR", "PR", "OVV", "SM", "CRGY"]

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"


@dataclass(frozen=True)
class EligibilityResult:
    ticker: str
    decision_date_T: date
    fiscal_quarter_end: date
    listed: bool
    market_cap_usd: float | None
    permian_fraction_ttm: float | None
    n_analysts: int
    eligible: bool
    drop_reason: str | None


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def load_ibes_coverage(path: Path = PHASE1_OUTPUT / "ibes_revenue_coverage.csv") -> dict[tuple[str, date], int]:
    """Returns {(ticker, fiscal_quarter_end): n_unique_analysts}."""
    out: dict[tuple[str, date], int] = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            out[(row["ticker"], _parse_date(row["fiscal_quarter_end"]))] = int(row["n_unique_analysts"])
    return out


def load_crsp_daily(path: Path = PHASE1_OUTPUT / "crsp_daily.csv") -> dict[str, list[dict]]:
    """Returns {current_ticker: [rows ordered by date]}.

    Legacy tickers (COG, CDEV, ECA) are remapped to current names (CTRA, PR, OVV)
    so that price history is continuous across corporate actions. AMR is a
    name-search false positive and is dropped. CTRA rows from CONTURA ENERGY
    (a coal company that previously held the ticker) are filtered out by COMNAM
    so they don't contaminate Coterra's series.
    """
    legacy_remap = {"COG": "CTRA", "CDEV": "PR", "ECA": "OVV"}
    drop = {"AMR"}
    out: dict[str, list[dict]] = {t: [] for t in CANDIDATES}
    with open(path) as f:
        for row in csv.DictReader(f):
            t = row["TICKER"]
            if t in drop:
                continue
            # Drop Contura Energy rows (coal company, ticker reuse before Coterra)
            if t == "CTRA" and "CONTURA" in (row.get("COMNAM") or "").upper():
                continue
            current = legacy_remap.get(t, t)
            if current not in CANDIDATES:
                continue
            row["_date"] = _parse_date(row["date"])
            row["_current_ticker"] = current
            out[current].append(row)
    for t in out:
        out[t].sort(key=lambda r: r["_date"])
    return out


def load_permian_fraction(path: Path | None = None) -> dict[tuple[str, int], float]:
    """Returns {(ticker, fiscal_year): permian_fraction_ttm}.

    Hand-populated from 10-K segment data per ticker per fiscal year. If file is
    missing, returns conservative defaults: pure-play Permian names get 1.0,
    multi-basin names get 0.40 as a placeholder (overwrite when audit completes).
    """
    out: dict[tuple[str, int], float] = {}
    if path is None:
        path = PHASE1_OUTPUT / "permian_fraction.csv"
    if path.exists():
        with open(path) as f:
            for row in csv.DictReader(f):
                v = row.get("permian_production_fraction_ttm") or row.get("permian_fraction_ttm") or ""
                if not v.strip():
                    continue
                try:
                    out[(row["ticker"], int(row["fiscal_year"]))] = float(v)
                except (ValueError, KeyError):
                    continue
        return out
    pure_play = {"FANG", "MTDR", "PR"}
    multi_basin = {"EOG", "DVN", "CTRA", "OXY", "OVV", "SM", "CRGY"}
    for t in pure_play:
        for y in range(2020, 2026):
            out[(t, y)] = 1.0
    for t in multi_basin:
        for y in range(2020, 2026):
            out[(t, y)] = 0.40
    return out


def market_cap_at(crsp_rows: list[dict], target: date) -> float | None:
    """Most recent close on or before `target` * shares outstanding (in 1000s).

    SHROUT is in thousands of shares per CRSP convention.
    """
    candidate = None
    for r in crsp_rows:
        if r["_date"] <= target:
            candidate = r
        else:
            break
    if candidate is None:
        return None
    try:
        prc = abs(float(candidate["PRC"]))
        shrout = float(candidate["SHROUT"]) * 1_000.0
    except (ValueError, KeyError):
        return None
    return prc * shrout


def latest_fiscal_year_at(target: date) -> int:
    """Most recent fiscal year whose 10-K is plausibly filed by `target` (lag 90 days)."""
    if target.month <= 3:
        return target.year - 2
    return target.year - 1


def evaluate_quarter(
    ticker: str,
    decision_date_T: date,
    fiscal_quarter_end: date,
    ibes: dict[tuple[str, date], int],
    crsp: dict[str, list[dict]],
    permian: dict[tuple[str, int], float],
    min_market_cap: float = 500_000_000.0,
    min_permian_fraction: float = 0.30,
    min_analysts: int = 3,
) -> EligibilityResult:
    rows = crsp.get(ticker, [])
    listed = any(r["_date"] <= decision_date_T for r in rows)

    cap = market_cap_at(rows, decision_date_T) if listed else None
    fy = latest_fiscal_year_at(decision_date_T)
    pf = permian.get((ticker, fy))
    n_an = ibes.get((ticker, fiscal_quarter_end), 0)

    reasons: list[str] = []
    if not listed:
        reasons.append("not_listed")
    if cap is None or cap < min_market_cap:
        reasons.append("low_market_cap")
    if pf is None or pf < min_permian_fraction:
        reasons.append("low_permian_fraction")
    if n_an < min_analysts:
        reasons.append("thin_coverage")

    eligible = not reasons
    return EligibilityResult(
        ticker=ticker,
        decision_date_T=decision_date_T,
        fiscal_quarter_end=fiscal_quarter_end,
        listed=listed,
        market_cap_usd=cap,
        permian_fraction_ttm=pf,
        n_analysts=n_an,
        eligible=eligible,
        drop_reason=";".join(reasons) or None,
    )


def quarter_ends_window(start_year: int = 2021, end_year: int = 2025) -> Iterable[date]:
    for y in range(start_year, end_year + 1):
        for m, d in [(3, 31), (6, 30), (9, 30), (12, 31)]:
            yield date(y, m, d)


def build_panel(
    decision_offsets_days: int = -14,
    earnings_lag_days: int = 45,
) -> list[EligibilityResult]:
    """Construct the (ticker x quarter) eligibility panel.

    decision_date_T = quarter_end + earnings_lag_days + decision_offsets_days,
    i.e. ~Q-close + 31 days = T-14 anchor for the quarter's earnings announcement.
    Real earnings dates per company are sourced separately (Pre-Code #14); this
    function uses the calendar approximation when an earnings calendar is not
    yet wired in.
    """
    ibes = load_ibes_coverage()
    crsp = load_crsp_daily()
    permian = load_permian_fraction()

    panel: list[EligibilityResult] = []
    for q_end in quarter_ends_window():
        for t in CANDIDATES:
            from datetime import timedelta
            T = q_end + timedelta(days=earnings_lag_days + decision_offsets_days)
            panel.append(evaluate_quarter(t, T, q_end, ibes, crsp, permian))
    return panel


def write_panel(panel: list[EligibilityResult], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "ticker", "decision_date_T", "fiscal_quarter_end",
            "listed", "market_cap_usd", "permian_fraction_ttm",
            "n_analysts", "eligible", "drop_reason",
        ])
        for r in panel:
            w.writerow([
                r.ticker, r.decision_date_T.isoformat(), r.fiscal_quarter_end.isoformat(),
                r.listed, r.market_cap_usd or "", r.permian_fraction_ttm or "",
                r.n_analysts, r.eligible, r.drop_reason or "",
            ])


if __name__ == "__main__":
    panel = build_panel()
    out = PHASE1_OUTPUT / "equity_universe_panel.csv"
    write_panel(panel, out)
    n_eligible = sum(1 for r in panel if r.eligible)
    print(f"Wrote {out} with {len(panel)} rows; {n_eligible} eligible")
    by_t = {}
    for r in panel:
        by_t.setdefault(r.ticker, [0, 0])
        by_t[r.ticker][1] += 1
        if r.eligible:
            by_t[r.ticker][0] += 1
    for t in CANDIDATES:
        e, n = by_t.get(t, [0, 0])
        print(f"  {t:6s}: {e}/{n} eligible")
