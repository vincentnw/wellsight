# v2.6 Pre-Registration: PM-Style Agent 5 Investment Committee

**Status:** Final system iteration. v2.6 replaces v2.5 as the canonical
Strategy 1 configuration reported in the paper's headline. v2.5 remains
documented as a development baseline alongside v1 to support the
v1 → v2.5 → v2.6 attribution table required by the project rubric.

**Project rubric framing.** The course rubric weights "Multi-agent
architecture & system design" at 20% and explicitly states *"the final
result of the system does not have to be fully correct"* and *"we are
not only looking for a profitable backtest."* v2.6 is the system-design
endpoint that demonstrates a realistic PM-style decomposition of the
investment process. The 2019-2024 backtest result for v2.6 is reported
as **retrospective in-sample system development**, not as a validated
out-of-sample proof — explicit in §11.X of the paper.

## Project goal (unchanged)

> Can a satellite-derived, pre-earnings revenue signal support
> profitable long trades in the U.S. Permian-basin E&P sector?

The satellite signal remains the entry thesis. v2.6 does not change
the input data, the deterministic Agent 2 forecast formula, the
Agent 3 divergence threshold table, the conviction-to-size lookup,
the portfolio construction (long-only, 30 bps round-trip), or the
T-14 entry / T+2 exit holding rule.

## What v2.6 changes vs v2.5

A new agent, **Agent 5_brief (Investment Committee Brief)**, runs
between Agent 4 (News Verification) and the existing Bull / Bear /
Arbiter sub-agents. Its job is to produce a structured JSON brief
covering four areas of point-in-time PM context that Bull/Bear/Arbiter
then consume alongside the existing Agents 1–4 outputs.

**The four brief sections (frozen schema):**

| Section | PIT inputs | Purpose |
|---|---|---|
| `reaction_history` | Prior 8 earnings dates for this ticker (from `earnings_dates.csv`); for each, the 2-trading-day post-earnings stock return (from CRSP); the IBES point-in-time consensus revenue at the time + Compustat actual `saleq` if reported by T-14 | Tells the board whether revenue surprises historically moved this stock, recent earnings volatility, and whether prior trades around earnings were positive/negative for the same ticker |
| `eps_context` | IBES point-in-time EPS consensus at T-14; recent EPS revision direction (3-month and 6-month); operating margin trend from Compustat (last 4 quarters of `oibdpq / saleq`); capex/cost intensity (`capxq / saleq`) | Catches cases where revenue may beat but stock can fall on EPS / margin / capex risk |
| `regime` | WTI 4-week and 12-week return at T (already implemented in `wti_veto.py`); XLE 4-week return at T (from `benchmark_prices.csv`); rolling 60-day stock beta to WTI returns | Tells whether the trade is a real company-specific bet or just oil beta |
| `positioning` | Trailing 3-month stock momentum (from CRSP); current price relative to 52-week high and low (from CRSP); EV/EBITDA snapshot if available point-in-time (Compustat) | Catches extended, crowded, or mechanically-overbought setups |

All four sections are populated by **deterministic Python feature
builders** in `fin580/agents/agent5_brief_features.py`. The LLM does
NOT compute these numbers. The LLM's role in the brief is to write a
1-2 sentence interpretation per section based on the deterministic
fields. The LLM is gpt-4o-mini via OpenAI, same as the rest of v2.5.

## Bull / Bear / Arbiter consumption (unchanged sub-agents, new context)

The three existing sub-agents (Bull gpt-4o-mini, Bear gpt-4o-mini,
Arbiter gpt-5-mini) each receive the original Agents 1–4 inputs PLUS
the Agent 5_brief output. Their output schemas are unchanged.

The Arbiter's prompt is updated to instruct: *"A long trade requires
both a credible revenue beat (Agent 3 says modest_beat or strong_beat)
AND a tradable setup according to the brief. If the brief shows
overwhelming risks (regime stress, EPS deterioration, extended
positioning), or evidence that revenue is not a reliable stock-mover
for this name, choose no_trade or downgrade conviction."*

## The veto-only invariant (HARD code-level constraint)

In `fin580/agents/orchestrator.py`, after the Agent 5 board completes,
the orchestrator MUST enforce:

```python
if agent5_out.decision == "long":
    assert agent3_out.divergence_class in {"modest_beat", "strong_beat"}, (
        f"v2.6 invariant violated: Agent 5 selected long but Agent 3 "
        f"divergence_class is {agent3_out.divergence_class!r}"
    )
```

The constraint is enforced at the orchestrator level, not just the
prompt. This guarantees the system stays revenue-signal-led: Agent 5
can `no_trade` despite a beat (veto), can downgrade conviction tier
(reduce size), but cannot turn a non-beat into a long.

## What Agent 5 is allowed to do

| Action | Allowed? |
|---|---|
| `decision = "no_trade"` regardless of Agent 3 class | Yes (veto) |
| `conviction_tier` downgrade (high → medium → low → none) | Yes |
| `decision = "long"` when Agent 3 says `modest_beat` or `strong_beat` | Yes |
| `decision = "long"` when Agent 3 says `in_line`, `modest_miss`, `strong_miss` | **No (orchestrator assertion fails)** |
| `conviction_tier` upgrade (low → medium → high) | Allowed in principle, but the deterministic conviction-to-size lookup is unchanged: high → 15%, medium → 10%, low → 5% |

## One-shot evaluation discipline

This is the most important methodological commitment. Once v2.6 is
implemented and the pre-reg doc is committed:

1. We run v2.6 on 2019-2024 **once**.
2. We **do not iterate prompts** after seeing the P&L.
3. If the result is worse than v2.5, we report it as observed and
   discuss why in §11.
4. Any further v2.6.x prompt iteration would require a new pre-reg
   doc and would invalidate the current iteration's claims.

The frozen artifacts that constrain "one shot":
- This pre-registration file
- All prompts in `fin580/agents/prompts/agent5_*.txt`
- The deterministic feature builder code in `agent5_brief_features.py`
- The brief agent code in `agent5_brief.py`
- The orchestrator invariant in `orchestrator.py`

## Reporting plan

| Paper section | What it reports |
|---|---|
| §1 Abstract | v2.6 as the canonical system; n / W-L / hit rate / P&L from the v2.6 ledger |
| §6 Multi-Agent Architecture | The brief agent + Bull/Bear/Arbiter, with the veto-only invariant explicitly described |
| §9 Results Headline | v2.6 ledger as the headline; v2.5 numbers reported in a v1/v2.5/v2.6 attribution table |
| §11 New subsection ("System development & in-sample disclosure") | Explicit statement: v2.6 was developed iteratively against 2019-2024 diagnostics from v2.5; the 2019-2024 result is retrospective system-design evaluation, not out-of-sample validation. Per-version trade count, hit rate, mean return, total P&L. WTI veto inversion (§11.9) carried forward unchanged. |
| §12 Limitations | Reiterate: v2.6's 2019-2024 metrics are in-sample retrospective; out-of-sample validation requires 2025+ data, documented as future work. |
| §13 Conclusion | The system-design endpoint; honest framing of what was and was not validated. |

## What v2.6 explicitly does NOT claim

- v2.6 does **not** claim to "improve" v2.5 in a statistically validated
  sense. The 2019-2024 evaluation is in-sample retrospective.
- v2.6 does **not** change the project's H1 hypothesis or the
  satellite-signal-led RQ.
- v2.6 does **not** introduce new entry signals; it only adds context
  for Bull/Bear/Arbiter to veto or downgrade existing v2.5-eligible
  candidates (subset of v2.5's 23 longs).
- v2.6's qualitative LLM judgements are not represented as calibrated
  probabilities; the conviction-to-size lookup remains the
  deterministic 15% / 10% / 5% / 0% mapping.

## Frozen at

This file's commit on `v2-improvements`. Subsequent prompt or schema
changes require a new versioned pre-reg doc (`v2_7_pre_registration.md`
or similar).
