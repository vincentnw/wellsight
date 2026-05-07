# FIN 580 — Multi-Agent Satellite-Based Trading System

A multi-agent LLM trading system that uses **real Sentinel-1 SAR satellite radar**
to detect drilling activity at Permian-basin oil-and-gas pads, combines it with
**point-in-time IBES analyst consensus** and **GDELT news verification**, and
issues pre-earnings long trades for 10 Permian-focused E&P stocks. Evaluated
against 9 deterministic baselines on real CRSP+Yahoo equity prices.

> **Status:** Headline empirical window is calendar year 2024 (Q1–Q4). All
> inputs are real public data — no synthetic substitutes. The pipeline supports
> multi-year extension; collaborators can help by running the SAR-download
> helper on their own machines (see [`docs/SAR_DATA_DOWNLOAD.md`](docs/SAR_DATA_DOWNLOAD.md)).

---

## Quick start (for friends who just want to see the demo)

```bash
git clone <this repo>
cd FINAL

# 1. Python deps
python3 -m pip install -r requirements.txt

# 2. Launch the demo dashboard
streamlit run dashboard/app.py
# → opens http://localhost:8501
```

The dashboard runs entirely on cached results that ship with the repo. **No
API keys required**, no LLM calls, no SAR fetches. Walks through:

1. The research question
2. Real data sources (provenance table)
3. The 5-agent pipeline
4. Per-cell walkthrough — pick any of the 40 cells and see what each agent did
5. The 2 long trades (FANG 2024-Q2 loss, PR 2024-Q3 win)
6. Cross-strategy comparison (Strategy 1 vs 9 baselines)
7. Honest limitations (n=2, mechanical α=0 + no-satellite ablations)

---

## What the system does

For every (firm × fiscal-quarter) **cell** — 10 firms × 4 quarters = 40 cells
in 2024 — at decision date `T = earnings_date − 14 days`, the system runs five
specialist agents in sequence:

| # | Agent | Job | LLM? |
|---|---|---|---|
| 1 | **GIS Detection** | Read real Sentinel-1 SAR backscatter at 5 representative pads. Apply +1.5 dB change-detection rule. | No (pure code) |
| 2 | **Revenue Forecast** | Compute deterministic forecast `consensus × (1 + 0.10 × clip(drilling_signal, -1, +1))`. LLM writes qualitative outlook. | Yes (annotation only) |
| 3 | **Consensus Comparison** | Classify divergence: strong_beat / modest_beat / in_line / modest_miss / strong_miss. **Cells outside `modest_beat`/`strong_beat` short-circuit to no_trade.** | No (Python; LLM writes only `reasoning`) |
| 4 | **News Verification** | Read GDELT articles up to T-14. If activity already disclosed, downgrade conviction. Defensive fallback if LLM fails. | Yes |
| 5 | **Investment Board** | Bull/Bear LLM debate moderated by Arbiter. Conviction tier → deterministic size lookup (high=15%, medium=10%, low=5%, none=0%). | Yes (debate only) |

A cell fires `long` only when **at least 3 of 5 sampled pads** classify as
active on the radar (3+ active → drilling_signal ≥ +0.5 → divergence ≥ +5% →
modest_beat). 38 of 40 cells in 2024 short-circuited; 2 fired (FANG Q2, PR Q3).

---

## Headline 2024 results

| Strategy | n trades | Hit rate | Mean net return | Sharpe |
|---|---:|---:|---:|---:|
| **1. Multi-agent (real Sentinel-1 SAR)** | **2** | **50.0%** | **+0.31%** | 0.03 |
| 2. No-news ablation | not run for 2024 | — | — | — |
| 3. Analyst-revision follower | 18 | 27.8% | −3.13% | −0.44 |
| 4. WTI 3-month momentum | 20 | 30.0% | −1.54% | −0.23 |
| 5. Permian rig count | 10 | 30.0% | −0.15% | −0.03 |
| 6. Equal-weight universe | 40 | 32.5% | −1.99% | −0.29 |
| 7. XLE buy-and-hold | 1 | 100% | +6.33% | — |
| 8. 12-1 momentum | 14 | 28.6% | −3.13% | −0.51 |
| 9. Value composite | 15 | 33.3% | −2.94% | −0.41 |
| 10. Quality composite | 16 | 18.8% | −3.54% | −0.63 |

**Statistical inference (n=2 is honestly small):**
- H1 (hit rate > 50%): bootstrap p = 0.245, exact binomial p = 0.750 — **cannot reject** H0 = 50%
- H2 (S1 vs S3 hit-rate gap > 3pp): observed +22.2pp, p = 0.284 — **cannot reject** H0
- α=0 ablation: 0 long trades (mechanically guaranteed)
- No-satellite ablation: 0 long trades (mechanically guaranteed)

The 2-trade sample is a transparent consequence of the project's real-data-only
commitment + free-tier compute scope. The mechanical ablations confirm that
whatever signal the system did produce in 2024 is mechanically traceable to
the satellite input, not the LLM scaffolding.

---

## Repository layout

A condensed map. **Full project-structure walkthrough — including which
directories are dev-history leftovers and where to put new code — is in
[`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md).**

```
FINAL/
├── README.md                  ← you are here
├── docs/
│   ├── PROJECT_STRUCTURE.md   ← detailed walkthrough of every directory
│   ├── SAR_DATA_DOWNLOAD.md   ← collaborator guide for SAR data fetching
│   └── paper/                 ← 14-section paper, source markdown
├── paper_pdf/paper.pdf        ← compiled 36-page paper
├── dashboard/app.py           ← Streamlit demo dashboard
├── fin580/                    ← main Python package
│   ├── agents/                ← Agent 1–5, LLM client, schemas, prompts
│   ├── data/                  ← Sentinel-1, FracFocus, IBES, GDELT, WTI, CRSP loaders
│   ├── backtest/              ← runner + 10 strategies + P&L engine
│   ├── inference/             ← bootstrap, H2 test, evidence pack, equity curves
│   └── repro/manifest.py      ← reproducibility manifest
├── phase1/output/             ← input data (CSVs + Sentinel-1 + GDELT caches)
├── runs/                      ← backtest outputs (one dir per run + inference rollups)
├── scripts/                   ← utility scripts (fetch_sar_for_window, validate_sar_cache, …)
└── tests/                     ← pytest suite
```

---

## Environment variables

| Variable | Required for | Default | How to get it |
|---|---|---|---|
| `CEREBRAS_API_KEY` | Re-running Strategy 1 / Strategy 2 (LLM agents 2–5). Not needed for dashboard or for running deterministic baselines (Strategies 3–10) or for SAR-only download. | none | **Free tier:** sign up at https://cloud.cerebras.ai → "API Keys" tab → create key. Free tier currently allows ~30 requests/minute and ~1M tokens/day. No credit card. |
| `FIN580_SAR_MODE` | Telling Agent 1 to read real Sentinel-1 (vs the legacy synthetic generator) | `synthetic` | Set to `real_sentinel1` to use real radar. (You almost always want this.) |
| `CEREBRAS_MIN_INTERVAL_SECONDS` | Throttle between Cerebras LLM calls; prevents queue-exceeded 429s during peak hours | `2.0` | Bump to `4.0` if you see frequent 429 errors during weekday US business hours. |
| `FIN580_SAR_PADS_PER_OP` | Number of representative pads sampled per firm per quarter (paper §12.3) | `5` | Increase to 10+ for higher-fidelity firm-quarter signals at the cost of longer SAR fetch time. |
| `HUGGINGFACE_API_KEY` | Optional fallback provider (legacy, not used in 2024 headline) | none | https://huggingface.co/settings/tokens — read-only token is fine. |
| `GROQ_API_KEY` | Optional fallback provider (legacy, not used in 2024 headline) | none | https://console.groq.com/keys — free tier is rate-limited. |
| `FIN580_ALPHA` | Override the α=0.10 consensus-anchor coefficient (used for the α=0 ablation) | `0.10` | Set to `0.0` to reproduce the no-signal ablation in §11.1. |
| `FIN580_ABLATION` | Force the no-satellite ablation (Agent 1 emits all-idle pads) | unset | Set to `no_satellite` to reproduce §11.2. |

**Quick setup with a `.env` file (recommended):**

```bash
# Create a .env file in the project root (do NOT commit it)
cat > .env <<'EOF'
CEREBRAS_API_KEY=your-cerebras-key-here
FIN580_SAR_MODE=real_sentinel1
CEREBRAS_MIN_INTERVAL_SECONDS=4.0
EOF

# Source it before any backtest run
set -a; source .env; set +a
```

Add `.env` to your `.gitignore` so the key never gets committed.

---

## Full reproduction (requires Cerebras API key + WRDS access)

If you want to **re-run the multi-agent pipeline from scratch** rather than
just load the cached results, you need:

1. **Cerebras API key** — see the env-var table above. Used for Agents 2–5 LLM calls.
2. **WRDS subscription** — for the IBES Detail-History, CRSP daily, and
   Compustat fundq pulls. Free for academic users via your university.
   Without WRDS you can still run the dashboard on cached results.
3. **Python ≥ 3.10**, deps in `requirements.txt`.

Then:

```bash
# Re-run Strategy 1 (full multi-agent, real Sentinel-1 SAR) on 2024 window
FIN580_SAR_MODE=real_sentinel1 \
    python3 -m fin580.backtest.runner --strategy 1 --window 2024Q1-2024Q4 \
        --cm-label target --run-suffix realsar

# Re-run deterministic baselines (no LLM, no API key needed)
python3 -m fin580.backtest.runner --strategies 3,4,5,6,7,8,9,10 \
    --window 2024Q1-2024Q4

# Refresh inference + evidence pack
python3 -m fin580.inference.build_evidence_pack
```

Output lands in `runs/2026-04-30-strategy1-2024Q1_2024Q4-target-realsar/`
plus `runs/inference/`.

---

## Helping the project: collaborative SAR data download

The biggest compute bottleneck is fetching real Sentinel-1 RTC backscatter
from Microsoft Planetary Computer (free but bandwidth-limited per machine).
If you'd like to help extend the backtest to additional years, you can run
the SAR-download helper on your own machine and ship back the JSON cache
files.

**See [`docs/SAR_DATA_DOWNLOAD.md`](docs/SAR_DATA_DOWNLOAD.md)** for the
full guide. Short version:

```bash
# 1. Install minimal deps (no API keys needed for SAR-only)
python3 -m pip install pystac-client planetary-computer rasterio rioxarray xarray pandas numpy

# 2. Run the helper for a year + firm range
python3 scripts/fetch_sar_for_window.py --start 2022Q1 --end 2022Q4 --firms FANG,EOG,DVN

# 3. Send back the new files in:
#    phase1/output/sentinel1_cache/
```

Cache files are small (~17 KB JSON per pad-year, ~500 B per firm-quarter
aggregate), so they ship easily over Slack / Drive / email.

---

## License & data sensitivity

- Code: free to share within the project team.
- **Do not redistribute** the IBES, CRSP, or Compustat CSVs in
  `phase1/output/` — they're licensed via WRDS subscription.
- FracFocus, EIA, GDELT, Sentinel-1 data are public domain / CC0.

---

## Citing

This is a FIN 580 final project. The compiled paper is at
`paper_pdf/paper.pdf`. If you reference it externally, cite as:

> Vincent N. W. (2026). *Satellite-Anchored Pre-Earnings Trading in
> Permian E&P: A Multi-Agent Framework with a Deterministic Numerical
> Core.* FIN 580 Final Project, Spring 2026.
