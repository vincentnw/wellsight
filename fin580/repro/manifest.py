"""Per-run manifest builder (spec Section 8.2).

Captures code state, data state, LLM state (provider/model/version/prompt SHAs),
environment, and pinned parameters. Empty TRC SHA signals stub-permit-dump
fallback per Plan Task 6 docstring."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


def _file_sha(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _dir_sha(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    for p in sorted(path.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            h.update(str(p.relative_to(path)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def _prompt_shas(prompts_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not prompts_dir.exists():
        return out
    for p in sorted(prompts_dir.glob("*.txt")):
        out[p.stem] = _file_sha(p)
    return out


_SEED_FUNCTION_DOC = "sha256(ticker|q_end|pad_id|cm_label)"


def _detect_sar_mode() -> str:
    """Read FIN580_SAR_MODE env var to record provenance of the SAR signal.
    'real_sentinel1' means real Microsoft Planetary Computer Sentinel-1 RTC
    backscatter; 'synthetic' (default) means the legacy literature-calibrated
    confusion-matrix generator."""
    import os
    mode = os.environ.get("FIN580_SAR_MODE", "synthetic")
    if mode not in ("real_sentinel1", "synthetic"):
        return f"unknown_{mode}"
    return mode


def build_manifest(
    *,
    run_id: str,
    run_dir: Path,
    llm_state: dict,
    parameters: dict,
    confusion_matrix_label: str = "target",
    modules_used: list[str] | None = None,
) -> dict:
    """Build the canonical run manifest. Caller passes per-agent llm_state with
    keys provider, model_id, model_version, temperature, prompt_sha,
    stability_check_passed.

    `modules_used` lists the dotted module names actually invoked in this run
    (e.g. fin580.agents.orchestrator, fin580.backtest.runner). Recorded so
    reruns can reproduce the exact code path.
    """
    repo_root = Path(__file__).resolve().parents[2]
    phase1_output = repo_root / "phase1" / "output"
    prompts_dir = repo_root / "fin580" / "agents" / "prompts"
    spec_path = repo_root / "docs" / "specs" / "2026-04-29-implementation-design.md"
    plan_path = repo_root / "docs" / "plans" / "2026-04-29-implementation-plan.md"
    return {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,  # Caller updates via finalize_manifest()
        "code_state": {
            "fin580_dir_sha": _dir_sha(repo_root / "fin580"),
            "phase1_dir_sha": _dir_sha(phase1_output),
            "docs_specs_sha": _dir_sha(repo_root / "docs" / "specs"),
            "docs_plans_sha": _dir_sha(repo_root / "docs" / "plans"),
            "spec_sha": _file_sha(spec_path),
            "plan_sha": _file_sha(plan_path),
            "requirements_lock_sha": _file_sha(repo_root / "requirements.txt"),
            "modules_used": modules_used or [],
        },
        "data_state": {
            "ibes_revenue_panel_sha": _file_sha(
                phase1_output / "ibes_revenue_coverage.csv"
            ),
            "ibes_detail_history_sha": _file_sha(
                phase1_output / "ibes_tr_ibes_sal_query11220958.csv"
            ),
            "compustat_fundq_sha": _file_sha(phase1_output / "compustat_fundq.csv"),
            "crsp_daily_sha": _file_sha(phase1_output / "crsp_daily.csv"),
            "permian_fraction_sha": _file_sha(phase1_output / "permian_fraction.csv"),
            "earnings_dates_sha": _file_sha(phase1_output / "earnings_dates.csv"),
            "fracfocus_permit_dump_sha": _file_sha(
                phase1_output / "permit_dump.csv"
            ),
            "fracfocus_permit_dump_provenance": "fracfocus_bulk_csv_2026_04_30",
            "yahoo_2025_supplement_sha": _file_sha(
                phase1_output / "yahoo_2025_supplement.csv"
            ),
            "wti_cache_sha": _file_sha(phase1_output / "eia_wti_weekly.csv"),
            "wti_provenance": "eia_rwtcw_xls",
            "bhi_rigcount_sha": _file_sha(
                phase1_output / "bhi_permian_rigcount_weekly.csv"
            ),
            "bhi_rigcount_provenance": "eia_dpr_permian_monthly_carryforward",
            # SAR mode: 'real_sentinel1' for the headline run via Microsoft
            # Planetary Computer; 'synthetic' for the legacy literature-
            # calibrated confusion-matrix generator (kept in code for
            # backwards-compat, not part of paper claims).
            "sar_mode": _detect_sar_mode(),
            "sar_change_detection_thresholds": {
                "activation_db": 1.5,
                "sustained_db": 0.5,
                "trailing_baseline_coefficient": 0.3,
            },
            "gdelt_cache_index_sha": _dir_sha(phase1_output / "gdelt_cache"),
            "sentinel1_firm_quarter_cache_index_sha": _dir_sha(
                phase1_output / "sentinel1_cache" / "firm_quarter_aggregates"
            ),
            "sentinel1_per_pad_cache_index_sha": _dir_sha(
                phase1_output / "sentinel1_cache"
            ),
            "synthetic_sar_confusion_matrix_label_legacy": confusion_matrix_label,
            "synthetic_sar_seed_function_legacy": _SEED_FUNCTION_DOC,
            "synthetic_sar_seed_function_sha_legacy": hashlib.sha256(
                _SEED_FUNCTION_DOC.encode()
            ).hexdigest(),
        },
        "llm_state": llm_state,
        "prompt_shas": _prompt_shas(prompts_dir),
        "env": {
            "python_version": sys.version,
            "platform": platform.platform(),
        },
        "parameters": parameters,
        "warnings": [],
    }


def finalize_manifest(manifest: dict, run_dir: Path) -> Path:
    """Stamp completed_at and persist."""
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    return write_manifest(manifest, run_dir)


def write_manifest(manifest: dict, run_dir: Path) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    out = run_dir / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2, default=str))
    return out
