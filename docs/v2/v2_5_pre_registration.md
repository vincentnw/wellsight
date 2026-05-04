# v2.5 Pre-Registration: Dense-SAR + Reliable LLM Stack

**Status:** Combined v2 system upgrade. Reported as a system-quality improvement
over the v1 baseline (`main`, commit `fcb1490`). Not framed as an isolated SAR
density attribution test.

**Two changes vs v1:**

1. **SAR pad sample density:** 5 → 25 representative pads per firm-quarter cell.
   Activated via `FIN580_SAR_PADS_PER_OP=25`. Cache key `..._n25.json` is
   distinct from `..._n5.json`, so v1 cache is preserved.

2. **LLM provider routing for Agents 3, 4, 5:** Cerebras free tier → OpenAI
   paid tier. Agent 2 stays on Cerebras (qwen-3-235b qualitative outlook).

   | Agent | v1 model | v2.5 model | Provider |
   |---|---|---|---|
   | Agent 2 (revenue outlook) | qwen-3-235b | **qwen-3-235b** (unchanged) | Cerebras |
   | Agent 3 (divergence reasoning) | llama3.1-8b | gpt-4o-mini | OpenAI |
   | Agent 4 (GDELT news) | llama3.1-8b | gpt-4o-mini | OpenAI |
   | Agent 5 Bull | qwen-3-235b | gpt-4o-mini | OpenAI |
   | Agent 5 Bear | llama3.1-8b | gpt-4o-mini | OpenAI |
   | Agent 5 Arbiter | qwen-3-235b | gpt-5.4-mini | OpenAI |

   Motivation: v1 hit Cerebras free-tier 429 rate limits multiple times
   mid-run, requiring multi-account key rotation and 12s throttling. The
   reliability cost was non-trivial (multi-day re-runs). OpenAI mini tier
   is ~$0.50-0.75 for the full 2019-2024 sweep with no rate-limit pain.

**What is unchanged from v1:**

- Agent 1 (SAR ingestion) — pure Python, no LLM
- Deterministic Agent 2 forecast formula (consensus-anchored α=0.10)
- Agent 3 deterministic gate (`modest_beat` / `strong_beat` only)
- Agent 5 deterministic conviction-to-size lookup
- 30 bps round-trip transaction cost
- T-14 entry / T+2 trading days exit
- 200-cell universe (10 firms × 24 quarters minus pre-IPO/pre-merger ineligible)
- α=0.10 anchor coefficient
- Long-only

**Pre-registered procedure:**

1. SAR fetch: 25 pads × 200 cells (10 firms × 24 quarters minus pre-IPO/merger
   exclusions) for 2019Q1-2024Q4. Cache to
   `phase1/output/sentinel1_cache/firm_quarter_aggregates/*_n25.json`.

2. Phase A — 2024 plumbing test: re-run Strategy 1 on 2024 only with the new
   SAR cache + new LLM routing. Validate (a) the pipeline runs end-to-end with
   no schema or routing errors, (b) the Agent 3 deterministic gate still
   produces sane divergence classes, (c) cell-level outputs land in the new
   run dir. **No headline interpretation from this phase.**

3. Phase B — 2019-2024 full re-run: extend to 2019-2023 only after Phase A
   passes. Same configuration. Generate canonical v2.5 parquet ledgers.

4. Reporting: v2.5 results are reported as a §11 / §12 **system-quality
   sensitivity**. We compare:
   - v1 baseline (5-pad, Cerebras): n=10, 5W/5L, hit_rate=0.500, p=0.606
   - v2.5 (25-pad, OpenAI mini stack): n=?, ?W/?L, hit_rate=?, p=?

   The comparison is a combined system-quality test, not an attribution of
   the change to either SAR density or LLM routing in isolation. We disclose
   both changes explicitly and avoid claims of the form "denser SAR caused
   the improvement." If we want pure SAR attribution we would need a
   matched-LLM-stack run, which is deferred as future work.

**What we are NOT pre-registering:**

- A new H1 hypothesis. The pre-registered H1 (trade-direction hit rate over
  2019-2024 against 50%) is unchanged. v2.5 is reported as a sensitivity
  alongside v1.
- A threshold change anywhere in Agent 1, 2, or 3.
- A score-to-size mapping. v2.3 signal-confidence stays diagnostic-only.
- Any post-veto change to v2.4's WTI threshold.

**Frozen at:** the commit that introduces this file.

**Next versioned change** (v2.6 or later) requires its own pre-registration
document. If v2.5 ends up dominating the v1 baseline by a wide margin, the
canonical "Strategy 1" reported in the paper's H1 may be promoted to v2.5,
but only after explicit disclosure in §0 / §1 / §9 with the v1 result also
shown for comparison.
