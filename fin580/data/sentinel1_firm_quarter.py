"""Firm × quarter aggregation of real Sentinel-1 SAR signals.

Selects representative pads per operator, fetches Sentinel-1 backscatter
time series for each, classifies the activity state per pad-quarter, and
returns aggregated counts ready for Agent 1 consumption.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from fin580.data.sentinel1_sar import (
    SarObservation,
    classify_pad_from_sar,
    fetch_pad_backscatter,
)
from fin580.data.trc_permits import Permit, load_permit_dump

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
SAR_FIRM_CACHE = PHASE1_OUTPUT / "sentinel1_cache" / "firm_quarter_aggregates"
SAR_FIRM_CACHE.mkdir(parents=True, exist_ok=True)


# Number of representative pads per operator to sample. Smaller = faster but
# noisier; larger = slower but more representative.
PADS_PER_OP_DEFAULT = int(os.environ.get("FIN580_SAR_PADS_PER_OP", 5))


def _select_representative_pads(
    permits: list[Permit],
    ticker: str,
    fiscal_quarter_end: date,
    n_pads: int,
) -> list[Permit]:
    """Pick n_pads representative permits for the operator.

    Stratified sampling: roughly 1/3 from the active-drilling cohort
    (permit filed within the last 6 months, no completion yet — likely
    'newly_active' radar signature), 1/3 from the recently-completed cohort
    (completed within prior 24 months), 1/3 from the older cohort
    (completed > 2 years ago — likely 'idle'). This gives the change-
    detection rule a balanced panel and makes the firm-quarter aggregate
    sensitive to real activity changes."""
    operator_permits = [p for p in permits if p.operator_normalized == ticker]
    if not operator_permits:
        return []

    active = [
        p for p in operator_permits
        if p.permit_filing_date <= fiscal_quarter_end
        and (p.permit_filing_date >= fiscal_quarter_end - timedelta(days=180))
        and (p.completion_filing_date is None or p.completion_filing_date > fiscal_quarter_end)
    ]
    recent = [
        p for p in operator_permits
        if p.completion_filing_date is not None
        and (fiscal_quarter_end - timedelta(days=730)) <= p.completion_filing_date <= fiscal_quarter_end
    ]
    older = [
        p for p in operator_permits
        if p.completion_filing_date is not None
        and p.completion_filing_date < (fiscal_quarter_end - timedelta(days=730))
    ]

    # Deterministic ordering inside each cohort for reproducibility
    active.sort(key=lambda p: p.pad_id)
    recent.sort(key=lambda p: p.pad_id)
    older.sort(key=lambda p: p.pad_id)

    # Round-robin from cohorts until we hit n_pads
    out: list[Permit] = []
    cohorts = [active, recent, older]
    while len(out) < n_pads and any(cohorts):
        for c in cohorts:
            if c:
                out.append(c.pop(0))
                if len(out) >= n_pads:
                    break
    return out[:n_pads]


@dataclass
class FirmQuarterSarSignal:
    ticker: str
    fiscal_quarter_end: date
    decision_date_T: date
    n_pads_sampled: int
    n_newly_active: int
    n_continuously_active: int
    n_idle: int
    n_observations_total: int
    pad_classifications: list[dict] = field(default_factory=list)


def aggregate_firm_quarter(
    *,
    ticker: str,
    fiscal_quarter_end: date,
    decision_date_T: date,
    pads_per_op: int = PADS_PER_OP_DEFAULT,
) -> FirmQuarterSarSignal:
    """Pull real Sentinel-1 SAR for representative pads of `ticker`,
    classify per-pad in [target_quarter_end - 91d, target_quarter_end] window,
    and return aggregate counts."""
    cache_key = f"{ticker}_{fiscal_quarter_end.isoformat()}_{decision_date_T.isoformat()}_n{pads_per_op}"
    cache_path = SAR_FIRM_CACHE / f"{cache_key}.json"
    if cache_path.exists():
        d = json.loads(cache_path.read_text())
        return FirmQuarterSarSignal(
            ticker=d["ticker"],
            fiscal_quarter_end=date.fromisoformat(d["fiscal_quarter_end"]),
            decision_date_T=date.fromisoformat(d["decision_date_T"]),
            n_pads_sampled=d["n_pads_sampled"],
            n_newly_active=d["n_newly_active"],
            n_continuously_active=d["n_continuously_active"],
            n_idle=d["n_idle"],
            n_observations_total=d["n_observations_total"],
            pad_classifications=d.get("pad_classifications", []),
        )

    permits = load_permit_dump()
    representative = _select_representative_pads(
        permits, ticker, fiscal_quarter_end, pads_per_op
    )
    if not representative:
        # No real permits for this operator (e.g. CRGY); return zero signal
        result = FirmQuarterSarSignal(
            ticker=ticker,
            fiscal_quarter_end=fiscal_quarter_end,
            decision_date_T=decision_date_T,
            n_pads_sampled=0,
            n_newly_active=0,
            n_continuously_active=0,
            n_idle=0,
            n_observations_total=0,
        )
        cache_path.write_text(json.dumps({
            "ticker": ticker,
            "fiscal_quarter_end": fiscal_quarter_end.isoformat(),
            "decision_date_T": decision_date_T.isoformat(),
            "n_pads_sampled": 0,
            "n_newly_active": 0,
            "n_continuously_active": 0,
            "n_idle": 0,
            "n_observations_total": 0,
            "pad_classifications": [],
        }))
        return result

    counts = {"newly_active": 0, "continuously_active": 0, "idle": 0}
    pad_classifications = []
    n_obs_total = 0

    # Fetch SAR for ~365 days ending at decision_date_T
    fetch_start = fiscal_quarter_end - timedelta(days=365)
    fetch_end = min(fiscal_quarter_end, decision_date_T)

    # Sequential fetch — earlier ThreadPoolExecutor + rasterio combination
    # deadlocked on macOS, leaving sockets in CLOSE_WAIT and all threads in
    # pthread_cond_wait. Sequential is slower but reliable. Each pad's full
    # 1-year fetch is cached to disk on first call; subsequent runs hit cache.
    pad_obs_pairs: list[tuple] = []
    for permit in representative:
        obs = fetch_pad_backscatter(
            pad_id=permit.pad_id,
            lat=permit.latitude,
            lon=permit.longitude,
            start_date=fetch_start,
            end_date=fetch_end,
        )
        pad_obs_pairs.append((permit, obs))

    for permit, obs in pad_obs_pairs:
        n_obs_total += len(obs)
        cls = classify_pad_from_sar(
            pad_id=permit.pad_id,
            obs=obs,
            target_quarter_end=fiscal_quarter_end,
            completion_filing_date=permit.completion_filing_date,
            decision_date_T=decision_date_T,
        )
        counts[cls] += 1
        pad_classifications.append({
            "pad_id": permit.pad_id,
            "lat": permit.latitude,
            "lon": permit.longitude,
            "n_obs": len(obs),
            "classification": cls,
        })

    result = FirmQuarterSarSignal(
        ticker=ticker,
        fiscal_quarter_end=fiscal_quarter_end,
        decision_date_T=decision_date_T,
        n_pads_sampled=len(representative),
        n_newly_active=counts["newly_active"],
        n_continuously_active=counts["continuously_active"],
        n_idle=counts["idle"],
        n_observations_total=n_obs_total,
        pad_classifications=pad_classifications,
    )
    cache_path.write_text(json.dumps({
        "ticker": result.ticker,
        "fiscal_quarter_end": result.fiscal_quarter_end.isoformat(),
        "decision_date_T": result.decision_date_T.isoformat(),
        "n_pads_sampled": result.n_pads_sampled,
        "n_newly_active": result.n_newly_active,
        "n_continuously_active": result.n_continuously_active,
        "n_idle": result.n_idle,
        "n_observations_total": result.n_observations_total,
        "pad_classifications": result.pad_classifications,
    }))
    return result
