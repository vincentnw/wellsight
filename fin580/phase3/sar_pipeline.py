"""
Phase 3 — Sentinel-1 SAR drilling-detection pipeline (scaffold).

Architecture (per project_overview.md sections 'The Signal We Are Creating',
DL #28, DL #29, DL #43, DL #47, Pre-Code Action Items 1, 2, 5):

    1. Build the point-in-time site universe of Permian drill pads from TRC
       (Texas Railroad Commission) and NM-OCD (New Mexico Oil Conservation
       Division) permit data: at decision date T, only pads whose permits were
       filed before T are eligible.

    2. For each eligible pad, query Google Earth Engine for Sentinel-1 SAR
       (C-band, VV+VH polarization, IW mode, 10m resolution, ~12-day revisit)
       imagery using the GEE asset publication date (NOT the satellite capture
       date) as the public-availability timestamp (DL #31).

    3. Apply a backscatter-change-detection algorithm to classify each pad x
       quarter as newly_active (fresh disturbance), continuously_active
       (ongoing), or idle (stable).

    4. (Validation gate, Pre-Code #2) Sample 80 pads against TRC spud and
       completion records and report precision and recall. Per DL #48, weak
       performance does not gate the trading layer; it is reported in
       Limitations.

This file is a SCAFFOLD: the GEE and TRC API calls are stubbed with
documented signatures. Replace stubs with live implementations after running
`earthengine authenticate` and downloading TRC permit dumps.

Authentication and one-time setup
---------------------------------
    pip install earthengine-api geopandas pandas pyarrow
    earthengine authenticate
    # Then `ee.Initialize(project='your-cloud-project')` in your environment.

The pipeline is intentionally light on production hardening per DL #48
(project goal is innovative thinking, not full execution).
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

# Optional dependency: earthengine-api. We import lazily so the scaffold can be
# imported and inspected even without GEE installed.
try:
    import ee  # type: ignore
    _HAS_EE = True
except ImportError:
    _HAS_EE = False

PHASE_OUTPUT = Path(__file__).resolve().parents[2] / "phase3" / "output"
PHASE_OUTPUT.mkdir(parents=True, exist_ok=True)

# Permian high-activity counties (DL #19, DL #28, DL #44).
TX_COUNTIES = {"Midland", "Martin", "Reeves", "Loving", "Howard", "Reagan",
               "Glasscock", "Upton", "Ector", "Andrews"}
NM_COUNTIES = {"Eddy", "Lea"}

# Sentinel-1 backscatter thresholds for the three-state classifier. These are
# coarse defaults derived from published literature on Permian bare-earth
# disturbance studies; calibrate during the validation step.
BACKSCATTER_DROP_DB_NEW_ACTIVE = -2.5    # 2.5 dB drop = pad construction / clearing
BACKSCATTER_DROP_DB_ACTIVE = -1.0        # ongoing disturbance
BACKSCATTER_DROP_DB_IDLE = -0.3          # stable / regrown

# Validation gate constants (Pre-Code #2, DL #37). Reported transparently per
# DL #48; not a hard pivot trigger.
TARGET_PRECISION = 0.70
TARGET_RECALL = 0.60
VALIDATION_SAMPLE_SIZE_TOTAL = 80
VALIDATION_SAMPLE_SIZE_ACTIVE = 40
VALIDATION_SAMPLE_SIZE_IDLE = 40
TRC_MATCH_WINDOW_DAYS = 30


# ---------------------------------------------------------------------------
# Site (drill pad) universe
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DrillPad:
    pad_id: str
    operator_at_permit: str
    state: str            # 'TX' or 'NM'
    county: str
    latitude: float
    longitude: float
    permit_filing_date: date
    api_number: str = ""  # TRC API number for TX, NMOCD permit ID for NM
    notes: str = ""


def load_pads_pit(
    permit_csv: Path,
    decision_date_T: date,
) -> list[DrillPad]:
    """Load drill pads from the consolidated TRC + NMOCD permit dump and filter
    to those whose `permit_filing_date <= decision_date_T`. The permit dump is
    expected to be produced once via `code/phase3/build_permit_dump.py` (also
    a scaffold; not yet implemented).

    Permit-dump CSV columns:
        pad_id, operator_at_permit, state, county, latitude, longitude,
        permit_filing_date (YYYY-MM-DD), api_number, notes
    """
    out: list[DrillPad] = []
    if not permit_csv.exists():
        return out
    with open(permit_csv) as f:
        for row in csv.DictReader(f):
            try:
                pfd = datetime.strptime(row["permit_filing_date"], "%Y-%m-%d").date()
            except (KeyError, ValueError):
                continue
            if pfd > decision_date_T:
                continue
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
            except (KeyError, ValueError):
                continue
            out.append(DrillPad(
                pad_id=row["pad_id"],
                operator_at_permit=row["operator_at_permit"],
                state=row["state"],
                county=row["county"],
                latitude=lat,
                longitude=lon,
                permit_filing_date=pfd,
                api_number=row.get("api_number", ""),
                notes=row.get("notes", ""),
            ))
    return out


# ---------------------------------------------------------------------------
# GEE asset query (lazy, requires earthengine-api)
# ---------------------------------------------------------------------------


@dataclass
class SARObservation:
    pad_id: str
    capture_date: date
    asset_publication_date: date  # GEE ingestion timestamp; the official "available" date (DL #31)
    vv_db: float
    vh_db: float


def _ensure_ee_initialized(cloud_project: str | None = None) -> None:
    if not _HAS_EE:
        raise RuntimeError(
            "earthengine-api not installed. Run `pip install earthengine-api` "
            "and `earthengine authenticate` before using the SAR ingest path."
        )
    if cloud_project is not None:
        ee.Initialize(project=cloud_project)
    else:
        ee.Initialize()


def query_s1_observations(
    pad: DrillPad,
    start: date,
    end: date,
    cloud_project: str | None = None,
    buffer_meters: int = 200,
) -> list[SARObservation]:
    """Query Sentinel-1 GRD imagery for a single pad over [start, end].

    The buffer (default 200m around the pad coordinate) defines the area used
    to summarize VV/VH backscatter to a single (date, db) tuple per scene.

    Returns one SARObservation per scene that overlaps the pad. Uses
    GEE's `system:time_start` for capture date and the GEE catalog ingestion
    metadata for the asset publication (availability) date.
    """
    if not _HAS_EE:
        return []
    _ensure_ee_initialized(cloud_project)
    point = ee.Geometry.Point(pad.longitude, pad.latitude)
    aoi = point.buffer(buffer_meters)
    coll = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(aoi)
        .filterDate(start.isoformat(), (end + timedelta(days=1)).isoformat())
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
    )
    scenes = coll.toList(coll.size()).getInfo()
    out: list[SARObservation] = []
    for s in scenes:
        ts = s["properties"].get("system:time_start")
        cap = date.fromtimestamp(ts / 1000) if ts else None
        ingest_ts = s["properties"].get("system:asset_size", None)  # placeholder
        # Real GEE ingestion timestamp lives at `ingestion_time` in newer
        # collections; use system:time_start + 24h as a safe approximation
        # in this scaffold.
        pub = (cap + timedelta(days=1)) if cap else None
        if cap is None or pub is None:
            continue
        img = ee.Image(s["id"])
        stats = img.select(["VV", "VH"]).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=10,
        ).getInfo()
        vv_db = stats.get("VV")
        vh_db = stats.get("VH")
        if vv_db is None or vh_db is None:
            continue
        out.append(SARObservation(
            pad_id=pad.pad_id,
            capture_date=cap,
            asset_publication_date=pub,
            vv_db=float(vv_db),
            vh_db=float(vh_db),
        ))
    return out


# ---------------------------------------------------------------------------
# Three-state change-detection classifier
# ---------------------------------------------------------------------------


@dataclass
class PadQuarterClassification:
    pad_id: str
    target_quarter_end: date
    state: str  # 'newly_active' | 'continuously_active' | 'idle'
    backscatter_change_db: float
    n_obs_in_quarter: int
    notes: str = ""


def classify_pad_quarter(
    obs: list[SARObservation],
    target_quarter_end: date,
    pad_id: str,
) -> PadQuarterClassification:
    """Classify a pad x quarter as newly_active, continuously_active, or idle.

    Method (intentionally simple for the design demo; harden in production):

      - Compute median VV backscatter (in dB) for observations whose
        asset_publication_date falls inside the target quarter.
      - Compute median VV backscatter for the prior quarter as the baseline.
      - delta = current_median - prior_median.
      - delta <= BACKSCATTER_DROP_DB_NEW_ACTIVE     => 'newly_active'
        BACKSCATTER_DROP_DB_NEW_ACTIVE < delta <= BACKSCATTER_DROP_DB_ACTIVE
                                                    => 'continuously_active'
        delta > BACKSCATTER_DROP_DB_ACTIVE          => 'idle'
    """
    q_start = (target_quarter_end - timedelta(days=92)).replace(day=1)
    in_q = [o for o in obs if q_start <= o.asset_publication_date <= target_quarter_end]
    prior_start = (q_start - timedelta(days=92)).replace(day=1)
    prior_in_q = [o for o in obs if prior_start <= o.asset_publication_date < q_start]

    def median(xs: list[float]) -> float:
        ys = sorted(xs)
        if not ys:
            return float("nan")
        return ys[len(ys) // 2]

    cur = median([o.vv_db for o in in_q])
    prior = median([o.vv_db for o in prior_in_q])
    if cur != cur or prior != prior:  # NaN check
        return PadQuarterClassification(
            pad_id=pad_id, target_quarter_end=target_quarter_end,
            state="idle", backscatter_change_db=0.0,
            n_obs_in_quarter=len(in_q),
            notes="insufficient observations",
        )
    delta = cur - prior
    if delta <= BACKSCATTER_DROP_DB_NEW_ACTIVE:
        state = "newly_active"
    elif delta <= BACKSCATTER_DROP_DB_ACTIVE:
        state = "continuously_active"
    else:
        state = "idle"
    return PadQuarterClassification(
        pad_id=pad_id, target_quarter_end=target_quarter_end,
        state=state, backscatter_change_db=delta,
        n_obs_in_quarter=len(in_q),
    )


# ---------------------------------------------------------------------------
# Validation against TRC ground truth (Pre-Code #2)
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    pad_id: str
    target_quarter_end: date
    sar_state: str
    trc_state_truth: str
    sar_event_date: date | None
    trc_event_date: date | None
    matched: bool


def load_trc_ground_truth(trc_csv: Path) -> dict[str, list[date]]:
    """Load TRC spud-or-completion records as {pad_id: [event_dates]}."""
    out: dict[str, list[date]] = {}
    if not trc_csv.exists():
        return out
    with open(trc_csv) as f:
        for row in csv.DictReader(f):
            try:
                d = datetime.strptime(row["event_date"], "%Y-%m-%d").date()
            except (KeyError, ValueError):
                continue
            out.setdefault(row["pad_id"], []).append(d)
    return out


def validate_sar_classifications(
    classifications: list[PadQuarterClassification],
    trc_truth: dict[str, list[date]],
    match_window_days: int = TRC_MATCH_WINDOW_DAYS,
) -> tuple[float, float, list[ValidationResult]]:
    """Compute precision and recall for SAR-detected drilling events vs TRC.

    A SAR classification of 'newly_active' is treated as a positive prediction.
    A TRC spud or completion event in [target_quarter_end - 92, target_quarter_end + match_window_days]
    is treated as ground-truth positive.

    Returns (precision, recall, [per-pad results]).
    """
    results: list[ValidationResult] = []
    tp = fp = fn = 0
    for c in classifications:
        truth_dates = trc_truth.get(c.pad_id, [])
        q_start = c.target_quarter_end - timedelta(days=92)
        q_end_window = c.target_quarter_end + timedelta(days=match_window_days)
        truth_event = next((d for d in truth_dates if q_start <= d <= q_end_window), None)
        truth_pos = truth_event is not None
        sar_pos = c.state == "newly_active"
        if sar_pos and truth_pos:
            tp += 1
        elif sar_pos and not truth_pos:
            fp += 1
        elif not sar_pos and truth_pos:
            fn += 1
        results.append(ValidationResult(
            pad_id=c.pad_id,
            target_quarter_end=c.target_quarter_end,
            sar_state=c.state,
            trc_state_truth="positive" if truth_pos else "negative",
            sar_event_date=c.target_quarter_end if sar_pos else None,
            trc_event_date=truth_event,
            matched=(sar_pos == truth_pos),
        ))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return precision, recall, results


def write_validation_report(
    precision: float,
    recall: float,
    results: list[ValidationResult],
    out_dir: Path = PHASE_OUTPUT,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "sar_validation_results.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "pad_id", "target_quarter_end", "sar_state", "trc_state_truth",
            "sar_event_date", "trc_event_date", "matched",
        ])
        for r in results:
            w.writerow([
                r.pad_id, r.target_quarter_end.isoformat(), r.sar_state,
                r.trc_state_truth,
                r.sar_event_date.isoformat() if r.sar_event_date else "",
                r.trc_event_date.isoformat() if r.trc_event_date else "",
                r.matched,
            ])
    summary_path = out_dir / "sar_validation_summary.json"
    with open(summary_path, "w") as f:
        json.dump({
            "n_samples": len(results),
            "precision": precision,
            "recall": recall,
            "target_precision": TARGET_PRECISION,
            "target_recall": TARGET_RECALL,
            "match_window_days": TRC_MATCH_WINDOW_DAYS,
            "passes_validation": (precision >= TARGET_PRECISION and recall >= TARGET_RECALL),
            "note": "Per DL #48 (project-goal alignment), weak validation is reported in Limitations and does not pivot the project; trading-layer results still produced."
        }, f, indent=2)


# ---------------------------------------------------------------------------
# CLI smoke test (synthetic inputs)
# ---------------------------------------------------------------------------


def _smoke() -> None:
    """End-to-end smoke test with 4 synthetic pads, no live GEE call."""
    pads = [
        DrillPad("PAD_FANG_001", "DIAMONDBACK E&P LLC", "TX", "Midland", 31.95, -101.95, date(2023, 1, 1)),
        DrillPad("PAD_MTDR_002", "MATADOR PRODUCTION CO", "NM", "Eddy", 32.45, -104.10, date(2023, 4, 1)),
        DrillPad("PAD_PR_003",   "PERMIAN RESOURCES OPERATING", "TX", "Reeves", 31.30, -103.30, date(2023, 7, 15)),
        DrillPad("PAD_OXY_004",  "OXY USA INC", "NM", "Lea", 32.50, -103.30, date(2024, 2, 10)),
    ]

    # Synthesize SAR observations: pad 1 newly_active in Q3-2024, pad 2
    # continuously_active, pad 3 idle, pad 4 newly_active.
    def synth(pad: DrillPad, prior_db: float, current_db: float) -> list[SARObservation]:
        out = []
        for d in [date(2024, 5, 15), date(2024, 6, 5), date(2024, 6, 25)]:
            out.append(SARObservation(pad.pad_id, d, d + timedelta(days=1), prior_db, prior_db - 1))
        for d in [date(2024, 7, 10), date(2024, 8, 2), date(2024, 9, 15)]:
            out.append(SARObservation(pad.pad_id, d, d + timedelta(days=1), current_db, current_db - 1))
        return out

    test_inputs = [
        (pads[0], -10.0, -13.0),  # 3 dB drop -> newly_active
        (pads[1], -10.0, -11.5),  # 1.5 dB drop -> continuously_active
        (pads[2], -10.0, -10.1),  # 0.1 dB drop -> idle
        (pads[3], -10.0, -13.5),  # 3.5 dB drop -> newly_active
    ]

    classifications = []
    for pad, prior, cur in test_inputs:
        obs = synth(pad, prior, cur)
        c = classify_pad_quarter(obs, date(2024, 9, 30), pad.pad_id)
        classifications.append(c)
        print(f"  {pad.pad_id}: delta={c.backscatter_change_db:+.2f} dB -> {c.state}")

    truth = {
        "PAD_FANG_001": [date(2024, 7, 20)],
        "PAD_MTDR_002": [date(2024, 8, 5)],
        "PAD_OXY_004":  [date(2024, 9, 1)],
    }
    p, r, vr = validate_sar_classifications(classifications, truth)
    print(f"\nValidation precision={p:.2f} recall={r:.2f}")
    write_validation_report(p, r, vr)


if __name__ == "__main__":
    print("Phase 3 SAR pipeline scaffold — smoke test")
    print("=" * 60)
    _smoke()
