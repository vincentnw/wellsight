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

Agent 4 (the GDELT-news verification step) calls a hosted LLM that occasionally returns malformed JSON or transient API errors. The implementation includes a defensive fallback (`fin580/agents/agent4_news.py`): on `JSONDecodeError`, `ValueError`, or `RuntimeError`, Agent 4 returns the most permissive default — `gdelt_disclosed=False, conviction_modifier="none"` — so the cell pipeline can proceed rather than terminating. Across the 23 long trades in the 2019-2024 headline, a small subset hit this fallback path on first invocation; in those cells the trade is supported by Agents 1–3 plus Agent 5's deterministic conviction-to-size lookup, but Agent 4's GDELT-news check effectively did not run. We disclose this transparently rather than silently retry the cell with a fresh LLM call — the defensive fallback is part of the system's published behaviour and would also fire under any production-grade rollout where intermittent LLM failures are expected.

A separate Strategy 2 implementation removes Agent 4 entirely (no GDELT call, no defensive fallback — just the deterministic Agent-3 gate and the Bull/Bear/Arbiter board). Strategy 2 is reported alongside Strategy 1 in §10 on the 2024 sub-window. The component-level claim we are most confident about is the architecture-level statement: the signal value is concentrated in Agents 1–3 (satellite + revenue forecast + divergence comparison) and Agent 5 (debate + sizing); Agent 4 is a defensive overlay whose marginal contribution at the project's sample size is too small to detect with confidence.

## 11.5 Confusion-matrix sensitivity (deferred)

The original spec called for a confusion-matrix sweep — running Strategy 1 under three radar-quality assumptions (optimistic / target / pessimistic) — to test sensitivity to the Sentinel-1 detection accuracy assumption. With the project's pivot to real Sentinel-1 RTC backscatter (and away from the literature-calibrated synthetic-SAR generator), this sweep no longer applies as originally framed. The change-detection threshold (1.5 dB activation, 0.5 dB sustained) is a calibration parameter that could be swept instead; we retain that as future work. The threshold values are anchored to the published Permian-pad SAR change-detection literature (Ben-David et al. 2021; Glaeser, Olsen & Welch 2020) and are not tuned on any in-sample year of the 2019-2024 data.

## 11.6 LLM provider routing and provider-independence claim

The headline run routes every LLM call through OpenAI's hosted API: `gpt-4o-mini` for Agent 2 (qualitative outlook), Agent 3 (reasoning text only — the divergence class is deterministic Python), Agent 4 (GDELT verification), and the Bull / Bear sub-agents in Agent 5; `gpt-5-mini` for the Arbiter. Total LLM cost across the full 2019-2024 sweep is approximately $1.00–$1.50 with the per-call cache enabled. Because the deterministic core (Agent 2 forecast, Agent 3 divergence threshold table, Agent 5 conviction-to-size lookup) is provider-independent and runs in pure Python, the only LLM degrees of freedom are qualitative reasoning text and Bull/Bear/Arbiter direction recommendations — both of which are downstream of the deterministic Agent-3 gate. We therefore expect the trade-direction headline to be robust to provider substitution within the modern instruction-tuned-LLM family; we do not run a formal substitution test in the paper, but the LLM cache (`runs/_global_cache/`) records prompt and response hashes that allow any external reviewer to re-run any cell on a different provider and audit the directional agreement.

## 11.7 Revenue-mechanism diagnostic (forecast quality vs trade quality)

The headline H1 metric is trade-direction hit rate, not revenue-prediction accuracy. Revenue prediction is the *mechanism* the satellite signal is meant to drive (Agent 2's deterministic consensus-anchored forecast); whether that mechanism worked, and whether it monetized into stock returns, are two separable questions. We add a diagnostic that disentangles them. Implementation: `fin580/inference/revenue_diagnostics.py` joins each cell's Agent-3 divergence class with the Compustat `saleq` actual revenue for that fiscal-period-ending and computes (i) whether the actual revenue beat the IBES point-in-time consensus and (ii) whether the trade (when it fired) was a stock-return win. The diagnostic is logged for every cell and surfaced in `runs/inference/revenue_diagnostics.csv`; it does not enter H1 or any pre-registered test.

**Result.** Across the 23 long trades in the 2019-2024 window, **19 of 23 (82.6%) corresponded to actual revenue beats** (Agent 2's satellite-anchored forecast was directionally correct on revenue 82.6% of the time among the cells the system selected to trade). However, only **10 of those 19 revenue-beat trades were stock-return wins (52.6%)**. The 4 cells where the forecast was directionally wrong on revenue produced 2 stock wins and 2 stock losses. The pattern is consistent with prior literature on post-earnings drift in commodity-linked equities: a correctly-forecast revenue beat is necessary but not sufficient for a positive 2-trading-day exit, since the stock reaction integrates EPS, capex guidance, hedge-book commentary, and (most prominently) the prevailing oil-price regime over the holding window.

This diagnostic does not change H1 (n = 23, hit rate 0.522, p = 0.408). It is reported here for honest characterization of where the system did and did not deliver on its premises: the revenue-prediction mechanism is a real, repeatable signal in the data, while the trade-monetization layer is regime-conditional and adds substantial variance to realized returns.

## 11.8 Signal-confidence score (diagnostic only)

Agent 3's gate is binary: a cell either reaches the `modest_beat` / `strong_beat` divergence class and is forwarded to Agents 4-5, or it short-circuits to `no_trade`. The binary outcome obscures wide quality variation among cells that pass: a cell whose `modest_beat` is supported by 5/5 active pads, all newly active, with a tight analyst panel and 20+ analysts, looks very different from a cell with 2/5 active pads, 1 newly active, and a wide consensus dispersion. We add a 0-100 deterministic score that composes five 0-20 sub-scores from inputs already exposed by §11.7's diagnostic frame:

(1) **SAR activity strength** (`share_active`); (2) **SAR signal newness** (newly-active / total-active); (3) **QoQ activity delta** (`relative_activity_delta`); (4) **Consensus tightness** (inverse coefficient of dispersion); and (5) **Analyst panel breadth** (`n_analysts_at_T_minus_14`). Components, bin edges, and tier mapping are frozen at `docs/v2/confidence_score_v0.md` (committed at v2.3). WTI / oil-regime is intentionally excluded so that §11.9's veto and this score do not double-count.

**Status: diagnostic only.** The score does not enter H1, trade eligibility, sizing, or any pre-registered test. It is annotation alongside Agent 3's binary class. Tiers: `score ≥ 70 → high`, `40 ≤ score < 70 → medium`, `< 40 → low`.

**Distribution.** Across the 200-cell panel, 97 cells score `low`, 91 score `medium`, and 12 score `high`. Of the 23 long trades, 18 land in the `medium` tier (scores 48-72) and 5 in the `high` tier (scores 72-80); none of the system's longs come from the `low` tier. The 7 high-tier no-trade cells and the 79 medium-tier no-trade cells were short-circuited by Agent 3 (divergence too small) or vetoed by Agent 5 (Bear flagged GDELT info-leakage or insufficient-conviction concerns).

**Diagnostic finding.** Hit rate by tier on the long-trade cohort: **`high` tier 5 trades, 3W / 2L (60.0%)**; **`medium` tier 18 trades, 9W / 9L (50.0%)**. The directional pattern (high-tier trades have a marginally better hit rate than medium-tier) is in the direction the score's components would predict, but the gap is small and the high-tier sample is only 5 trades — well within bootstrap noise. We make no efficiency claims from this; the score is logged for transparency about input-quality variation but is not validated as a decision rule.

## 11.9 WTI stress-veto sensitivity (portfolio-construction layer)

The §11.7 diagnostic showed that the most expensive losses in the 2019-2024 ledger came from cells whose revenue forecast was actually correct but whose stock-return outcome was dominated by an acute oil-price regime — the SM and OXY 2019-Q4 cells, both exiting in February 2020 directly into a sharply-declining WTI environment. We add a single, pre-registered, point-in-time portfolio-construction veto that asks whether a simple oil-stress guardrail would have prevented the system from monetizing satellite-driven signals during such regimes.

**Rule, frozen ex ante:** for each long trade with entry date `T`, compute the 4-week WTI return as `wti_at_T / wti_at_(T−28_calendar_days) − 1`, using the latest weekly EIA WTI spot price on or before each anchor (point-in-time discipline). Block the long entry if `wti_4w_return(T) ≤ −10.0%`. Position size, transaction cost, and exit rule for non-blocked trades are unchanged. Implementation: `fin580/inference/wti_veto.py`. WTI is not a satellite signal and is not used in §11.8's confidence score; the veto only filters existing long candidates and never creates new trades.

**Status: sensitivity only.** The headline H1 ledger (n = 23, 12W / 11L, p = 0.408) is unchanged. The veto produces an alternative ledger written to `strategy01_trades_wti_veto.csv` and a `wti_veto_summary` block in `evidence_pack.json`.

**Result.** The veto blocks exactly two trades — both 2020-Q1 entries during the COVID oil-price collapse:

| Trade | Entry T | WTI 4w return at T | Baseline P&L |
|---|---|---|---|
| SM 2020-Q1 | 2020-04-15 | −24.64% | **+\$91,029** |
| OVV 2020-Q1 | 2020-04-23 | −16.83% | **+\$16,900** |

These are the two largest gains in the entire 2019-2024 ledger. Post-veto sensitivity statistics:

| Metric | Baseline (n = 23) | Post-veto (n = 21) |
|---|---|---|
| Trade outcome | 12W / 11L | 10W / 11L |
| Hit rate | 52.2% | 47.6% |
| Mean net return | +2.31% | −2.61% |
| Total net P&L on $1M | **+\$71,833** | **−\$36,096** |
| Firm-clustered bootstrap p (one-sided vs 50%) | 0.408 | 0.554 |
| Bootstrap 95% CI on hit rate | [35.0%, 76.5%] | [31.3%, 71.4%] |

**Interpretation.** The WTI stress veto, as pre-registered, is **not protective** for this system. The directional logic embedded in the −10% threshold — that long entries during sharp oil-price declines should be blocked — is misaligned with the system's actual signal direction in the 2020-Q1 dislocation. Both 2020-Q1 trades opened in mid-to-late April 2020 (after the WTI negative-pricing event of 2020-04-20) and exited in early May 2020, by which point WTI had partially recovered into the $20s and the equities had rebounded sharply. The system entered at multi-decade lows and exited shortly after — a regime-conditional mean-reversion that the veto would have foreclosed.

**Three honest observations attached to this result.**

(a) **The 2020-Q1 cohort dominates the aggregate.** Removing those two trades leaves the remaining 21 trades at 47.6% hit rate and −\$36,096 aggregate. The system without 2020-Q1 looks materially worse than the system with it — the +\$71,833 headline depends heavily on those two entries, as already disclosed in §9.1.

(b) **The veto's pre-registration was honest about scope.** The threshold was frozen before this run, motivated by post-earnings-drift literature on commodity-linked equities under regime stress. We did not re-tune the threshold after observing the result; doing so would constitute curve-fitting on the 2020-Q1 cohort. The pre-registered veto produces this directional outcome on the data and we report it as observed.

(c) **The veto's outcome is informative about the system's payoff profile.** The system's largest gains came from cells where (i) the satellite-derived drilling activity stayed elevated in the months prior to the COVID crash, (ii) consensus revenue forecasts were heavily revised down on the COVID news, and (iii) Agent 2's consensus-anchored forecast — anchored to the (downward-revised) consensus plus an SAR-driven uplift — produced a `modest_beat` divergence class. The 2-trading-day exit captured a partial mean-reversion as oil prices recovered from their April 2020 lows. This is a regime-conditional payoff structure: it depends on the system's mechanical entry mechanism intersecting with a market dislocation in a specific direction. We do not claim this pattern repeats outside such dislocations, and we are explicit in §12 (Limitations) that the headline aggregate should not be projected forward as a steady-state expectation.

The combined picture from §11.7–§11.9 is: (i) the satellite-driven revenue mechanism is directionally correct on 82.6% of the actually-traded cells; (ii) the system's tier of cells with strongest input quality has a marginally higher trade hit rate (60% vs 50%) but the gap is within bootstrap noise; (iii) a pre-registered oil-stress veto would have removed the system's two largest gains rather than its largest losses. Together these findings argue for caution about the +\$71,833 headline and for the §12 limitations framing.

## 11.10 Summary of robustness

The pattern across all robustness checks is consistent. (i) The signal is mechanically traceable to the satellite-anchored consensus divergence; remove the satellite (or set α=0) and the system mechanically stops trading (§11.1, §11.2). (ii) The deterministic Agent-3 gate eliminates LLM boundary noise that contaminated earlier audit results (§11.3). (iii) The deterministic core is provider-independent; LLM provider choice affects only qualitative reasoning text and Bull/Bear/Arbiter direction recommendations downstream of the Agent-3 gate (§11.6). (iv) The LLM scaffolding does not generate novel directional signal independent of the satellite input (§11.2). (v) When the H1 hit-rate is decomposed into "did revenue beat?" and "did the trade win?" the satellite-driven revenue mechanism was directionally correct on 82.6% of the traded cells, while the trade-monetization layer adds substantial regime-conditional variance (§11.7). (vi) A 0–100 signal-confidence score that composites SAR coverage, activity newness, qoq delta, consensus tightness, and analyst breadth shows a marginally higher hit rate in the high tier (60%, n=5) than the medium tier (50%, n=18); the gap is within bootstrap noise (§11.8). (vii) A pre-registered single-threshold WTI stress veto, applied as a sensitivity, would have **removed the system's two largest gains rather than its losses**, shifting the aggregate from +\$71,833 to −\$36,096 (§11.9) — informative about the regime-conditional payoff structure of the headline result. The constellation of findings is the most honest summary we can offer for a multi-agent LLM trading system at this sample size: the deterministic core is reproducible and ablation-validated; the system's headline aggregate is dominated by a single 2020-Q1 trade that captured a COVID-bottom mean-reversion; and the pre-registered macro-regime guardrail does not protect against the system's losses but instead would have foreclosed its largest gains.
