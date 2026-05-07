"""TRC + NMOCD permit/completion dump (spec Sections 3.1, 3.7).

Strategy: download per-county permit dumps from public RRC/NMOCD endpoints once,
deduplicate by API number, attach point-in-time operator at permit filing date.
Cache the result as `phase1/output/permit_dump.csv`.

PAPER-CLAIM SCOPE NOTE (per Codex Round-5 cleanup, Tier-2 #D):

If the cache file exists, the synthetic SAR generator runs on real TRC/NMOCD
records and the paper can claim "TRC-derived synthetic SAR proxy."

If the cache file does NOT exist, this module returns a deterministic
synthetic permit dump (`_generate_stub_dump`). In that case, the paper claim
narrows from "TRC-derived synthetic SAR proxy" to "synthetic permit dump +
literature-calibrated SAR proxy" — i.e. both the permit truth-state AND the
SAR observation are synthetic. This is acceptable under the project-goal
framing (innovation > full correctness) but MUST be reflected in:
  - paper Methodology (07-methodology.md): state explicitly which path was used
  - paper Limitations (13-discussion-limitations.md): list "fully synthetic
    permit substrate" as the top limitation
  - manifest.data_state.trc_permits_sha = "" (empty, signaling stub path)

The synthetic SAR pipeline only requires (operator, permit_filing_date,
spud_filing_date, completion_filing_date, latitude, longitude) per pad."""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from pathlib import Path

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
PERMIT_DUMP = PHASE1_OUTPUT / "permit_dump.csv"

UNIVERSE_OPERATORS = {
    "FANG": ["DIAMONDBACK"],
    "EOG": ["EOG RESOURCES"],
    "DVN": ["DEVON ENERGY"],
    "CTRA": ["COTERRA", "CIMAREX", "CABOT OIL"],
    "OXY": ["OCCIDENTAL", "OXY USA"],
    "MTDR": ["MATADOR"],
    "PR": ["PERMIAN RESOURCES", "CENTENNIAL", "COLGATE"],
    "OVV": ["OVINTIV", "ENCANA"],
    "SM": ["SM ENERGY", "ST. MARY"],
    "CRGY": ["CRESCENT ENERGY", "INDEPENDENCE ENERGY"],
}


@dataclass(frozen=True)
class Permit:
    pad_id: str
    operator_at_permit: str
    operator_normalized: str
    state: str
    county: str
    latitude: float
    longitude: float
    permit_filing_date: date
    spud_filing_date: date | None
    completion_filing_date: date | None
    api_number: str


def normalize_operator(name: str) -> str | None:
    name_upper = (name or "").upper()
    for ticker, patterns in UNIVERSE_OPERATORS.items():
        if any(p in name_upper for p in patterns):
            return ticker
    return None


def load_permit_dump() -> list[Permit]:
    if not PERMIT_DUMP.exists():
        return _generate_stub_dump()
    out: list[Permit] = []
    with open(PERMIT_DUMP) as f:
        for r in csv.DictReader(f):
            out.append(
                Permit(
                    pad_id=r["pad_id"],
                    operator_at_permit=r["operator_at_permit"],
                    operator_normalized=r["operator_normalized"],
                    state=r["state"],
                    county=r["county"],
                    latitude=float(r["latitude"]),
                    longitude=float(r["longitude"]),
                    permit_filing_date=datetime.strptime(
                        r["permit_filing_date"], "%Y-%m-%d"
                    ).date(),
                    spud_filing_date=(
                        datetime.strptime(r["spud_filing_date"], "%Y-%m-%d").date()
                        if r.get("spud_filing_date")
                        else None
                    ),
                    completion_filing_date=(
                        datetime.strptime(r["completion_filing_date"], "%Y-%m-%d").date()
                        if r.get("completion_filing_date")
                        else None
                    ),
                    api_number=r.get("api_number", ""),
                )
            )
    return out


def _generate_stub_dump() -> list[Permit]:
    """Deterministic synthetic permit dump for design demo.

    Per paper-claim scope note above, when this path is taken the paper
    Methodology must explicitly say so."""
    import random

    rng = random.Random(42)
    counties_tx = [
        "Midland", "Martin", "Reeves", "Loving", "Howard", "Reagan",
        "Glasscock", "Upton", "Ector", "Andrews",
    ]
    counties_nm = ["Eddy", "Lea"]
    pads_per_op = {
        "FANG": 90, "EOG": 80, "DVN": 65, "CTRA": 55, "OXY": 75,
        "MTDR": 50, "PR": 55, "OVV": 50, "SM": 45, "CRGY": 35,
    }
    out: list[Permit] = []
    pad_counter = 0
    for ticker, n_pads in pads_per_op.items():
        for _ in range(n_pads):
            pad_counter += 1
            state = rng.choices(["TX", "NM"], weights=[0.7, 0.3])[0]
            county = rng.choice(counties_tx if state == "TX" else counties_nm)
            base_lat = 31.5 if state == "TX" else 32.5
            lat = base_lat + rng.uniform(-1.0, 1.0)
            base_lon = -101.5 if state == "TX" else -103.7
            lon = base_lon + rng.uniform(-1.5, 1.5)
            permit_year = rng.randint(2019, 2025)
            permit_month = rng.randint(1, 12)
            permit_day = rng.randint(1, 28)
            permit_d = date(permit_year, permit_month, permit_day)
            spud_d: date | None = permit_d + timedelta(days=rng.randint(60, 180))
            comp_d: date | None = (
                spud_d + timedelta(days=rng.randint(180, 540))
                if rng.random() > 0.15
                else None
            )
            if spud_d and spud_d > date(2025, 12, 31):
                spud_d = None
            if comp_d and comp_d > date(2025, 12, 31):
                comp_d = None
            op_name = (
                UNIVERSE_OPERATORS[ticker][0]
                + (" CORP" if rng.random() > 0.5 else " LLC")
            )
            out.append(
                Permit(
                    pad_id=f"PAD_{pad_counter:05d}",
                    operator_at_permit=op_name,
                    operator_normalized=ticker,
                    state=state,
                    county=county,
                    latitude=lat,
                    longitude=lon,
                    permit_filing_date=permit_d,
                    spud_filing_date=spud_d,
                    completion_filing_date=comp_d,
                    api_number=f"42-{rng.randint(10000, 99999)}",
                )
            )
    return out


def filter_pit(
    permits: list[Permit],
    decision_date_T: date,
    operator: str | None = None,
) -> list[Permit]:
    """Apply spec Section 3.1 point-in-time rule: only permits AND completion
    records filed on or before T are visible."""
    out: list[Permit] = []
    for p in permits:
        if p.permit_filing_date > decision_date_T:
            continue
        if operator and p.operator_normalized != operator:
            continue
        spud = (
            p.spud_filing_date
            if p.spud_filing_date and p.spud_filing_date <= decision_date_T
            else None
        )
        comp = (
            p.completion_filing_date
            if p.completion_filing_date
            and p.completion_filing_date <= decision_date_T
            else None
        )
        out.append(replace(p, spud_filing_date=spud, completion_filing_date=comp))
    return out
