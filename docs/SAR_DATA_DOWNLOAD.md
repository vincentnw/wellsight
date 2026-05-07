# Collaborative Sentinel-1 SAR Data Download Guide

**Goal:** help extend the backtest to additional years (2022, 2023, 2025…) by
running the Sentinel-1 download helper on your own machine and shipping back
the resulting cache files. The lead author's laptop is the bottleneck — your
help directly accelerates the project.

---

## What you'll be doing

For each (firm × fiscal-quarter) cell in the requested window, the helper:

1. Picks 5 representative drilling pads for that firm from the FracFocus
   permit database (already in the repo).
2. For each pad, queries Microsoft Planetary Computer's STAC API for every
   Sentinel-1 RTC scene that covered the pad's coordinates over the prior
   365 days.
3. Reads a small ~500 m × 500 m AOI patch from each scene (cloud-optimised
   GeoTIFF range-read, not a full download).
4. Computes mean VV and VH backscatter for that patch → one scalar per
   acquisition per pad.
5. Saves the time series to JSON.
6. Aggregates to a firm-quarter classification (newly_active /
   continuously_active / idle counts) using the same +1.5 dB / +0.5 dB
   change-detection rule the system uses.

**Output**: small JSON files (each ~17 KB per pad-year, ~500 B per
firm-quarter aggregate). Ship those back to the lead author.

**Cost**: zero. Microsoft Planetary Computer is free, no auth required.
The data fetched is bandwidth-only (no API key, no quota you can blow).

---

## Setup (5 minutes)

You need **Python ≥ 3.10** and a few scientific packages.

```bash
# Clone the repo
git clone <repo-url>
cd FINAL

# Install only the deps needed for SAR ingestion (no LLM packages)
python3 -m pip install pystac-client planetary-computer rasterio rioxarray xarray pandas numpy
```

That's it. **No environment variables, no API keys, no auth, no WRDS access**
needed for SAR-only. Microsoft Planetary Computer is free and anonymous.

> ℹ️ The main project README documents API keys (`CEREBRAS_API_KEY`, etc.) but
> those are only needed if someone wants to re-run the multi-agent LLM pipeline
> end-to-end. For the SAR-fetch helper described here, you can ignore them.

---

## Run the helper

```bash
# Example: download SAR for the full 2022 calendar year
python3 scripts/fetch_sar_for_window.py --start 2022Q1 --end 2022Q4

# Or: a specific firm subset (faster, useful for parallel collaboration)
python3 scripts/fetch_sar_for_window.py --start 2023Q1 --end 2023Q4 --firms FANG,EOG,DVN

# Or: a specific quarter only
python3 scripts/fetch_sar_for_window.py --start 2025Q3 --end 2025Q3
```

The helper prints progress per cell. **Each cell takes about 5–10 minutes**
of wall-clock (sequential per-pad SAR fetches over HTTPS to Microsoft Azure
Blob storage). For an entire year (~36 cells with FracFocus coverage), expect
**3–6 hours**.

You can stop and restart any time — every cell is checkpointed, and re-running
the helper skips cells that already have a cached aggregate.

---

## Coordinating who downloads what

To avoid duplicate work, the team splits ranges by **firm** or **year**.
Suggested splits for 78 cells (2022 + 2023):

| Person | Firms | Cells |
|---|---|---|
| Vincent | CTRA, OXY, MTDR | ~24 |
| Friend A | FANG, EOG, DVN | ~24 |
| Friend B | PR, OVV, SM | ~24 |
| (CRGY has 0 Permian permits, skipped automatically) | | 0 |

(Pick whatever split makes sense; the helper is idempotent so duplicates
don't cause harm — they just waste your bandwidth.)

---

## Where the cache files end up

After the helper runs, two directories are populated:

```
phase1/output/sentinel1_cache/
├── 42003478140000_32.4215_-102.2200_2023-04-01_2024-03-31.json   ← per-pad time series (~17 KB each)
├── 42003478180000_32.4211_-102.2217_2024-01-01_2024-03-31.json
├── ...
└── firm_quarter_aggregates/
    ├── FANG_2022-03-31_2022-04-19_n5.json   ← per-cell aggregate (~500 B each)
    ├── FANG_2022-06-30_2022-07-22_n5.json
    └── ...
```

**Ship back both of those subtrees** — preferably as a single zip file —
and we'll merge them into the canonical cache.

```bash
# Quick zip of just the new files (replace 2022 with whatever you ran)
zip -r sar_cache_yourname_2022.zip phase1/output/sentinel1_cache/
```

---

## Quality checks

Before shipping back, run the included validator:

```bash
python3 scripts/validate_sar_cache.py
```

It will:
- Verify every JSON is valid syntax
- Confirm acquisition dates fall within the requested window
- Flag any pad-year files with < 30 acquisitions (Sentinel-1 has ~50 visits/year,
  so much fewer = something went wrong with the COG range-reads)
- Print a summary of how many cells you covered

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: rasterio` | system libs (GDAL) missing | `brew install gdal` (macOS) or `apt install libgdal-dev` (Linux), then re-pip-install |
| `pystac_client.exceptions.APIError` | transient Microsoft Planetary Computer 5xx | re-run the helper; it skips already-cached cells |
| `The request exceeded the maximum allowed time` | Microsoft Planetary Computer scene timeout | re-run; the helper retries failed cells |
| Cell takes > 30 minutes | one slow scene blocked the read | kill helper with Ctrl+C, re-run; checkpoint resumes |

---

## What to do if you have time and want to push further

After the basic 2022 + 2023 fetch, you could also:

- **Bump `--pads-per-firm` from 5 to 10** for higher-fidelity firm-quarter
  signals (paper §12.3 documents this as a known limitation).
- **Try the no-FracFocus mode** that samples pads from operator-public
  geographic centroids if you have time to write a small wrapper. (Not
  needed for the basic backtest extension.)
- **Pull 2025 Q4** once Q4 earnings come in (typically Feb-Mar 2026 for
  the 8 firms not yet reporting at the time of writing).

---

## Questions / handoff

DM the lead author with the zip file once you're done. Or commit it to
the team's shared folder. Either way the merge step is `unzip` into
`phase1/output/sentinel1_cache/` — every cache file is keyed by content
so duplicates resolve cleanly.

Thanks for helping extend the empirical window. 🙏
