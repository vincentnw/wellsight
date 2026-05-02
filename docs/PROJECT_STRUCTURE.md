# Project Structure

This document is the map of the repo. It explains what each top-level
directory contains, where to look for which kind of file, and the small
amount of dev-history naming that survived from the project's early phases
(the `phase1/`, `phase2/`, `phase3/` directories — these are historical
labels, not architectural layers).

```
FINAL/
│
├── README.md                  ← Top-level project overview, quick start, env vars
├── requirements.txt           ← Python deps (pip)
├── .env.example               ← Template for API keys; copy to .env (gitignored)
│
├── docs/                      ← All documentation
│   ├── PROJECT_STRUCTURE.md   ← (this file)
│   ├── SAR_DATA_DOWNLOAD.md   ← Guide for collaborators downloading SAR
│   ├── paper/                 ← 14-section paper, source markdown
│   │   ├── 00-index.md
│   │   ├── 01-title-and-abstract.md
│   │   ├── ...
│   │   └── 14-references.md
│   ├── specs/                 ← Original design / specification docs (historical)
│   └── plans/                 ← Original implementation plan (historical)
│
├── paper_pdf/
│   └── paper.pdf              ← Compiled 36-page paper (regenerate with pandoc)
│
├── dashboard/
│   └── app.py                 ← Streamlit demo dashboard (single-page, story-driven)
│
├── fin580/                    ← Main Python package (everything importable)
│   ├── agents/                ← Multi-agent system
│   │   ├── orchestrator.py    ← Cell-level coordinator: runs Agent 1→5, handles short-circuit
│   │   ├── agent1_gis.py      ← Agent 1 — GIS Detection (real Sentinel-1 SAR; no LLM)
│   │   ├── agent2_revenue.py  ← Agent 2 — Revenue Forecast (deterministic + LLM outlook)
│   │   ├── agent3_consensus.py← Agent 3 — Consensus Comparison (deterministic divergence + LLM reasoning)
│   │   ├── agent4_news.py     ← Agent 4 — News Verification (GDELT + LLM, defensive fallback)
│   │   ├── agent5_board.py    ← Agent 5 — Investment Board (Bull/Bear/Arbiter LLM debate)
│   │   ├── llm_client.py      ← Provider abstraction + cache layer + per-call throttle
│   │   ├── schemas.py         ← Pydantic schemas for inter-agent JSON contracts
│   │   └── prompts/           ← LLM prompts as text files
│   │
│   ├── data/                  ← Data loaders (one file per source)
│   │   ├── sentinel1_sar.py   ← Per-pad real Sentinel-1 RTC backscatter via Microsoft Planetary Computer
│   │   ├── sentinel1_firm_quarter.py ← Firm-quarter aggregation + change-detection rule
│   │   ├── synthetic_sar.py   ← Legacy synthetic-SAR generator (kept for backwards-compat; not used in headline)
│   │   ├── trc_permits.py     ← FracFocus permit-dump loader (real Permian wells)
│   │   ├── ibes_pit.py        ← IBES point-in-time consensus reconstruction (REVDATS-corrected)
│   │   ├── gdelt_loader.py    ← GDELT 2.0 DOC API + cache (T-14 enforced both paths)
│   │   ├── wti_loader.py      ← Real EIA weekly WTI spot
│   │   ├── bhi_loader.py      ← Real EIA-DPR Permian rig count (monthly + carry-forward)
│   │   ├── crsp_loader.py     ← Real CRSP daily prices (WRDS pull)
│   │   ├── compustat_loader.py← Real Compustat fundq quarterly fundamentals
│   │   └── yahoo_supplement.py← yfinance 2025 price supplement (CRSP gap)
│   │
│   ├── backtest/              ← Strategy execution
│   │   ├── runner.py          ← Cell-by-cell loop; CLI: `python -m fin580.backtest.runner`
│   │   ├── pnl_engine.py      ← Per-trade P&L with 30 bps round-trip cost
│   │   └── strategies/        ← One module per strategy (s01–s10)
│   │       ├── s01_full_system.py    ← Strategy 1 — full multi-agent (real SAR)
│   │       ├── s02_no_news.py        ← Strategy 2 — no-Agent-4 ablation
│   │       └── s03–s10                ← Deterministic single-signal baselines
│   │
│   ├── inference/             ← Statistical aggregation + tests
│   │   ├── pnl.py             ← compute_pnl_for_strategy + headline_table
│   │   ├── bootstrap.py       ← Null-centered firm-clustered bootstrap (H1)
│   │   ├── h2_test.py         ← Quarter-block diff bootstrap (H2)
│   │   ├── ablations.py       ← α=0 + no-satellite ablation tables
│   │   ├── equity_curves.py   ← Per-strategy equity curve generator
│   │   └── build_evidence_pack.py ← One-shot rollup → evidence_pack.json
│   │
│   ├── repro/
│   │   └── manifest.py        ← Reproducibility manifest writer (data SHAs, sar_mode, params)
│   │
│   ├── phase2/                ← Historical: contains a few utility modules still used
│   │   ├── revenue_forecast.py← Used by Agent 2 (consensus-anchored formula)
│   │   ├── earnings_dates.py  ← Used to generate phase1/output/earnings_dates.csv
│   │   ├── permian_fraction_extractor.py
│   │   └── equity_universe.py
│   │
│   └── phase3/                ← Historical: legacy SAR pipeline (superseded by data/sentinel1_*)
│       └── sar_pipeline.py    ← Not used in current codepath — kept for reference
│
├── phase1/                    ← Data inputs + caches (NOT a phase of the code; just where the bytes live)
│   ├── output/                ← The actual data files
│   │   ├── ibes_tr_ibes_sal_query11220958.csv  ← WRDS pull — DO NOT redistribute
│   │   ├── crsp_daily.csv                       ← WRDS pull — DO NOT redistribute
│   │   ├── compustat_fundq.csv                  ← WRDS pull — DO NOT redistribute
│   │   ├── permit_dump.csv                      ← FracFocus public — 12,376 Permian permits
│   │   ├── eia_wti_weekly.csv                   ← EIA public
│   │   ├── bhi_permian_rigcount_weekly.csv      ← EIA-DPR public
│   │   ├── earnings_dates.csv                   ← derived from IBES ANNDATS_ACT
│   │   ├── yahoo_2025_supplement.csv            ← yfinance free
│   │   ├── gdelt_cache/                         ← cached GDELT articles per (ticker, window)
│   │   └── sentinel1_cache/                     ← cached Sentinel-1 backscatter
│   │       ├── *.json                           ← per-pad time-series (~17 KB each)
│   │       └── firm_quarter_aggregates/         ← per-cell aggregate (~500 B each)
│   └── *.md                   ← Original data spec / coverage-audit docs
│
├── phase3/                    ← Historical: empty / placeholder; no current code reads from it
│   └── output/
│
├── runs/                      ← All backtest outputs (one dir per run)
│   ├── 2026-04-30-strategy1-2024Q1_2024Q4-target-realsar/  ← The headline 2024 run
│   │   ├── strategy_01/
│   │   │   ├── cell_results.parquet              ← One row per cell
│   │   │   ├── cell_results_summary.parquet      ← Final summary
│   │   │   └── agent_outputs/                    ← Per-cell agent JSON outputs
│   │   ├── manifest.json                         ← Reproducibility hash + sar_mode + params
│   │   └── quality_log.csv
│   ├── 2026-04-29-* (legacy synthetic-data runs from earlier phases)
│   ├── 2026-05-01-* (later real-data runs)
│   ├── inference/                                ← Aggregated tables consumed by paper + dashboard
│   │   ├── headline_table_2024.csv
│   │   ├── strategy01_trades_2024.csv
│   │   ├── evidence_pack.json
│   │   ├── ablation_table.csv
│   │   ├── bootstrap_table.csv
│   │   └── strategyXX_equity.csv
│   └── _global_cache/                            ← LLM call cache keyed by (prompt+input+model+temp)
│
├── scripts/                   ← Utility scripts (callable directly, not imported)
│   ├── fetch_sar_for_window.py     ← SAR-only download helper for collaborators
│   ├── validate_sar_cache.py       ← Pre-shipment validator
│   └── probe_providers.py          ← Test LLM provider connectivity
│
├── tests/                     ← Pytest suite
│   ├── test_llm_client.py
│   ├── test_pnl_engine.py
│   ├── test_schemas.py
│   └── test_synthetic_sar.py
│
└── project_overview.md, project_requirement.md  ← Original assignment artifacts (historical)
```

---

## Where to find / change things

| If you want to… | Look at |
|---|---|
| Run the demo dashboard | `dashboard/app.py` |
| Re-run the backtest | `python -m fin580.backtest.runner ...` |
| Modify how a single agent works | `fin580/agents/agentN_*.py` |
| Modify the SAR change-detection rule | `fin580/data/sentinel1_sar.py::classify_pad_from_sar` |
| Add a new strategy baseline | drop a new `sNN_*.py` file in `fin580/backtest/strategies/` and register it in `__init__.py` |
| Change the consensus-anchor coefficient α | `fin580/agents/agent2_revenue.py` (default `0.10`) — or env var `FIN580_ALPHA` |
| Update statistical tests | `fin580/inference/bootstrap.py`, `h2_test.py` |
| Read or edit the paper | `docs/paper/0X-*.md`, then regenerate `paper_pdf/paper.pdf` with `pandoc` |
| Help with collaborative SAR fetches | follow `docs/SAR_DATA_DOWNLOAD.md` |

---

## Naming caveats (dev-history leftovers)

The directory names below are **historical** — they reflect the project's
chronological development phases, not architectural layers. They survive in
the codebase because changing them would break import paths and run-dir
references. A reader can safely treat them as ordinary directories:

| Directory | What it actually contains | Why the awkward name |
|---|---|---|
| `phase1/output/` | Input data files (real CSVs + caches) | "Phase 1" of the project plan was data ingestion. The directory became the data root. |
| `fin580/phase2/` | Utility modules: `revenue_forecast`, `earnings_dates`, `permian_fraction_extractor`, `equity_universe` | "Phase 2" was the deterministic-numerical-core build. These modules are still used (e.g., `revenue_forecast.py` is imported by Agent 2). |
| `fin580/phase3/sar_pipeline.py` | Legacy SAR scaffolding (superseded by `fin580/data/sentinel1_*.py`) | "Phase 3" was the original synthetic SAR design. The file is unused but kept for git-history traceability. |
| `phase3/` (top-level) | Mostly empty | Vestigial. Could be deleted. |

If we were starting over today, the cleaner layout would be:

```
src/{name}/{agents,data,backtest,inference,repro}/  # main package
data/{raw,cache}/                                    # was phase1/output
docs/{paper,specs,plans}/
runs/{YYYY-MM-DD-...}/
```

But the current structure is functional and documented; refactoring at this
point would break import paths for marginal gain.

---

## Run artifacts: the `runs/` directory grows

Every backtest invocation creates a new directory in `runs/` named:

```
{YYYY-MM-DD}-strategy{N}-{start}_{end}-{cm_label}[-{suffix}]
```

For example: `2026-04-30-strategy1-2024Q1_2024Q4-target-realsar`

Each run dir contains:
- `manifest.json` — full reproducibility manifest (data SHAs, params, env)
- `strategy_NN/cell_results.parquet` — one row per cell
- `strategy_NN/agent_outputs/` — per-cell JSON for each agent (audit trail)
- `quality_log.csv` — error log for debugging

**Old run dirs are NOT auto-cleaned.** They accumulate. The codebase contains
several from the synthetic-data era (April 2026, run id starts with
`2026-04-29-`). These are kept for reproducibility but are not part of any
current empirical claim.

---

## License + redistribution

- **Code (`fin580/`, `dashboard/`, `scripts/`, `docs/`)**: free to share within
  the project team / academic context.
- **WRDS-licensed data** (`phase1/output/ibes_*.csv`, `crsp_daily.csv`,
  `compustat_fundq.csv`): **do not redistribute outside your institution.**
- **Public data** (FracFocus, EIA, GDELT, Sentinel-1): public domain / CC0.

When sharing the repo with collaborators who don't have WRDS, either:
(a) zip without the `phase1/output/ibes_*`, `crsp_daily`, `compustat_fundq`
files, OR (b) verify the recipient also has WRDS access.
