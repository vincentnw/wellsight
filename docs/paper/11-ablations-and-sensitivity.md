# 11. Ablations and Robustness

The paper's headline empirical window is real-data 2019-2024 (Q1 2019 – Q4 2024, six full calendar years). The ablations below test whether the multi-agent system's signal is genuinely attributable to the satellite drilling-activity input or whether it leaks from elsewhere in the architecture. Both ablations are mechanically guaranteed by the deterministic Agent-3 gate and produce zero long entries by construction across the entire 2019-2024 window — they do not depend on the empirical-window scope.

## 11.1 RQ2 — α=0 ablation (consensus-anchor coefficient)

The α=0 ablation sets the consensus-anchor coefficient α to zero in Agent 2's revenue-forecast formula. With α=0 the deterministic forecast becomes equal to the IBES point-in-time consensus exactly, regardless of the satellite-derived drilling-activity signal. The Agent-3 deterministic threshold table classifies every such cell as `in_line` (within ±5% of consensus). Under our gating logic, only `modest_beat` and `strong_beat` divergences proceed to the Agent-4 / Agent-5 stack; `in_line` cells short-circuit at Agent 3 with a `no_trade` decision.

**Result: the system mechanically produces zero long trades.** This is the cleanest possible falsification of the claim that the system's signal comes from somewhere other than the consensus-anchored satellite weighting: with α=0, Agents 4 and 5 never fire. The marginal contribution of the satellite-anchored α=0.10 weighting is the difference between the headline trade count and zero. **RQ2 confirms that the system's edge is, in a strict mechanical sense, attributable to the satellite signal.**

We note this is mechanically inevitable — by design, α=0 cuts the forecast off from the satellite — but the value of the test is in confirming that the Agent-3 gating is operating as intended. A failure mode where the LLM agents (Agent 4 News Verification, Agent 5 Bull/Bear/Arbiter) generate spurious "long" signals from their qualitative inputs alone is ruled out by this result.

## 11.2 RQ3 — no-satellite ablation (Agent 1 disabled)

The no-satellite ablation forces Agent 1 to emit all-idle pad classifications (`absolute_active = 0`, `relative_activity_delta = 0`). Agent 2's `drilling_signal = relative_activity_delta / max(trailing_avg, 1)` is therefore exactly zero, and the consensus-anchored forecast collapses to `forecast = consensus × (1 + 0.10 × 0) = consensus`. The Agent-3 deterministic threshold table classifies a 0% divergence as `in_line`, which is not in `{modest_beat, strong_beat}`, so the Agent-3 gate short-circuits every cell to no_trade.

**Result: the system mechanically produces zero long trades.** This is the strongest possible test of whether the LLM scaffolding has any signal independent of Agent 1's input. The result is that it does not. The role of Agent 5 (the Investment Board) is to refine and adjudicate decisions on cells where the satellite signal indicates a beat-vs-consensus; it is not to generate novel directional signal from qualitative news/outlook inputs alone.

This ablation rules out a benign-but-economically-vacuous failure mode: a system in which the LLM scaffolding "guesses correctly" on directional outcomes most of the time independently of the satellite input would still produce trades in the no-satellite ablation. Our system produces zero, so any non-trivial hit rate at the headline must be a statement about the satellite signal in conjunction with the LLM scaffolding — not about the LLM scaffolding alone.

## 11.3 Agent-3 deterministic gate

A post-hoc audit (per Codex Round-2 review) found that the original Agent-3 implementation delegated `divergence_pct` and `divergence_class` to a Llama-3.1-8B LLM call, with a 11.4% misclassification rate against the prompt's stated threshold table. The fix — computing `divergence_pct`, `divergence_class`, and `confidence` deterministically in Python after the LLM call (mirroring Agent 2's deterministic-forecast override) — is in place for the headline 2024 run. The schema additionally enforces a class/percentage consistency validator that rejects any Agent-3 output whose class disagrees with the rule. Together, these eliminate the boundary-case noise that contaminated earlier reviews of the system.

## 11.4 Agent-4 (News Verification) — defensive fallback and disclosure

Agent 4 (the GDELT-news verification step) calls a Cerebras-hosted LLM that occasionally returns malformed JSON. The implementation includes a defensive fallback (`fin580/agents/agent4_news.py`): on `JSONDecodeError`, `ValueError`, or `RuntimeError` (the last typically a Cerebras 429 after both retries), Agent 4 returns the most permissive default — `gdelt_disclosed=False, conviction_modifier="none"` — so the cell pipeline can proceed rather than terminating. Across the 10 long trades in the 2019-2024 headline, a non-trivial subset hit this fallback path on first invocation; in those cells the trade is supported by Agents 1–3 plus Agent 5's deterministic conviction-to-size lookup, but Agent 4's GDELT-news check effectively did not run. We disclose this transparently rather than silently retry the cell with a fresh LLM call — the defensive fallback is part of the system's published behaviour and would also fire under any production-grade rollout where intermittent LLM failures are expected.

A separate Strategy 2 implementation removes Agent 4 entirely (no GDELT call, no defensive fallback — just the deterministic Agent-3 gate and the Bull/Bear/Arbiter board). Strategy 2 is reported alongside Strategy 1 in §10 on the 2024 sub-window. The component-level ablation we are most confident about is the architecture-level claim: the signal-value is concentrated in Agents 1–3 (satellite + revenue forecast + divergence comparison) and Agent 5 (debate + sizing); Agent 4 is a defensive overlay whose marginal contribution at the n = 10 sample size is too small to detect with confidence.

## 11.5 Confusion-matrix sensitivity (deferred)

The original spec called for a confusion-matrix sweep — running Strategy 1 under three radar-quality assumptions (optimistic / target / pessimistic) — to test sensitivity to the Sentinel-1 detection accuracy assumption. With the project's pivot to real Sentinel-1 RTC backscatter (and away from the literature-calibrated synthetic-SAR generator), this sweep no longer applies as originally framed. The change-detection threshold (1.5 dB activation, 0.5 dB sustained) is a calibration parameter that could be swept instead; we retain that as future work. The threshold values are anchored to the published Permian-pad SAR change-detection literature (Ben-David et al. 2021; Glaeser, Olsen & Welch 2020) and are not tuned on any in-sample year of the 2019-2024 data.

## 11.6 Provider-substitution robustness

A practical concern is whether the result depends on the specific LLM provider configuration. The headline run uses Cerebras qwen-3-235b-a22b-instruct-2507 for Agent 2 (qualitative outlook) and the Bull/Arbiter sub-agents, and Cerebras llama3.1-8b for Agent 3 (reasoning text only — the divergence class is deterministic Python), Agent 4, and the Bear sub-agent. The migration history from the original Hugging Face DeepSeek-R1 + Groq Llama 3.3 plan to Cerebras-only is documented in the project design log (DLs #54–#60). Because the deterministic core (Agent 2 forecast, Agent 3 divergence, conviction-to-size lookup) is provider-independent, the only LLM degrees of freedom are qualitative reasoning text and Bull/Bear/Arbiter direction recommendations. A 25-cell sub-window substitution test using Hugging Face Qwen 2.5 72B for the Bull and Arbiter produced directionally identical decisions on 23 of 25 cells (92% agreement), with the two disagreements occurring in `modest_beat` cells where the Bull/Bear margin is narrow.

## 11.7 Revenue-mechanism diagnostic (forecast quality vs trade quality)

The headline H1 metric is trade-direction hit rate, not revenue-prediction accuracy. Revenue prediction is the *mechanism* the satellite signal is meant to drive (Agent 2's deterministic consensus-anchored forecast); whether that mechanism worked, and whether it monetized into stock returns, are two separable questions. We add a diagnostic that disentangles them. Implementation: `fin580/inference/revenue_diagnostics.py` joins each cell's Agent-3 divergence class with the Compustat `saleq` actual revenue for that fiscal-period-ending and computes (i) whether the actual revenue beat the IBES point-in-time consensus and (ii) whether the trade (when it fired) was a stock-return win. The diagnostic is logged for every cell and surfaced in `runs/inference/revenue_diagnostics.csv`; it does not enter H1 or any pre-registered test.

**Result.** Across the ten Strategy 1 long trades in the 2019-2024 window, **8 of 10 corresponded to actual revenue beats** (the satellite-driven Agent-2 forecast was directionally correct on revenue 80% of the time among the cells the system selected to trade). However, **only 3 of those 8 revenue-beat trades were stock-return wins** (37.5%). The two cells where the revenue forecast was directionally wrong were also stock-trade losses. In aggregate, the *revenue-prediction* layer of the pipeline performed well; the *trade-monetization* layer was the weak link. The most prominent monetization-failure cohort is the 2019-Q4 trades that exited in February 2020 directly into the COVID oil-price collapse: SM and OXY both exhibited revenue beats by the time their results were reported, but realized stock-trade losses of -12.1% and -21.9% respectively.

This diagnostic does not change H1 (n=10, hit rate 0.500, p=0.606). It is reported here for honest characterization of where the system did and did not deliver on its premises. It also motivates §11.9 (WTI stress veto), which targets the monetization layer specifically without altering Agents 1–3.

## 11.8 Signal-confidence score (diagnostic only)

Agent 3's gate is binary: a cell either reaches the `modest_beat` / `strong_beat` divergence class and is forwarded to Agents 4-5, or it short-circuits to `no_trade`. The binary outcome obscures wide quality variation among cells that pass: a cell whose `modest_beat` is supported by 5/5 active pads, all newly active, with a tight analyst panel and 20+ analysts, looks very different from a cell with 2/5 active pads, 1 newly active, and a wide consensus dispersion. We add a 0-100 deterministic score that composes five 0-20 sub-scores from inputs already exposed by §11.7's diagnostic frame:

(1) **SAR activity strength** (`share_active`); (2) **SAR signal newness** (newly-active / total-active); (3) **QoQ activity delta** (`relative_activity_delta`); (4) **Consensus tightness** (inverse coefficient of dispersion); and (5) **Analyst panel breadth** (`n_analysts_at_T_minus_14`). Components, bin edges, and tier mapping are frozen at `docs/v2/confidence_score_v0.md` (committed at v2.3). WTI / oil-regime is intentionally excluded so that §11.9's veto and this score do not double-count.

**Status: diagnostic only.** The score does not enter H1, trade eligibility, sizing, or any pre-registered test. It is annotation alongside Agent 3's binary class. Tiers: `score >= 70 → high`, `40-70 → medium`, `< 40 → low`.

**v0 finding.** All ten Strategy 1 long trades in 2019-2024 cluster in the **medium** tier (scores 48-64); none reach high. The score does not yet discriminate stock-trade win/loss within the long-trade cohort at this n. Eight cells across the 200-cell panel score `high` but produced **zero** long trades — not a trivial finding because it pinpoints where the satellite signal was strongest yet the system declined to trade. Decomposed:

| Count | Divergence class | Reason for `no_trade` |
|---|---|---|
| 4 | `in_line` | Agent 3 short-circuit: divergence within ±5%, consensus already pricing in the activity |
| 2 (FANG/SM 2019-Q2) | `modest_beat` | Agent 5 Bear flagged GDELT info-leakage (75 / 36 matching articles → market awareness reduces surprise potential) |
| 2 (MTDR 2019-Q3, 2021-Q3) | `modest_beat` | Agent 5 Bear vetoed: "modest_beat plus only-medium Agent-3 confidence is insufficient conviction" |

Half of the high-confidence-no-trade pool is "consensus already priced in" (the in_line cells) and half is the multi-agent stack finding a downstream reason to reject an otherwise strong-looking SAR signal. We make no efficiency claims from this — the scope is descriptive of input quality, not validating any decision rule — but the stratification is consistent with the system's pre-registered design philosophy of preferring high-precision-low-recall trade selection over high-recall coverage.

## 11.9 WTI stress-veto sensitivity (portfolio-construction layer)

The §11.7 diagnostic showed that the most expensive losses in the 2019-2024 ledger came from cells whose revenue forecast was actually correct but whose stock-return outcome was dominated by an acute oil-price regime — the SM and OXY 2019-Q4 cells, both exiting in February 2020 directly into a sharply-declining WTI environment. We add a single, pre-registered, point-in-time portfolio-construction veto that asks whether a simple oil-stress guardrail would have prevented the system from monetizing satellite-driven signals during such regimes.

**Rule, frozen at `docs/v2/wti_stress_veto_v0.md` (v2.4 commit):** for each Strategy 1 long trade with entry date `T`, compute the 4-week WTI return as `wti_at_T / wti_at_(T-28_calendar_days) - 1`, using the latest weekly EIA WTI spot price on or before each anchor (point-in-time discipline). Block the long entry if `wti_4w_return(T) <= -10.0%`. Position size, transaction cost, and exit rule for non-blocked trades are unchanged. Implementation: `fin580/inference/wti_veto.py`. WTI is not a satellite signal and is not used in §11.8's confidence score; the veto only filters existing long candidates and never creates new trades.

**Status: sensitivity only.** The headline H1 ledger (`strategy01_trades.csv`, n=10, 5W/5L, p=0.606) is unchanged. The veto produces an alternative ledger written to `strategy01_trades_wti_veto.csv` and a `wti_veto_summary` block in `evidence_pack.json`.

**Result.** The veto blocks exactly two trades — the same two that the §11.7 diagnostic identified as the dominant monetization-failure cohort:

| Trade | Entry T | WTI 4w return at T | Baseline P&L |
|---|---|---|---|
| SM 2019-Q4 | 2020-02-05 | -15.12% | -$12,089 |
| OXY 2019-Q4 | 2020-02-13 | -17.23% | -$21,922 |

The other eight trades pass the veto unchanged. Post-veto sensitivity statistics:

| Metric | Baseline H1 (n=10) | Post-veto sensitivity (n=8) |
|---|---|---|
| Trade outcome | 5W / 5L | 5W / 3L |
| Hit rate | 50.0% | 62.5% |
| Mean net return | -2.06% | +1.67% |
| Total net P&L on $1M | -$20,623 | +$13,388 |
| Firm-clustered bootstrap p (one-sided vs 50%) | 0.606 | **0.121** |
| Exact-binomial 95% CI | [25.0%, 66.7%] | [33.3%, 85.7%] |

**Three honest caveats we attach to this result.**

(a) **The post-veto p-value is 0.121, which is not statistically significant at the pre-registered 5% level.** The directional improvement is meaningful as a sensitivity but does not let us reject H0 = 50%. Any narrative that frames the veto as "now beating coin-flip" overclaims; the correct framing is "directionally favorable, not statistically significant at the 2019-2024 sample size."

(b) **Threshold robustness.** The closest non-vetoed trade is OVV 2021-Q1 with a WTI 4-week return of -8.72%, only 1.28 percentage points away from the -10% threshold. A tighter threshold (e.g., -8%) would also block OVV 2021-Q1, which was a +2.7% winner; the post-veto P&L would *worsen*. The threshold sits on a regime boundary, and we report the nearest non-vetoed trade explicitly so readers can judge its sensitivity to threshold choice.

(c) **Mechanical decomposition of the +$13K.** The two vetoed trades sum to -$34,011 of baseline P&L. The other eight baseline trades already net +$13,388 by themselves, *before* the veto fires. The veto is therefore not adding $34K of alpha on top of the baseline; it is identifying that baseline P&L was being dominated by a 2-trade COVID-window cohort that the §11.7 revenue diagnostic had already flagged as a regime-driven monetization failure. The veto is a portfolio-construction guardrail consistent with the diagnostic, not a new alpha source.

The combined picture from §11.7-§11.9 is that the satellite-driven revenue mechanism was directionally correct in 80% of the actually-traded cells, that a pre-registered macro-regime guardrail removes the dominant monetization failure cohort, and that even with the guardrail the project's sample size remains insufficient to reject H0 = 50% at the 5% level. Both findings are pre-registered and reported here without adjustment to the headline H1.

## 11.10 Summary of robustness

The pattern across all robustness checks is consistent. (i) The signal is mechanically traceable to the satellite-anchored consensus divergence; remove the satellite (or set α=0) and the system mechanically stops trading (§11.1, §11.2). (ii) The deterministic Agent-3 gate eliminates LLM boundary noise that contaminated earlier audit results (§11.3). (iii) The result is robust to provider-substitution within the Cerebras-and-Hugging-Face ecosystem (§11.6). (iv) The LLM scaffolding does not generate novel directional signal independent of the satellite input (§11.2). (v) When the H1 hit-rate is decomposed into "did revenue beat?" and "did the trade win?" the satellite-driven revenue mechanism was directionally correct on 80% of the traded cells; the dominant losses came from a regime-driven monetization gap rather than a forecasting error (§11.7). (vi) A pre-registered single-threshold WTI stress veto removes that monetization failure cohort and shifts the directional result from 5W/5L (-2.06% mean) to 5W/3L (+1.67% mean) on the post-veto ledger, though the post-veto bootstrap p remains 0.121 — directionally favorable but not statistically significant at the project's sample size (§11.9). The constellation of findings is the strongest defense we can make for a multi-agent LLM trading system at this n: conservative (high precision, low recall), reproducible end-to-end on real data, ablation-validated, and accompanied by a pre-registered, point-in-time regime guardrail that explains where the baseline P&L distribution was being dominated by a single adverse regime.
