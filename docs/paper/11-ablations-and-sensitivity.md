# 11. Ablations and Robustness

Pre-registered ablations are mechanically guaranteed by the Agent-3 gate; diagnostics and sensitivities follow.

## 11.1 RQ2 — α = 0 ablation

α = 0 makes Agent 2's forecast equal IBES consensus exactly; Agent 3 classifies every cell as `in_line`; gate short-circuits. **Result: zero long trades.** Agents 4 and 5 never fire, so the α = 0.10 weighting is the system's only firing mechanism. Rules out the failure mode where Agents 4–5 generate spurious longs from qualitative inputs alone.

## 11.2 RQ3 — no-satellite ablation

Forcing Agent 1 to all-idle drives `drilling_signal` to zero. **Result: zero long trades.** Any non-trivial hit rate at the headline is a statement about the satellite signal *in conjunction with* the LLM scaffolding, not the scaffolding alone.

## 11.3 Agent-3 deterministic gate

Agent 3 computes class, percentage, and confidence deterministically in Python after the LLM call (text only); a schema validator rejects any output where the LLM's class disagrees with the rule. This is what makes §§11.1–11.2 mechanically guaranteed.

## 11.4 Defensive fallbacks and provider routing

Agent 4 has a permissive default on JSON/runtime errors. LLM calls route through OpenAI (`gpt-4o-mini` for Agents 2/3/4 and Bull/Bear; `gpt-5-mini` for Arbiter); sweep cost ~\$1–\$2 with caching. The deterministic core is provider-independent. SAR threshold sensitivity deferred.

## 11.5 Revenue-mechanism diagnostic

Joining Agent-3 class with Compustat `saleq` actual revenue: **41 of 51 long trades (80.4%) corresponded to actual revenue beats**; 22 of those 41 became stock wins (53.7%). The 10 cells with directionally-wrong forecasts produced 5W / 5L. A correctly-forecast revenue beat is necessary but not sufficient for a positive 2-trading-day exit — the reaction integrates EPS, capex guidance, hedge-book commentary, and the oil-price regime. Does not change H1.

## 11.6 WTI stress-veto sensitivity

Pre-registered point-in-time veto: block long entries with `wti_4w_return(T) ≤ −10.0%`. Sizing, costs, exit unchanged.

**Veto blocks one trade** — OVV 2020-Q1 (4w WTI = −16.8%, baseline +\$16,900). Post-veto: 50 trades, 52.0% hit, **-\$10,266** (vs +\$6,634 baseline); bootstrap p = 0.384, CI [38.1%, 64.8%]. The pre-registered veto is **not protective**: the −10% threshold is misaligned with the system's signal direction in the 2020-Q1 dislocation — OVV 2020-Q1 opened *after* the negative-pricing event and exited as oil partially recovered, capturing a regime-conditional mean-reversion the veto would have foreclosed. We do not retune. A single-threshold WTI guardrail removes a gain, not a loss.

## 11.7 Summary

(i) Remove satellite (or α = 0) → system mechanically stops trading. (ii) Agent-3 gate eliminates LLM boundary noise. (iii) Core is provider-independent. (iv) Revenue mechanism correct on 80% of traded cells; monetisation adds variance. (v) Pre-registered WTI veto removes a gain, shifting +\$6,634 → -\$10,266. The constellation argues for caution about the +\$6,634 headline; +0.18% mean is within transaction-cost noise.
