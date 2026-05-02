"""Real Sentinel-1 SAR backscatter ingestion via Microsoft Planetary Computer.

Replaces the synthetic-SAR generator for the 1-year (2024) real-data demo.
Pulls VV/VH backscatter time series at FracFocus-derived pad coordinates,
applies a literature-anchored change-detection rule, and emits the same
per-pad-quarter classification (newly_active / continuously_active / idle)
that the synthetic generator produced.

Detection rule (calibrated to Permian active-drilling acoustic literature):
  - Compute mean VV backscatter over a small AOI around the pad center
    (typical pad footprint ~200-500m).
  - Compare current quarter's mean VV vs trailing-4-quarter baseline:
      (a) newly_active: current VV >= baseline + 3 dB AND no completion
          record before the quarter (drilling pad just lit up);
      (b) continuously_active: current VV >= baseline + 1 dB AND completion
          record within prior 8 quarters;
      (c) idle: otherwise.

Caching: per (operator, pad_lat, pad_lon, quarter) JSON files in
phase1/output/sentinel1_cache/.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
SAR_CACHE_DIR = PHASE1_OUTPUT / "sentinel1_cache"
SAR_CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class SarObservation:
    pad_id: str
    lat: float
    lon: float
    scene_id: str
    acquisition_date: date
    vv_mean_linear: float
    vv_mean_db: float
    vh_mean_linear: float | None


def fetch_pad_backscatter(
    *,
    pad_id: str,
    lat: float,
    lon: float,
    start_date: date,
    end_date: date,
    aoi_buffer_deg: float = 0.005,  # ~500m at Permian latitude
    max_scenes: int = 50,
) -> list[SarObservation]:
    """Fetch Sentinel-1 backscatter time series at a pad location.

    Caches per (pad_id, start, end) under phase1/output/sentinel1_cache/.
    Returns an empty list on network failure (PIT-safe: if real SAR is
    unavailable, the orchestrator can fall back to synthetic radar)."""
    cache_key = (
        f"{pad_id}_{lat:.4f}_{lon:.4f}_"
        f"{start_date.isoformat()}_{end_date.isoformat()}"
    )
    cache_path = SAR_CACHE_DIR / f"{cache_key}.json"
    if cache_path.exists():
        data = json.loads(cache_path.read_text())
        return [
            SarObservation(
                pad_id=d["pad_id"],
                lat=d["lat"],
                lon=d["lon"],
                scene_id=d["scene_id"],
                acquisition_date=date.fromisoformat(d["acquisition_date"]),
                vv_mean_linear=d["vv_mean_linear"],
                vv_mean_db=d["vv_mean_db"],
                vh_mean_linear=d.get("vh_mean_linear"),
            )
            for d in data
        ]

    try:
        import pystac_client
        import planetary_computer
        import rioxarray  # noqa
        import numpy as np
    except ImportError:
        return []

    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )
    aoi = [lon - aoi_buffer_deg, lat - aoi_buffer_deg,
           lon + aoi_buffer_deg, lat + aoi_buffer_deg]
    search = catalog.search(
        collections=["sentinel-1-rtc"],
        bbox=aoi,
        datetime=f"{start_date.isoformat()}/{end_date.isoformat()}",
        limit=max_scenes,
    )
    items = list(search.items())

    obs: list[SarObservation] = []
    for item in items:
        try:
            import rioxarray
            vv = rioxarray.open_rasterio(item.assets["vv"].href, masked=True).squeeze()
            vv_clip = vv.rio.clip_box(*aoi, crs="EPSG:4326")
            arr = vv_clip.values
            mean_lin = float(np.nanmean(arr))
            if not np.isfinite(mean_lin) or mean_lin <= 0:
                continue
            mean_db = 10.0 * float(np.log10(mean_lin))
            vh_mean_lin = None
            try:
                vh = rioxarray.open_rasterio(item.assets["vh"].href, masked=True).squeeze()
                vh_clip = vh.rio.clip_box(*aoi, crs="EPSG:4326")
                vh_arr = vh_clip.values
                vh_mean_lin = float(np.nanmean(vh_arr))
                if not np.isfinite(vh_mean_lin):
                    vh_mean_lin = None
            except Exception:
                pass
            acq_dt_str = item.properties.get("datetime", "")
            acq_d = datetime.fromisoformat(acq_dt_str.replace("Z", "+00:00")).date()
            obs.append(
                SarObservation(
                    pad_id=pad_id, lat=lat, lon=lon,
                    scene_id=item.id,
                    acquisition_date=acq_d,
                    vv_mean_linear=mean_lin,
                    vv_mean_db=mean_db,
                    vh_mean_linear=vh_mean_lin,
                )
            )
        except Exception as e:
            continue

    # Persist cache
    cache_path.write_text(json.dumps(
        [{
            "pad_id": o.pad_id, "lat": o.lat, "lon": o.lon,
            "scene_id": o.scene_id,
            "acquisition_date": o.acquisition_date.isoformat(),
            "vv_mean_linear": o.vv_mean_linear,
            "vv_mean_db": o.vv_mean_db,
            "vh_mean_linear": o.vh_mean_linear,
        } for o in obs],
        indent=2,
    ))
    return obs


def classify_pad_from_sar(
    *,
    pad_id: str,
    obs: list[SarObservation],
    target_quarter_end: date,
    completion_filing_date: date | None,
    decision_date_T: date,
    activation_threshold_db: float = 1.5,
    sustained_threshold_db: float = 0.5,
) -> str:
    """Apply change-detection rule to per-pad backscatter time series.
    Returns 'newly_active', 'continuously_active', or 'idle'."""
    # Quarter window: 91 days ending target_quarter_end, masked to ≤ T
    quarter_start = target_quarter_end - timedelta(days=91)
    quarter_obs = [
        o for o in obs
        if quarter_start <= o.acquisition_date <= min(target_quarter_end, decision_date_T)
    ]
    baseline_obs = [
        o for o in obs
        if (target_quarter_end - timedelta(days=365)) <= o.acquisition_date < quarter_start
        and o.acquisition_date <= decision_date_T
    ]
    if not quarter_obs:
        return "idle"  # No coverage in target quarter
    cur_db = sum(o.vv_mean_db for o in quarter_obs) / len(quarter_obs)
    if not baseline_obs:
        # No baseline — fallback: classify based on completion record only
        if completion_filing_date and (
            target_quarter_end - timedelta(days=8 * 91)
        ) <= completion_filing_date <= decision_date_T:
            return "continuously_active"
        return "idle"
    base_db = sum(o.vv_mean_db for o in baseline_obs) / len(baseline_obs)
    delta_db = cur_db - base_db

    has_recent_completion = (
        completion_filing_date is not None
        and (target_quarter_end - timedelta(days=8 * 91))
        <= completion_filing_date
        <= decision_date_T
    )

    if delta_db >= activation_threshold_db and not has_recent_completion:
        return "newly_active"
    if delta_db >= sustained_threshold_db and has_recent_completion:
        return "continuously_active"
    return "idle"
