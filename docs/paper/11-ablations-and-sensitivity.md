# 11. Ablations and Robustness

The two pre-registered ablations (§§11.1–11.2) are mechanically guaranteed by the deterministic Agent-3 gate. Diagnostics and sensitivities are reported in summary; full tables are in Appendix B.

## 11.1 RQ2 — α = 0 ablation

Setting α to zero makes Agent 2's forecast equal IBES consensus exactly. Agent 3 classifies every such cell as `in_line`; the gate short-circuits to `no_trade`. **Result: zero long trades** across 2019–2024. With α = 0, Agents 4 and 5 never fire, so the marginal contribution of the satellite-anchored α = 0.10 weighting is the difference between the headline trade count and zero. RQ2 confirms the system's trade-firing mechanism is, in a strict mechanical sense, attributable to the satellite signal, and rules out the failure mode where Agents 4–5 generate spurious "long" signals from qualitative inputs alone.

## 11.2 RQ3 — no-satellite ablation

Forcing Agent 1 to emit all-idle classifications drives `drilling_signal` to zero, so the forecast collapses to consensus and Agent 3 returns `in_line`. **Result: zero long trades.** Any non-trivial hit rate at the headline must therefore be a statement about the satellite signal *in conjunction with* the LLM scaffolding, not the scaffolding alone.

## 11.3 Agent-3 deterministic gate

Agent 3 computes class, percentage, and confidence deterministically in Python after the LLM call (which produces only explanatory text); a schema validator rejects any output where the LLM's class disagrees with the rule. This is the architectural mechanism that makes §§11.1–11.2 mechanically guaranteed.

## 11.4 Defensive fallbacks and provider routing

Agent 4 has a defensive fallback (permissive default on JSON/runtime errors). The headline routes every LLM call through OpenAI (`gpt-4o-mini` for Agents 2/3/4 and Bull/Bear; `gpt-5-mini` for the Arbiter); total cost ~\$1.00–\$2.00 with caching. The deterministic core is provider-independent. Threshold sensitivity over the SAR change-detection rule is deferred.

## 11.5 Revenue-mechanism diagnostic

Joining each cell's Agent-3 class with Compustat `saleq` actual revenue: **41 of 51 long trades (80.4%) corresponded to actual revenue beats**; 22 of those 41 became stock-return wins (53.7%). The 10 cells where the satellite-anchored forecast was directionally wrong on revenue produced 5W / 5L. A correctly-forecast revenue beat is necessary but not sufficient for a positive 2-trading-day exit, since the stock reaction integrates EPS, capex guidance, hedge-book commentary, and the prevailing oil-price regime. The diagnostic does not change H1.

## 11.6 WTI stress-veto sensitivity

A pre-registered point-in-time veto: for each long trade with entry date T, **block the entry if `wti_4w_return(T) ≤ −10.0%`**. Sizing, costs, and exit are unchanged.

**The veto blocks one trade** — OVV 2020-Q1 (4w WTI = −16.8%, baseline +\$16,900). Post-veto: 50 trades, 26W / 24L (52.0%), total **-\$10,266** (vs +\$6,634 baseline); bootstrap p = 0.384; 95% CI on hit rate [38.1%, 64.8%].

**Interpretation.** The pre-registered veto is **not protective**. The −10% threshold is misaligned with the system's signal direction in the 2020-Q1 dislocation: OVV 2020-Q1 opened *after* the WTI negative-pricing event of 2020-04-20 and exited in early May as oil partially recovered, capturing a regime-conditional mean-reversion the veto would have foreclosed. We do not retune. The qualitative finding is that a single-threshold WTI guardrail removes a gain, not a loss.

## 11.7 Summary

(i) Remove the satellite (or set α = 0) → system mechanically stops trading. (ii) The Agent-3 gate eliminates LLM boundary noise. (iii) The deterministic core is provider-independent. (iv) Revenue mechanism directionally correct on 80% of traded cells; trade-monetisation adds variance independent of revenue accuracy. (v) Pre-registered WTI veto **removes a gain, not a loss**, shifting aggregate from +\$6,634 to -\$10,266. The constellation argues for caution about the +\$6,634 headline; mean return per trade (+0.18%) is within transaction-cost noise.
