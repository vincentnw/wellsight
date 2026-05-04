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
    SAR_CACHE_DIR,
    SarObservation,
    _open_stac_catalog,
    _pad_key,
    batch_read_pads_from_items,
    classify_pad_from_sar,
    fetch_pad_backscatter,
    stac_search_with_retry,
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

    # Round-robin from cohorts until we hit n_pads, deduping by
    # (pad_id, rounded coords). FracFocus occasionally lists the same well
    # twice (re-frac filings) and even re-emits identical pad_id rows with
    # micro-perturbed coordinates (~10-20m). Without dedup, the new batch-
    # read path's pad_id-keyed dict would collide and either waste a slot
    # (exact dup) or silently merge observations from two distinct wells
    # under one identity (coord-perturbed dup). Dedup at selection time
    # makes "25 pads" mean 25 actually-distinct radar-target panels.
    seen: set[tuple[str, float, float]] = set()
    out: list[Permit] = []
    cohorts = [active, recent, older]
    while len(out) < n_pads and any(cohorts):
        for c in cohorts:
            if c:
                p = c.pop(0)
                key = (p.pad_id, round(p.latitude, 4), round(p.longitude, 4))
                if key in seen:
                    continue
                seen.add(key)
                out.append(p)
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

    # v2.5 optimizations #2 + #3:
    #   #2 — do ONE STAC search per firm-quarter at the union bbox of all
    #        non-cached pads (was 25 per-pad searches; STAC is the failure-
    #        prone step under MS Planetary Computer load).
    #   #3 — open each scene ONCE per firm-quarter, clip windows for every
    #        non-cached pad from the in-memory raster (was 25 × ~150 = ~3750
    #        COG opens per cell; now ~150).
    #
    # Pads with prior per-pad cache hits skip both fetches entirely.
    AOI_BUFFER_DEG = 0.005
    # Composite-key dicts (pad_id, rounded lat, rounded lon) — same identity
    # we dedup on in _select_representative_pads, so two FracFocus rows with
    # the same pad_id but different coords stay distinct.
    cached_obs: dict[tuple[str, float, float], list] = {}
    pads_needing_fetch = []
    for permit in representative:
        cache_key = (
            f"{permit.pad_id}_{permit.latitude:.4f}_{permit.longitude:.4f}_"
            f"{fetch_start.isoformat()}_{fetch_end.isoformat()}"
        )
        cache_path_pad = SAR_CACHE_DIR / f"{cache_key}.json"
        permit_key = _pad_key(permit.pad_id, permit.latitude, permit.longitude)
        if cache_path_pad.exists():
            try:
                data = json.loads(cache_path_pad.read_text())
                cached_obs[permit_key] = [
                    SarObservation(
                        pad_id=d["pad_id"], lat=d["lat"], lon=d["lon"],
                        scene_id=d["scene_id"],
                        acquisition_date=date.fromisoformat(d["acquisition_date"]),
                        vv_mean_linear=d["vv_mean_linear"],
                        vv_mean_db=d["vv_mean_db"],
                        vh_mean_linear=d.get("vh_mean_linear"),
                    )
                    for d in data
                ]
            except (json.JSONDecodeError, KeyError, ValueError):
                pads_needing_fetch.append(permit)
        else:
            pads_needing_fetch.append(permit)

    fresh_obs: dict[tuple[str, float, float], list] = {}
    if pads_needing_fetch:
        lats = [p.latitude for p in pads_needing_fetch]
        lons = [p.longitude for p in pads_needing_fetch]
        union_bbox = [
            min(lons) - AOI_BUFFER_DEG,
            min(lats) - AOI_BUFFER_DEG,
            max(lons) + AOI_BUFFER_DEG,
            max(lats) + AOI_BUFFER_DEG,
        ]
        catalog = _open_stac_catalog()
        items = []
        if catalog is not None:
            items = stac_search_with_retry(
                catalog=catalog, bbox=union_bbox,
                start_date=fetch_start, end_date=fetch_end,
                max_scenes=200,
                label=f"{ticker} {fiscal_quarter_end.isoformat()}",
            )
        if items:
            fresh_obs, _counters = batch_read_pads_from_items(
                items=items,
                pads=[(p.pad_id, p.latitude, p.longitude) for p in pads_needing_fetch],
                start_date=fetch_start,
                end_date=fetch_end,
                aoi_buffer_deg=AOI_BUFFER_DEG,
                label=f"{ticker} {fiscal_quarter_end.isoformat()}",
            )
        else:
            # STAC search returned no items — every uncached pad gets empty obs
            fresh_obs = {
                _pad_key(p.pad_id, p.latitude, p.longitude): []
                for p in pads_needing_fetch
            }

    pad_obs_pairs: list[tuple] = []
    for permit in representative:
        k = _pad_key(permit.pad_id, permit.latitude, permit.longitude)
        obs = cached_obs.get(k, fresh_obs.get(k, []))
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
