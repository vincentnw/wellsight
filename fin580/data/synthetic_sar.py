"""Synthetic SAR generator (spec Section 3).

Translates TRC permit/completion records into per-pad-quarter classifications
(newly_active / continuously_active / idle) using a literature-calibrated
class-conditional confusion matrix. Errors are i.i.d. per pad-quarter cell;
this assumption is documented in spec Section 3.5 and acknowledged in the
paper's Limitations section.

Codex Round-5 fixes baked in:
- Q1 quarter start is Jan 1 of the SAME year (not prior year)
- `continuously_active` truth state expires after 8 quarters
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import date
from typing import Literal

from fin580.data.trc_permits import Permit, filter_pit

State = Literal["newly_active", "continuously_active", "idle"]
STATES: list[State] = ["newly_active", "continuously_active", "idle"]

CONFUSION_MATRICES = {
    "optimistic": {
        "newly_active":        {"newly_active": 0.90, "continuously_active": 0.07, "idle": 0.03},
        "continuously_active": {"newly_active": 0.05, "continuously_active": 0.90, "idle": 0.05},
        "idle":                {"newly_active": 0.02, "continuously_active": 0.05, "idle": 0.93},
    },
    "target": {
        "newly_active":        {"newly_active": 0.78, "continuously_active": 0.12, "idle": 0.10},
        "continuously_active": {"newly_active": 0.08, "continuously_active": 0.80, "idle": 0.12},
        "idle":                {"newly_active": 0.05, "continuously_active": 0.10, "idle": 0.85},
    },
    "pessimistic": {
        "newly_active":        {"newly_active": 0.55, "continuously_active": 0.20, "idle": 0.25},
        "continuously_active": {"newly_active": 0.15, "continuously_active": 0.65, "idle": 0.20},
        "idle":                {"newly_active": 0.10, "continuously_active": 0.20, "idle": 0.70},
    },
}


@dataclass(frozen=True)
class PadQuarterClassification:
    pad_id: str
    operator_normalized: str
    quarter_end: date
    truth_state: State
    observed_state: State


def _quarter_start(q_end: date) -> date:
    """Spec Section 3.2: q_start is the first day of the quarter ending at q_end."""
    q_start_month = {3: 1, 6: 4, 9: 7, 12: 10}[q_end.month]
    return date(q_end.year, q_start_month, 1)


def _truth_for_pad_quarter(p: Permit, q_end: date) -> State:
    """Spec Section 3.2 truth mapping (point-in-time).

    Quarter start is the first day of the quarter that ends at q_end (e.g.
    q_end=2024-09-30 → q_start=2024-07-01). A pad is `newly_active` if its spud
    was filed within this quarter. A pad is `continuously_active` if it
    completed before this quarter and the completion is recent enough that the
    well is plausibly still producing — operationalized as completion within
    the prior 8 quarters; after that the pad is treated as `idle`.
    """
    q_start = _quarter_start(q_end)
    eight_quarters_ago = date(q_end.year - 2, q_end.month, 1)
    if p.spud_filing_date and q_start <= p.spud_filing_date <= q_end:
        return "newly_active"
    if (
        p.completion_filing_date
        and eight_quarters_ago <= p.completion_filing_date < q_start
    ):
        return "continuously_active"
    return "idle"


def _seed_for(ticker: str, q_end: date, pad_id: str, cm_label: str) -> int:
    s = f"{ticker}|{q_end.isoformat()}|{pad_id}|{cm_label}"
    h = hashlib.sha256(s.encode()).hexdigest()
    return int(h[:8], 16)


def _sample_observation(truth: State, cm: dict, rng: random.Random) -> State:
    weights = [cm[truth][s] for s in STATES]
    return rng.choices(STATES, weights=weights)[0]


def classify_pads(
    *,
    permits: list[Permit],
    operator: str,
    fiscal_quarter_end: date,
    decision_date_T: date,
    cm_label: str = "target",
) -> list[PadQuarterClassification]:
    """Run point-in-time classification for one operator × quarter (spec Section 3)."""
    cm = CONFUSION_MATRICES[cm_label]
    pit_permits = filter_pit(permits, decision_date_T, operator=operator)
    out: list[PadQuarterClassification] = []
    for p in pit_permits:
        truth = _truth_for_pad_quarter(p, fiscal_quarter_end)
        seed = _seed_for(operator, fiscal_quarter_end, p.pad_id, cm_label)
        rng = random.Random(seed)
        observed = _sample_observation(truth, cm, rng)
        out.append(
            PadQuarterClassification(
                pad_id=p.pad_id,
                operator_normalized=operator,
                quarter_end=fiscal_quarter_end,
                truth_state=truth,
                observed_state=observed,
            )
        )
    return out


def aggregate_to_firm_quarter(
    classifications: list[PadQuarterClassification],
) -> dict:
    """Spec Section 3.4 aggregation rule."""
    n_new = sum(1 for c in classifications if c.observed_state == "newly_active")
    n_cont = sum(1 for c in classifications if c.observed_state == "continuously_active")
    n_idle = sum(1 for c in classifications if c.observed_state == "idle")
    total = n_new + n_cont + n_idle
    return {
        "n_newly_active": n_new,
        "n_continuously_active": n_cont,
        "n_idle": n_idle,
        "absolute_active": n_new + n_cont,
        "share_active": (n_new + n_cont) / total if total > 0 else 0.0,
        "total_monitored": total,
    }
