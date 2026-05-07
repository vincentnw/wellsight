# 11. Ablations and Robustness

The two pre-registered ablations (§§11.1–11.2) are mechanically guaranteed by the deterministic Agent-3 gate. Diagnostics and sensitivities are reported in summary; full tables are in Appendix B.

## 11.1 RQ2 — α = 0 ablation

Setting α to zero makes Agent 2's forecast equal IBES consensus exactly. Agent 3 classifies every such cell as `in_line`; the gate short-circuits to `no_trade`. **Result: zero long trades** across 2019–2024. With α = 0, Agents 4 and 5 never fire, so the marginal contribution of the satellite-anchored α = 0.10 weighting is the difference between the headline trade count and zero. RQ2 confirms the system's edge is, in a strict mechanical sense, attributable to the satellite signal, and rules out the failure mode where Agents 4–5 generate spurious "long" signals from qualitative inputs alone.

## 11.2 RQ3 — no-satellite ablation

Forcing Agent 1 to emit all-idle classifications drives `drilling_signal` to zero, so the forecast collapses to consensus and Agent 3 returns `in_line`. **Result: zero long trades.** Any non-trivial hit rate at the headline must therefore be a statement about the satellite signal *in conjunction with* the LLM scaffolding, not the scaffolding alone.

## 11.3 Agent-3 deterministic gate

Agent 3 computes class, percentage, and confidence deterministically in Python after the LLM call (which produces only explanatory text); a schema validator rejects any output where the LLM's class disagrees with the rule. This is the architectural mechanism that makes §§11.1–11.2 mechanically guaranteed.

## 11.4 Defensive fallbacks and provider routing

Agent 4 includes a defensive fallback (permissive default on JSON/runtime errors); a small subset of the 23 trades hit it. The headline routes every LLM call through OpenAI (`gpt-4o-mini` for Agents 2/3/4 and Bull/Bear; `gpt-5-mini` for the Arbiter); total cost ~\$1.00–\$1.50 with caching. The deterministic core is provider-independent. The original spec's confusion-matrix sweep over synthetic-SAR no longer applies after the pivot to real Sentinel-1 RTC; the analogous threshold sensitivity is deferred.

## 11.5 Revenue-mechanism diagnostic and confidence score

Joining each cell's Agent-3 class with Compustat `saleq` actual revenue: **19 of 23 long trades (82.6%) corresponded to actual revenue beats**; only 10 of those 19 became stock wins (52.6%). A correctly-forecast revenue beat is necessary but not sufficient for a positive 2-trading-day exit, since the stock reaction integrates EPS, capex guidance, hedge-book commentary, and the oil-price regime. A 0–100 deterministic signal-confidence score (Appendix B) shows high-tier (n=5) at 60.0% vs medium-tier (n=18) at 50.0% — directionally consistent but within bootstrap noise. Neither diagnostic enters H1.

## 11.6 WTI stress-veto sensitivity

A pre-registered point-in-time veto: for each long trade with entry date T, **block the entry if `wti_4w_return(T) ≤ −10.0%`**. Sizing, costs, and exit are unchanged.

**The veto blocks exactly two trades** — both 2020-Q1 entries during the COVID oil-price collapse: SM 2020-Q1 (4w WTI = −24.6%, baseline +\$91,029) and OVV 2020-Q1 (4w WTI = −16.8%, baseline +\$16,900). These are the system's two largest gains. Post-veto: 21 trades, 10W / 11L (47.6%), mean −2.61%, total **−\$36,096** (vs +\$71,833 baseline); bootstrap p = 0.554.

**Interpretation.** The pre-registered veto is **not protective**. The −10% threshold is misaligned with the system's signal direction in the 2020-Q1 dislocation: both trades opened *after* the WTI negative-pricing event of 2020-04-20 and exited in early May once oil had partially recovered, capturing a regime-conditional mean-reversion the veto would have foreclosed. We do not retune; doing so would constitute curve-fitting on the 2020-Q1 cohort.

## 11.7 Summary

(i) Remove the satellite (or set α = 0) and the system mechanically stops trading. (ii) The Agent-3 deterministic gate eliminates LLM boundary noise. (iii) The deterministic core is provider-independent. (iv) The satellite-driven revenue mechanism was directionally correct on 82.6% of traded cells, but the trade-monetisation layer adds substantial regime-conditional variance. (v) The pre-registered WTI stress veto would have **removed the two largest gains rather than the largest losses**, shifting the aggregate from +\$71,833 to −\$36,096. The constellation argues for caution about the +\$71,833 headline.
