# Phase 1 Redesign — Negative Result on 2024

**Branch:** `experiment/agent4-5-redesign`
**Phase 1 finished:** 2026-05-03
**Per user's pre-registered criterion** ("if result is better, extend to 2019-2024"),
**Phase 2/3 are NOT triggered.**

## Configuration

The redesign per `docs/AGENT4_5_REDESIGN.md`:
- Agent 3 gate: **REMOVED** (informational only)
- Agent 5 hard guardrail (DL #56): **REMOVED**
- Agent 4: **rewritten** to produce GDELT-backed structured catalyst brief
- Agent 5: outputs `conviction_score` 0-100; trade-selection layer applies
  top-K-per-cycle budget (K=4, min_score=45)
- Model stack: gpt-4o-mini for Agents 2/3/4/Bull/Bear; gpt-5.4-mini for Arbiter

## Headline result

| Metric | Baseline α=0.10 (gated) | Redesign (ungated, OpenAI mini) |
|---|---:|---:|
| Cells evaluated | 40 | 40 |
| Long trades fired | 2 | **4** |
| Hit rate | 50% (1W/1L) | **25% (1W/3L)** |
| Total net P&L (10% size, $1M) | **+$628** | **−$13,262** |
| Errors | 0 | 0 (clean) |

## Per-trade P&L

| Trade | Score | Net return | $ P&L | Notes |
|---|---:|---:|---:|---|
| PR 2024-Q3 | 66 | +7.43% | +$7,426 | Same as baseline winner |
| DVN 2024-Q2 | 66 | −2.15% | −$2,149 | NEW (not in baseline) |
| SM 2024-Q2 | 63 | −3.42% | −$3,424 | NEW |
| CRGY 2024-Q2 | 61 | −15.11% | **−$15,115** | NEW (worst trade) |

## Score distribution across 40 cells

- Top 4 cells (firing): scores 61-66 (one in Q3, three in Q2)
- Fifth cell drops to 38 — clear separation; budget effectively no-op
- Bulk of cells: 14-38 (no_trade)

The Arbiter is **discriminating** (not over-firing) but its top picks happen to
cluster in 2024-Q2 — suggesting the Bull/Bear/Arbiter LLM debate found a shared
positive narrative (likely early-2024 oil-price strength, drilling activity
recovery rhetoric) that didn't survive Q2 reports.

## What the redesign got *right* mechanically

- Clean end-to-end run on full OpenAI stack (40/40 cells `ok`, no errors)
- Architecture works as designed: Agent 4 catalyst brief produced for every cell;
  Agent 5 scored every cell; trade-selection budget applied
- **Correctly skipped FANG 2024-Q2** (baseline loser) — gave it score 34, below firing threshold
- **Correctly kept PR 2024-Q3** (baseline winner) — score 66, top-tier conviction
- conviction_score parquet column populated correctly (after fixing
  `_append_cell_result` bug — see commit 24de285)

## What the redesign got *wrong* empirically

- 3 of 4 fired trades lost; net P&L is sharply worse than baseline
- Cluster bias: 3 of 4 trades in 2024-Q2, suggesting the LLM debate saw a
  regime-wide positive narrative and amplified it across multiple Permian names
- The `conviction_score` ranking does not appear to be predictive of forward
  returns at the score levels we're firing on (61-66)

## Why this matches the α=0.20 experiment finding

This is the third confirmation of the same pattern:

| Experiment | Trade count | Hit rate | Total P&L |
|---|---:|---:|---:|
| Baseline (gated, α=0.10) | 2 | 50% | +$628 |
| α=0.20 sensitivity (loosened gate) | 4 | 50% | −$2,740 |
| **Phase 1 redesign (ungated + new Agent 4 + score-budget)** | **4** | **25%** | **−$13,262** |

**Pattern:** changing the system to fire MORE trades does NOT improve P&L on 2024.
Each successive loosening either preserves hit rate at cost of variance (α=0.20)
or *degrades* hit rate (Phase 1). The marginal cells the system identifies as
"candidates" are not predictive at the population scale we have (40 cells × 5 pads
per firm-quarter sampling).

## Implication for the paper

This is a **valuable negative result** that supports several paper claims:

1. **The original α=0.10 / DL #56-#61 gated specification is empirically
   competitive** — not just a free-tier-cost compromise but actually a
   conservative-correct decision in this sample.
2. **Multi-agent architectural complexity does not automatically improve
   alpha extraction** — the redesign added richer news context (Agent 4
   catalyst brief) and a flexible LLM-driven decision (Agent 5 score), and
   both *failed to outperform* a deterministic gate.
3. **The bottleneck isn't the architecture; it's the input signal**. With
   5 pads per firm-quarter sampling, the satellite signal is too sparse
   to identify true firm-quarter winners reliably. Codex's earlier framing
   stands: the right path forward is more pads + Permian-pure universe,
   not parameter or architecture tuning.

## Cost of Phase 1

OpenAI API cost: ~$0.30 (40 cells × ~5 LLM calls × small token volumes per call,
mostly gpt-4o-mini at $0.15/$0.60 with one gpt-5.4-mini Arbiter call at $0.25/$2).

Confirmed cheap; would have spent ~$3 if extending to full 2019-2024.

## Decision

**Phase 2 (5-variant ablation matrix on 2024) and Phase 3 (extension to 2019-2023)
are NOT triggered**, per user's pre-registered criterion. The redesign branch
remains available as documented research artifact.

The α=0.10 + gated architecture (current main branch) stays as the project
headline.

## Status

- Phase 1 finished cleanly: ✅
- Result documented honestly: ✅
- Ablation matrix decision pre-registered: do NOT proceed
- Total Phase 1 spend: ~$0.30
- Redesign branch frozen as `experiment/agent4-5-redesign` for paper Robustness
  Checks section
