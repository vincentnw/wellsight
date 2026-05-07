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
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

# GDAL/rasterio HTTP timeouts — applied BEFORE rasterio is imported anywhere.
# Without these, a single slow Microsoft Planetary Computer COG range-read can
# hang indefinitely (we've seen >30 min hangs). With these, any single read
# that stalls for >30s of low traffic, or exceeds 60s total, is killed and
# the per-scene try/except in fetch_pad_backscatter skips that scene.
os.environ.setdefault("GDAL_HTTP_TIMEOUT", "60")          # max 60s per HTTP request
os.environ.setdefault("GDAL_HTTP_LOW_SPEED_TIME", "30")   # kill if <1KB/s for 30s
os.environ.setdefault("GDAL_HTTP_LOW_SPEED_LIMIT", "1000")
os.environ.setdefault("GDAL_HTTP_CONNECTTIMEOUT", "20")   # max 20s to establish

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
SAR_CACHE_DIR = PHASE1_OUTPUT / "sentinel1_cache"
SAR_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _bind_timeout(method, default_timeout: float):
    """Wrap a requests.Session.request method to inject a default timeout.
    Used so pystac_client's HTTP calls can't hang forever."""
    def wrapped(*args, **kwargs):
        kwargs.setdefault("timeout", default_timeout)
        return method(*args, **kwargs)
    return wrapped


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


def _open_stac_catalog():
    """Open the Microsoft Planetary Computer STAC catalog with a 45s HTTP
    timeout. Returns the catalog or None on open-time failure."""
    try:
        import pystac_client
        import planetary_computer
    except ImportError:
        return None
    try:
        try:
            return pystac_client.Client.open(
                "https://planetarycomputer.microsoft.com/api/stac/v1",
                modifier=planetary_computer.sign_inplace,
                timeout=45,
            )
        except TypeError:
            return pystac_client.Client.open(
                "https://planetarycomputer.microsoft.com/api/stac/v1",
                modifier=planetary_computer.sign_inplace,
            )
    except Exception as e:
        print(f"  [sentinel1] STAC open failed: {type(e).__name__}: {str(e)[:80]}")
        return None


def stac_search_with_retry(
    *,
    catalog,
    bbox: list[float],
    start_date: date,
    end_date: date,
    max_scenes: int = 50,
    label: str = "",
) -> list:
    """STAC search with progressive backoff. Returns items list or [] on
    persistent failure. Microsoft Planetary Computer (discussion #246) does
    NOT publish per-IP rate limits; 503/504 / timeouts are transient backend
    overload, so retry-with-backoff is the recommended pattern.

    `label` is used only in log messages (e.g. "FANG 2024Q3" or "pad 4200347...").
    """
    import random as _r
    import time as _t
    BACKOFFS = [30, 60, 120]  # seconds; 4 attempts total = 1 + 3 retries
    last_err: Exception | None = None
    for attempt in range(len(BACKOFFS) + 1):
        try:
            search = catalog.search(
                collections=["sentinel-1-rtc"],
                bbox=bbox,
                datetime=f"{start_date.isoformat()}/{end_date.isoformat()}",
                limit=max_scenes,
            )
            return list(search.items())
        except Exception as e:
            last_err = e
            if attempt < len(BACKOFFS):
                wait = BACKOFFS[attempt] + _r.uniform(0, 10)
                print(f"  [sentinel1] {label} STAC attempt {attempt+1} failed "
                      f"({type(e).__name__}); retry in {wait:.0f}s")
                _t.sleep(wait)
                continue
    print(f"  [sentinel1] {label} STAC failed after {len(BACKOFFS)+1} attempts: "
          f"{type(last_err).__name__}: {str(last_err)[:80]}")
    return []


def fetch_pad_backscatter(
    *,
    pad_id: str,
    lat: float,
    lon: float,
    start_date: date,
    end_date: date,
    aoi_buffer_deg: float = 0.005,  # ~500m at Permian latitude
    max_scenes: int = 50,
    prefetched_items: list | None = None,
) -> list[SarObservation]:
    """Fetch Sentinel-1 backscatter time series at a pad location.

    Caches per (pad_id, start, end) under phase1/output/sentinel1_cache/.
    Returns an empty list on network failure (PIT-safe: if real SAR is
    unavailable, the orchestrator can fall back to synthetic radar).

    `prefetched_items` is an optimization: when fetching multiple pads for the
    same firm-quarter the caller can run ONE STAC search at a union bbox and
    pass the resulting items list here. We then skip the per-pad STAC search
    (which is the failure-prone step under MS Planetary Computer load).
    """
    cache_key = (
        f"{pad_id}_{lat:.4f}_{lon:.4f}_"
        f"{start_date.isoformat()}_{end_date.isoformat()}"
    )
    cache_path = SAR_CACHE_DIR / f"{cache_key}.json"
    if cache_path.exists():
        try:
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
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Corrupt cache — fall through to fresh fetch
            print(f"  [sentinel1] pad {pad_id} cache corrupt ({type(e).__name__}); refetching")

    try:
        import rioxarray  # noqa
        import numpy as np
    except ImportError:
        return []

    aoi = [lon - aoi_buffer_deg, lat - aoi_buffer_deg,
           lon + aoi_buffer_deg, lat + aoi_buffer_deg]

    # Source the STAC items: caller-provided (one search per firm-quarter,
    # the v2.5 optimization) or fall back to a per-pad search (legacy path,
    # used when the function is called directly).
    if prefetched_items is not None:
        items = prefetched_items
    else:
        catalog = _open_stac_catalog()
        if catalog is None:
            return []
        items = stac_search_with_retry(
            catalog=catalog, bbox=aoi,
            start_date=start_date, end_date=end_date,
            max_scenes=max_scenes, label=f"pad {pad_id}",
        )
        if not items:
            return []

    obs: list[SarObservation] = []
    for item in items:
        try:
            # v2.5 optimization #1: classifier uses VV only, so we no longer
            # read VH. Halves per-scene raster I/O and matches the documented
            # change-detection rule which is purely VV-based.
            vv = rioxarray.open_rasterio(item.assets["vv"].href, masked=True).squeeze()
            vv_clip = vv.rio.clip_box(*aoi, crs="EPSG:4326")
            arr = vv_clip.values
            mean_lin = float(np.nanmean(arr))
            if not np.isfinite(mean_lin) or mean_lin <= 0:
                continue
            mean_db = 10.0 * float(np.log10(mean_lin))
            acq_dt_str = item.properties.get("datetime", "")
            acq_d = datetime.fromisoformat(acq_dt_str.replace("Z", "+00:00")).date()
            obs.append(
                SarObservation(
                    pad_id=pad_id, lat=lat, lon=lon,
                    scene_id=item.id,
                    acquisition_date=acq_d,
                    vv_mean_linear=mean_lin,
                    vv_mean_db=mean_db,
                    vh_mean_linear=None,  # not read in v2.5+; classifier is VV-only
                )
            )
        except Exception as e:
            continue

    # Persist cache atomically so a concurrent reader (or another fetch shell
    # racing on the same pad-year) never sees a half-written file.
    payload = json.dumps(
        [{
            "pad_id": o.pad_id, "lat": o.lat, "lon": o.lon,
            "scene_id": o.scene_id,
            "acquisition_date": o.acquisition_date.isoformat(),
            "vv_mean_linear": o.vv_mean_linear,
            "vv_mean_db": o.vv_mean_db,
            "vh_mean_linear": o.vh_mean_linear,
        } for o in obs],
        indent=2,
    )
    tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    tmp_path.write_text(payload)
    import os as _os
    _os.replace(tmp_path, cache_path)
    return obs


def _pad_key(pad_id: str, lat: float, lon: float) -> tuple[str, float, float]:
    """Composite identity for a pad. Same `pad_id` can appear in FracFocus
    with slightly different coordinates (~10-20m); keying by pad_id alone
    would silently merge observations from physically distinct wells. We
    round to 4 decimal places (~10m at the Permian latitude) so floating-
    point representation jitter doesn't fragment one pad into many keys."""
    return (pad_id, round(lat, 4), round(lon, 4))


def batch_read_pads_from_items(
    *,
    items: list,
    pads: list[tuple[str, float, float]],  # [(pad_id, lat, lon), ...]
    start_date: date,
    end_date: date,
    aoi_buffer_deg: float = 0.005,
    label: str = "",
) -> tuple[dict[tuple[str, float, float], list[SarObservation]], dict[str, int]]:
    """v2.5 optimization #3: open each scene ONCE per firm-quarter, clip
    a small window for every pad from the in-memory raster, and accumulate
    per-pad observations.

    Previously each pad iterated all ~50-200 scenes individually with its own
    `rioxarray.open_rasterio` call → 25 pads × ~150 scenes ≈ 3,750 COG opens
    per cell. This function collapses that to one open per scene (~50-200 per
    cell) and clips per-pad in memory. Per-pad clips are nearly free
    (numpy/xarray slicing), so the dominant cost becomes the per-scene COG
    open.

    Per-pad cache files are written after the batch completes for backward
    compatibility — `fetch_pad_backscatter` callers still get cache hits.
    Pads passed in here are assumed to have NO existing cache (caller filters
    with the per-pad cache check first); we don't double-check.

    Returns:
        (per_pad_obs, counters)
        per_pad_obs: {pad_id: [SarObservation, ...]}
        counters:    {"n_scenes": int, "n_scene_reads": int,
                      "n_pad_samples": int, "n_pad_skips_offscene": int}

    Per-pad cache files are written before return.
    """
    counters = {"n_scenes": len(items), "n_scene_reads": 0,
                "n_pad_samples": 0, "n_pad_skips_offscene": 0}
    if not items or not pads:
        return ({_pad_key(pid, lat, lon): [] for pid, lat, lon in pads}, counters)

    try:
        import rioxarray  # noqa
        import numpy as np
    except ImportError:
        return ({_pad_key(pid, lat, lon): [] for pid, lat, lon in pads}, counters)

    per_pad: dict[tuple[str, float, float], list[SarObservation]] = {
        _pad_key(pid, lat, lon): [] for pid, lat, lon in pads
    }

    for item in items:
        try:
            vv = rioxarray.open_rasterio(
                item.assets["vv"].href, masked=True
            ).squeeze()
            counters["n_scene_reads"] += 1
        except Exception:
            continue
        acq_dt_str = item.properties.get("datetime", "")
        try:
            acq_d = datetime.fromisoformat(acq_dt_str.replace("Z", "+00:00")).date()
        except Exception:
            continue

        # Clip a small AOI window for each pad from the same in-memory raster.
        # Pads outside the scene's data extent yield empty / non-finite arrays
        # and are skipped without re-opening the COG.
        for pad_id, lat, lon in pads:
            aoi = [lon - aoi_buffer_deg, lat - aoi_buffer_deg,
                   lon + aoi_buffer_deg, lat + aoi_buffer_deg]
            try:
                vv_clip = vv.rio.clip_box(*aoi, crs="EPSG:4326")
                arr = vv_clip.values
            except Exception:
                counters["n_pad_skips_offscene"] += 1
                continue
            if arr.size == 0:
                counters["n_pad_skips_offscene"] += 1
                continue
            with np.errstate(all="ignore"):
                mean_lin = float(np.nanmean(arr))
            if not np.isfinite(mean_lin) or mean_lin <= 0:
                counters["n_pad_skips_offscene"] += 1
                continue
            mean_db = 10.0 * float(np.log10(mean_lin))
            per_pad[_pad_key(pad_id, lat, lon)].append(
                SarObservation(
                    pad_id=pad_id, lat=lat, lon=lon,
                    scene_id=item.id,
                    acquisition_date=acq_d,
                    vv_mean_linear=mean_lin,
                    vv_mean_db=mean_db,
                    vh_mean_linear=None,
                )
            )
            counters["n_pad_samples"] += 1

    # Persist per-pad cache files atomically (backward-compat with
    # fetch_pad_backscatter readers). The on-disk cache key embeds lat/lon
    # to 4 decimal places already, so the disk format is consistent with
    # the in-memory composite key.
    import os as _os
    for pad_id, lat, lon in pads:
        cache_key = (
            f"{pad_id}_{lat:.4f}_{lon:.4f}_"
            f"{start_date.isoformat()}_{end_date.isoformat()}"
        )
        cache_path = SAR_CACHE_DIR / f"{cache_key}.json"
        if cache_path.exists():
            continue  # someone else wrote it (race-safe)
        payload = json.dumps(
            [{
                "pad_id": o.pad_id, "lat": o.lat, "lon": o.lon,
                "scene_id": o.scene_id,
                "acquisition_date": o.acquisition_date.isoformat(),
                "vv_mean_linear": o.vv_mean_linear,
                "vv_mean_db": o.vv_mean_db,
                "vh_mean_linear": o.vh_mean_linear,
            } for o in per_pad[_pad_key(pad_id, lat, lon)]],
            indent=2,
        )
        tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
        tmp_path.write_text(payload)
        _os.replace(tmp_path, cache_path)

    if label:
        print(f"  [sentinel1] {label} batch-read: {counters['n_scenes']} items, "
              f"{counters['n_scene_reads']} COG opens, "
              f"{counters['n_pad_samples']} pad samples, "
              f"{counters['n_pad_skips_offscene']} pad-clips skipped")
    return (per_pad, counters)


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
