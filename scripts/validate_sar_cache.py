"""Sanity-check the Sentinel-1 SAR cache before shipping it back.

Verifies that every JSON file is valid syntax, has plausible shape, and
flags pad-year files with too few acquisitions (suggests truncated COG
range-reads). Prints a concise summary.

Usage:
    python3 scripts/validate_sar_cache.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAR_DIR = ROOT / "phase1" / "output" / "sentinel1_cache"
FQ_DIR = SAR_DIR / "firm_quarter_aggregates"


def main() -> int:
    if not SAR_DIR.exists():
        print(f"❌ {SAR_DIR} does not exist — did the helper script run?")
        return 1

    pad_files = sorted(p for p in SAR_DIR.glob("*.json") if p.is_file())
    fq_files = sorted(FQ_DIR.glob("*.json")) if FQ_DIR.exists() else []

    print(f"Pad-year time-series files:    {len(pad_files)}")
    print(f"Firm-quarter aggregate files:  {len(fq_files)}")
    print()

    issues = 0

    # Validate pad-year files
    too_few_obs = []
    for p in pad_files:
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            print(f"❌ {p.name}: invalid JSON ({e})")
            issues += 1
            continue
        if not isinstance(data, list):
            print(f"❌ {p.name}: expected a list, got {type(data).__name__}")
            issues += 1
            continue
        if len(data) < 30:
            too_few_obs.append((p.name, len(data)))

    if too_few_obs:
        print(f"⚠️  {len(too_few_obs)} pad-year files have < 30 acquisitions "
              "(Sentinel-1 has ~50 visits/year — fewer suggests COG read failure):")
        for name, n in too_few_obs[:10]:
            print(f"     {name}: only {n} acquisitions")
        if len(too_few_obs) > 10:
            print(f"     ... and {len(too_few_obs) - 10} more")
        print()

    # Validate firm-quarter aggregates
    per_firm = Counter()
    quarters_seen = set()
    for p in fq_files:
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            print(f"❌ {p.name}: invalid JSON ({e})")
            issues += 1
            continue
        if data.get("n_pads_sampled", 0) > 0:
            per_firm[data.get("ticker", "?")] += 1
            quarters_seen.add(data.get("fiscal_quarter_end", ""))

    if per_firm:
        print(f"Firm-quarter aggregates with at least one pad sampled:")
        for f, n in sorted(per_firm.items()):
            print(f"     {f}: {n}")
        print()
        if quarters_seen:
            print(f"Distinct fiscal quarters covered: {len(quarters_seen)}")
            for q in sorted(quarters_seen):
                print(f"     {q}")
        print()

    if issues == 0:
        print("✅ No structural issues detected. Cache is ready to ship.")
    else:
        print(f"⚠️  {issues} structural issue(s) detected. Re-run "
              "scripts/fetch_sar_for_window.py for the affected windows.")

    print()
    print(f"Tip: zip the cache for upload with:")
    print(f"  zip -r sar_cache_$(whoami)_$(date +%Y%m%d).zip "
          f"phase1/output/sentinel1_cache/")

    return 0 if issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
