# Agent 4 + Agent 5 Redesign Proposal

**Branch:** `experiment/agent4-5-redesign`
**Date drafted:** 2026-05-03
**Status:** SPEC — not yet implemented
**Authors:** Vincent (with Claude Opus 4.7 + Codex GPT-5.5 review)

---

## 1. Motivation

The 2019-2024 backtest produced 10 long trades, 50% hit rate, total -$20,623
P&L on $1M. Two findings drove this redesign:

### Finding A — Agent 3 gate is anti-predictive
A suppressed-cell audit (`docs/AGENT3_GATE_AUDIT.md`) showed:
- `modest_beat` cells (gate **passes** → fires long): mean **−0.91%**, n=15
- `in_line` cells (gate **blocks**): mean **+1.48%**, n=113
- `modest_miss` cells (gate **blocks**): mean **+1.65%**, n=72

The gate is filtering OUT positive-return cells on average.

### Finding B — Agent 4 is too narrow to add value
Current Agent 4 only answers "is the SAR signal already disclosed in GDELT
news?" with a boolean. It misses pre-earnings catalysts: production guidance,
operational disruptions, analyst revisions, balance-sheet stress, M&A,
commodity exposure changes.

### What this redesign addresses
- Replace Agent 3's hard gate with informational use of `divergence_class`
- Replace Agent 4's narrow novelty check with a structured news brief
- Move the trade decision entirely to Agent 5, on **all 200 cells**, with a
  mechanical trade budget (not free LLM approval)
- Restore model-family diversity by moving the Arbiter to Gemini

---

## 2. Architecture (proposed)

```
Agent 1  GIS Detection      Python only (unchanged)
Agent 2  Revenue Forecast   Python deterministic; Cerebras llama3.1-8b for outlook annotation (unchanged)
Agent 3  Consensus Compare  Python only — produces divergence_class as INFO ONLY (no veto)
Agent 4  News Intelligence  Cerebras llama3.1-8b — GDELT-backed structured news brief
                            (positive_catalysts, negative_catalysts, sentiment, sar_complement)
Agent 5  Decision Board     Runs on ALL cells. Outputs a SCORE not a binary call.
            Bull:    Cerebras qwen-3-235b
            Bear:    Cerebras llama3.1-8b
            Arbiter: Gemini 2.5 Flash (free tier, 250 RPD / 10 RPM)
            Output:  conviction_score [0-100] + tier (high/medium/low/none)

Trade Selection (NEW — replaces Agent 3 gate + Agent 5 hard guardrail):
  - Agent 5 outputs conviction_score for every cell
  - Mechanical trade budget: TOP K_PER_CYCLE cells per earnings cycle by score
  - K_PER_CYCLE pre-registered before looking at returns (see Section 5)
  - Position size from conviction tier: high=15%, medium=10%, low=5%, none=0%
  - Capacity cap: max 8 simultaneous positions

Execution: stays mechanical (T-14 entry close, T+2 exit close)

Removed:
  - DL #56 Agent 5 hard guardrail
  - DL #61 orchestrator short-circuit
```

---

## 3. Per-agent specifications

### Agent 4 — News Intelligence (rewrite)

**News source: GDELT 2.0** (locked decision — see Appendix C for why not NewsAPI).

**Inputs:**
- GDELT articles for firm in `[T-30, T-14]` window (existing cache;
  hard cutoff at T-14 for leakage discipline)
- Agent 1's SAR signal: `n_newly_active`, `n_continuously_active`, `n_idle`,
  `relative_activity_delta`
- Agent 2's forecast: `revenue_forecast_usd`, `consensus_anchor_usd`, `divergence_pct`
- Agent 3's `divergence_class`

**LLM prompt structure (Cerebras llama3.1-8b):**
```
SYSTEM: You are an equity-research analyst summarizing pre-earnings news for
{ticker} ahead of earnings on {ed}. The decision date is T-14 = {T}; you may
only use information dated on or before {T}.

INPUTS:
  - GDELT articles in window [T-30, T-14]: {articles}
  - SAR drilling signal: {agent1_summary}
  - Revenue forecast vs consensus: {agent2_summary}, divergence {div_pct}%

TASK: Produce a structured news brief in JSON with these fields:
  positive_catalysts: list of 3-5 specific positive items, each with article reference
  negative_catalysts: list of 3-5 specific negative items, each with article reference
  overall_sentiment: one of {bullish, neutral, bearish}
  sar_complement: 1-2 sentences — what the news adds BEYOND what SAR alone shows
  novelty_assessment: is the SAR signal already public? (yes/no/partial)

Be specific. Cite article timestamps. Do not speculate beyond the articles.
```

**Output JSON schema:**
```python
class Agent4Out(BaseModel):
    positive_catalysts: list[CatalystRef]      # max 5
    negative_catalysts: list[CatalystRef]      # max 5
    overall_sentiment: Literal["bullish","neutral","bearish"]
    sar_complement: str
    novelty_assessment: Literal["yes","no","partial"]
    n_articles_in_window: int
    fallback_used: bool
```

**Defensive fallback:** if LLM JSON parse fails after 2 retries, default to:
`overall_sentiment="neutral"`, empty catalyst lists, `fallback_used=True`.
Pipeline continues; cell scores will reflect missing news context.

### Agent 5 — Decision Board (refactor)

**Inputs (all cells, no gate):**
- Agent 1, 2, 3, 4 outputs (the full info package)
- divergence_class is now informational, not a veto

**Three-LLM debate (existing structure, expanded prompts):**

```
BULL (Cerebras qwen-3-235b):
  Make the strongest case for going long this firm-quarter at T-14.
  Use SAR signal, news positive catalysts, divergence vs consensus.
  Output: direction (long/no_trade), confidence (high/medium/low),
          key_evidence, counter_evidence, reasoning_short.

BEAR (Cerebras llama3.1-8b):
  Make the strongest case AGAINST going long this firm-quarter.
  Use SAR risks, news negative catalysts, divergence_class concerns.
  Same output schema.

ARBITER (Gemini 2.5 Flash):
  Read both Bull and Bear opinions plus all upstream agent outputs.
  Output:
    decision: long | no_trade
    conviction_score: 0-100   # NEW — calibrated rank, not just tier
    conviction_tier: high | medium | low | none
    arbiter_reasoning: 2-3 sentences
    key_factors: top 3 factors driving the score
```

**Score calibration:** the conviction_score is the new ranking variable.
Pre-registered tier mapping (locked before final 2024 test):
- score ≥ 75 → high (15% size)
- score 60-74 → medium (10% size)
- score 45-59 → low (5% size)
- score < 45 → none (0%, no trade)

### Trade Selection (new mechanical layer)

After Agent 5 scores all eligible cells in an earnings cycle:

1. Sort cells by `conviction_score` descending
2. Select top K_PER_CYCLE cells (default: 4 — calibrated from Codex's "concentrated portfolio" framing)
3. Among selected, fire `long` only if `conviction_score ≥ 45`
4. Cap simultaneous positions at 8 (legacy rule from DL #16)
5. Position size from tier mapping above

**Tunable parameters (pre-registered before 2024 test):**
- `K_PER_CYCLE = 4`
- `score_threshold_long = 45`
- `score_to_tier_thresholds = (75, 60, 45)` for (high, medium, low)
- `max_simultaneous_positions = 8`

Calibration source: 2019-2023 backtest output. Choose K to produce ~2-3
trades per quarter on average. Locked before 2024 evaluation.

---

## 4. Comparison framework — same budget across all benchmarks

Per user requirement: "for comparison to VOO and XES and other comparison,
it needs to be the same budget as well."

### Two distinct comparison modes

**Mode A — Total wealth comparison (current dashboard Section 6):**
- $1M starting capital
- System: compounds per-trade net P&L, holds cash between trades
- XES B&H: $1M deployed Day 1 of window, held to end
- VOO B&H: same as XES
- Honest framing: "what total wealth would each strategy have produced?"
- Caveat: system's average exposure is much lower than 100% (typically <5%)

**Mode B — Matched-exposure comparison (NEW):**
- Same $1M starting capital
- For each of system's N trades, with size_pct%, compute what XES and VOO
  would have returned over the SAME entry-to-exit window at the SAME size_pct
- Aggregate: sum dollar P&L across matched windows
- Honest framing: "did the system's selection beat passive index over the
  same time the system was actually in position?"
- This isolates the alpha question from the exposure question

Dashboard Section 6 should show **both modes** side-by-side. Mode A is
conservative (system looks bad); Mode B is the actual alpha test.

### Implementation note
- Mode A: already in dashboard
- Mode B: ~30 lines of new code in dashboard Section 6 — for each trade,
  look up XES/VOO close on entry_date_T and exit_date, compute matched return
- Both modes use $1M nominal capital but Mode B applies size_pct properly

---

## 5. Test protocol — pre-registered

Per Codex's pushback: prompts, thresholds, K, tier mappings, model choices
are all **frozen before** running the 2024 final evaluation.

### Phase 1 — Plumbing test on 2024 only
**Purpose:** validate data flow, cost, latency, parsing, and trade-count
behavior. **NOT performance evaluation.**

- Run new pipeline on 2024 (40 cells)
- Verify: all agents produce valid JSON; Gemini Arbiter rate limits respected;
  trade-count is in expected range (2-6); approval rate < 30%
- Cost estimate: ~200 LLM calls (40 cells × 5 calls), ~2-3 hr at current
  Cerebras throttle, ~40 Gemini calls (well under 250 RPD limit on gemini-2.5-flash)
- If approval rate is uncontrolled (>30% trades), tune K_PER_CYCLE BEFORE
  running on full 2019-2023 history

### Phase 2 — Full backtest 2019-2024
**Purpose:** measure performance against the locked architecture.

- Run all 200 cells with frozen architecture
- Compare against current gated baseline (10 trades, -$20,623, 50% hit rate)
- Run full ablation matrix (Section 6)
- **Acknowledged caveat:** user explicitly chose 2024-first testing despite
  Codex's selection-bias concern. Document this in paper Limitations.

### Required ablations

| Variant | Agent 3 gate | Agent 4 | Agent 5 stack | Purpose |
|---|---|---|---|---|
| **Baseline** | gated | old (novelty check) | all-Cerebras | current published system |
| **Gate-removed** | ungated | old | all-Cerebras | isolates gate effect |
| **News-rewritten** | ungated | new (catalyst brief) | all-Cerebras | isolates Agent 4 effect |
| **Hybrid stack** | ungated | new | Cerebras + Gemini | full proposed redesign |
| **Placebo** | ungated | shuffled GDELT (wrong ticker/date) | all-Cerebras | tests if Agent 4 adds real signal |

Run all 5 variants on 2024 first. Only extend to 2019-2023 if hybrid-stack
variant shows: (a) trade count in target range, (b) approved-trade hit rate
> baseline, (c) conviction tier monotonicity (high > medium > low realized
returns).

---

## 6. Metrics — first-class tracking

Per Codex: "track approval rate as a first-class metric. Before caring about
returns, check whether Agent 5 approves 5%, 20%, or 50%."

For each variant, report:
1. **Approval rate** = trades_fired / cells_evaluated. Target: 5-15%.
2. **Conviction tier monotonicity:** mean realized return for each of
   high / medium / low tiers. high should outperform low.
3. **Hit rate, mean return, total P&L** (existing metrics)
4. **Sharpe** (annualized, daily basis)
5. **Per-divergence-class breakdown:** does the new architecture pick
   winners from in_line / modest_miss cells (the suppressed-cell winners
   the audit flagged)?
6. **Mode A and Mode B** vs XES and VOO (matched-exposure too)
7. **Score calibration plot:** scatter conviction_score (0-100) vs realized
   return. Should be monotonically positive.

---

## 7. Implementation plan

### File changes

| File | Change |
|---|---|
| `fin580/agents/agent4_news.py` | Rewrite for catalyst brief; new prompt template |
| `fin580/agents/prompts/agent4_*.txt` | New prompt files (positive/negative catalyst extraction) |
| `fin580/agents/agent5_board.py` | Add `conviction_score` field; remove DL #56 hard guardrail |
| `fin580/agents/llm_client.py` | Add `gemini-2.0-flash` route via Google AI Studio API |
| `fin580/agents/orchestrator.py` | Remove DL #61 short-circuit; Agent 4 + 5 always run |
| `fin580/agents/schemas.py` | New `Agent4Out` schema with catalyst lists; updated `Agent5Out` |
| `fin580/backtest/runner.py` | New trade-selection layer (sort by score, top K, tier→size) |
| `dashboard/app.py` | Add Mode B (matched-exposure) comparison in Section 6 |
| `phase1/output/redesign_calibration.csv` | NEW — calibration data from 2019-2023 |
| `requirements.txt` | Add `google-genai>=0.3.0` |
| `.env.example` | Add `GEMINI_API_KEY` |
| `docs/AGENT4_5_REDESIGN.md` | This file (already drafted) |
| `docs/paper/11-attribution-ablation.md` | Add 5-variant ablation table |

### New env vars

```bash
GEMINI_API_KEY=...     # Free tier from aistudio.google.com
GEMINI_MODEL=gemini-2.0-flash
GEMINI_MIN_INTERVAL_SECONDS=4.0
```

### Estimated wall time

- Implementation: ~6-10 hours (prompts, schemas, runner trade-selection, Gemini routing)
- Phase 1 plumbing on 2024: ~2-3 hours of LLM time
- Phase 2 full ablation matrix on 2024: ~10-15 hours of LLM time (5 variants × 40 cells × 5 LLM calls)
- Phase 2 extension to 2019-2023 (if Phase 1 looks good): ~30-50 hours of LLM time spread across multiple days

---

## 8. Acknowledged risks and limitations

1. **Selection bias from 2024-first testing.** User chose this over Codex's
   pre-registered split protocol. Will be documented as a Limitations item.
2. **The gate-inversion finding may be regime-specific.** 2019-2024 includes
   COVID and unusual oil cycles. The new architecture may not generalize.
3. **Agent 5 free approval problem:** mitigated by mechanical trade budget,
   but the budget itself is a tunable parameter. We'll lock it before final
   eval but reviewers may still ask "what if you'd picked K=6?"
4. **Gemini quality is not guaranteed > Cerebras qwen-3-235b.** The Arbiter
   role might suffer. We'll know from the conviction_score calibration.
5. **No statistical predictive target.** Codex's deepest critique still
   stands: the system has no calibrated EV→size mapping, no factor adjustment
   for oil/sector beta, no uncertainty estimate. Out of scope for this
   redesign; documented as future work.
6. **Reproducibility burden.** Adding Gemini = 5th provider rotation. The
   paper's Methodology section will need updating.

---

## 9. Open questions for follow-up

1. Should the conviction tier→size mapping be linear (15/10/5/0%) or
   risk-adjusted (e.g., size = score × VolAdjustment)?
2. Should Agent 5 see the prior agents' free-text reasoning, or only their
   structured outputs?
3. For the placebo arm, should we shuffle ticker, date, or both?
4. Should we run Agent 4 on cells where Agent 1 produces empty SAR data
   (currently those cells default to no_trade silently)?

---

## 10. Status checklist

- [x] Spec drafted
- [ ] User review and sign-off
- [ ] Codex review of spec
- [ ] Implementation: Agent 4 rewrite
- [ ] Implementation: Gemini route in llm_client
- [ ] Implementation: Agent 5 score field + remove guardrail
- [ ] Implementation: orchestrator gate removal
- [ ] Implementation: trade-selection layer in runner
- [ ] Implementation: dashboard Mode B
- [ ] Phase 1: 2024 plumbing test
- [ ] Phase 1: tune K_PER_CYCLE if needed; LOCK parameters
- [ ] Phase 2: full ablation matrix on 2024
- [ ] Phase 2: extension to 2019-2023 (if 2024 looks good)
- [ ] Update `docs/paper/11-attribution-ablation.md`
- [ ] Merge experiment branch back to main with full results

---

## Appendix A — Codex's pushbacks and how this design addresses them

| Codex pushback | This design's response |
|---|---|
| "Agent 5 free approval = new hidden gate" | Mechanical top-K trade budget (Section 5) |
| "Don't bundle Gemini with redesign" | Ablation matrix runs all-Cerebras AND hybrid (Section 5) |
| "2024-first testing is selection-biased" | Documented as user-chosen risk (Section 8) |
| "Audit could be data-mining" | Acknowledged in Section 8; placebo ablation arm (Section 5) |
| "Track approval rate as first-class metric" | Section 6 metric #1 |
| "Conviction tiers must be monotonic" | Section 6 metric #2 |
| "No calibrated predictive target" | Documented as future work in Section 8.5 |
| "Recalibrate Agent 3 instead of remove" | Rejected — audit shows directional inversion, not just threshold issue |

---

## Appendix C — Why GDELT, not NewsAPI

User initially proposed NewsAPI.org. We evaluated and locked in GDELT
because of a hard blocker on NewsAPI's free tier:

| Source | Historical coverage | Free RPD | Cost for 2019-2024 backtest |
|---|---|---:|---|
| **GDELT 2.0** | full back to 2015 | unlimited, no auth | $0 (already cached for 78 windows) |
| NewsAPI free | **current month only** | 100 | unusable for historical backtest |
| NewsAPI Business | full | unlimited | $449/month |
| NewsAPI Advanced | full | unlimited | $599/month |

NewsAPI's developer (free) plan returns articles "up to a month old" only.
That makes it incompatible with backfilling news for 2019-2023 cells. The
paid tiers solve this but are out of scope for a student project budget.

GDELT 2.0 has full historical coverage, no API key, no rate limit, and
strong global news indexing including Reuters, Bloomberg-syndicated, and
regional press relevant to Permian E&P. The current Agent 4 *underuses*
GDELT by only asking a yes/no novelty question — the rewrite extracts
substantive structured catalysts from the same articles.

**If a future demo requires real-time news**, NewsAPI's free tier could
be added as a forward-only data source for live trading paper-trading
demos (post-paper). It would not affect the 2019-2024 backtest results.

---

## Appendix B — Decision-log entries to update after implementation

- DL #56 — supersede the hard guardrail; document the new score-based decision rule
- DL #61 — supersede the orchestrator short-circuit
- New DL — document the trade-budget layer and pre-registered K_PER_CYCLE
- New DL — document the Gemini Arbiter rotation (5th provider rotation)
- New DL — document the Agent 4 rewrite from novelty-check to catalyst-brief
