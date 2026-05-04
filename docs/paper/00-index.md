# FIN 580 Final Paper — Section Index

| § | Title | File |
|---|---|---|
| 1 | Title and Abstract | [01-title-and-abstract.md](01-title-and-abstract.md) |
| 2 | Introduction | [02-introduction.md](02-introduction.md) |
| 3 | Literature Review | [03-literature-review.md](03-literature-review.md) |
| 4 | Hypotheses and Research Questions | [04-hypotheses.md](04-hypotheses.md) |
| 5 | Data and Investment Universe | [05-data-and-universe.md](05-data-and-universe.md) |
| 6 | Multi-Agent Architecture | [06-multi-agent-architecture.md](06-multi-agent-architecture.md) |
| 7 | Methodology | [07-methodology.md](07-methodology.md) |
| 8 | Portfolio Construction | [08-portfolio-construction.md](08-portfolio-construction.md) |
| 9 | Results: Headline Strategy Comparison | [09-results-headline.md](09-results-headline.md) |
| 10 | Results: Cross-Strategy Comparison | [10-results-strategy-comparison.md](10-results-strategy-comparison.md) |
| 11 | Ablations and Robustness | [11-ablations-and-sensitivity.md](11-ablations-and-sensitivity.md) |
| 12 | Limitations and Threats to Validity | [12-limitations.md](12-limitations.md) |
| 13 | Conclusion | [13-conclusion.md](13-conclusion.md) |
| 14 | References | [14-references.md](14-references.md) |

## Supplementary materials

- `runs/inference/headline_table.csv` — per-strategy hit-rate, return, Sharpe, drawdown
- `runs/inference/strategy01_trades.csv` — Strategy 1 per-trade ledger
- `runs/inference/strategyXX_equity.csv` — per-strategy cumulative equity curves
- `runs/inference/bootstrap_table.csv` — primary + sensitivity bootstrap tests
- `runs/inference/ablation_table.csv` — legacy synthetic-window ablation table (kept for reference; mechanical α=0 and no-satellite results in §11 are window-independent)
- `runs/inference/evidence_pack.json` — top-level summary used to anchor paper claims
- `runs/<run_id>/manifest.json` — per-run reproducibility manifest

## How to regenerate every result

The headline empirical window is **Q1 2019 – Q4 2024 with real Sentinel-1 SAR** (six full calendar years, 200 firm-quarter cells, 10 long trades). Strategy 1 must run with `FIN580_SAR_MODE=real_sentinel1` so Agent 1 ingests real Microsoft Planetary Computer Sentinel-1 RTC backscatter (rather than the legacy synthetic-SAR generator, which is retained in the codebase only for backwards-compatibility).

```bash
# Strategy 1 — full multi-agent system, real Sentinel-1 SAR
# Run per-year (each year ~30-60 min wall time on free-tier LLM throughput)
FIN580_SAR_MODE=real_sentinel1 \
    python -m fin580.backtest.runner --strategy 1 --window 2019Q1-2019Q4 \
        --cm-label target --run-suffix realsar
# (repeat for 2020, 2021; 2022-2023 as a single run; 2024)

# Strategies 3-10 — deterministic baselines on real EIA / FracFocus / IBES
# Currently scoped to the 2024 sub-window; extension to 2019-2024 is documented
# as future work in §12.9.
python -m fin580.backtest.runner --strategies 3,4,5,6,7,8,9,10 --window 2024Q1-2024Q4

# Strategy 2 — no-news ablation (Agent 4 stubbed), real Sentinel-1 SAR, 2024 sub-window
FIN580_SAR_MODE=real_sentinel1 \
    python -m fin580.backtest.runner --strategy 2 --window 2024Q1-2024Q4 \
        --cm-label target --run-suffix realsar

# Mechanical ablations (α=0, no-satellite) produce zero trades by construction
# and do not require a separate run — documented in §11.1 / §11.2.

# Inference rollups
python -m fin580.inference.build_evidence_pack
python -m fin580.inference.equity_curves
```

The legacy synthetic-SAR pipeline is retained in the codebase for backwards-compatibility but is not part of the paper's empirical claims.
