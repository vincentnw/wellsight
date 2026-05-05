# 12. Limitations and Threats to Validity

## 12.1 SAR change-detection rule

The Sentinel-1 RTC ingestion is real and the per-pad backscatter time series are real radar pixels — but the change-detection rule is intentionally simple: a fixed +1.5 dB / +0.5 dB threshold on quarterly mean VV backscatter, anchored to Ben-David et al. (2021) and Glaeser, Olsen & Welch (2020). The rule has no CV/DL component, no polarimetric decomposition, and no coherent change detection on SLC products. A more sophisticated pipeline — a U-Net or fine-tuned earth-observation foundation model such as NASA-IBM Prithvi — would catch finer signals and emit per-pad probabilities. We treat this as the system's most consequential simplification.

## 12.2 Sample size, IBES proxy, LLM determinism

The full backtest produces 51 long trades across 200 cells (the gate suppresses ~75%). With n = 51 the firm-clustered bootstrap fails to reject H0 = 50% (p = 0.328); the firm-clustered 95% CI on mean return [-1.83%, +1.53%] straddles zero.

The IBES consensus uses `ANNDATS_ACT` as a proxy for pre-T-14 announcement-date provability (WRDS Wall Street Horizon not subscribed). U.S. E&P firms pre-announce calendars 30+ days ahead, so the proxy is unbiased in expectation but subtly biased when announcement dates shift. The survivorship leak (Anderson & Akbas 2020) is mitigated by the `(REVDATS == ANNDATS) OR (REVDATS > T)` filter.

LLM determinism: all calls run at temperature 0.0 with a per-call cache. OpenAI does not guarantee bit-for-bit determinism, but variance is small for constrained-JSON outputs and the deterministic-numerical-core means trades are insensitive to small qualitative-text changes.

## 12.3 Universe, architecture, scope

The ten-firm universe is selected on Permian concentration, correlated with mid-/small-cap status; the universe was selected knowing all ten firms exist as of 2025, itself a forward-looking selection. CRGY produces zero FracFocus Permian disclosures. The 25-pad sample is bandwidth-limited at ~12 hours wall-clock. The deterministic conviction-to-size lookup preserves traceability at the cost of bounded achievable Sharpe. Strategies 2–10 are 2024-only; extending them is the most direct future-work item.

## 12.4 Recovery-regime over-firing and signal saturation

The corrected backtest's most consequential structural limitation is **2021 over-firing**: 16 long trades in 2021 (post-COVID recovery) vs 2–12 in every other year. **13 of 16 (81%) reach `modest_beat` via a clipped `drilling_signal = +1.0`**, pinning forecast divergence at exactly +10.0%. Mechanism: trailing-4Q active-pad averages in 2021 are dominated by the COVID 2020 trough (most pads idle by Agent 1's rule), so baselines are low (1.25–7.75). 2021 active counts (7–23) divided by those baselines produce raw signals of 1.4–7.5, all clipped at +1.0.

The clip prevents runaway forecasts when baselines approach zero, but the consequence is that the gate cannot distinguish a modest recovery from an explosive one when the baseline collapsed. 13 of 16 cells share an identical +10.0% divergence number, so Agent-3 loses rank-ordering within the cohort. This explains why the 2021 cohort produces 16 trades at 62.5% hit but only +0.50% mean — the gate fires broadly without ranking. We do not modify the clip or baseline formula post-hoc; §13 lists "regime-aware sizing" as future work. Excluding the 2021 cohort leaves 35 trades at 17W / 18L (48.6%) and aggregate +\$1,840.

## 12.5 External validity

**Regime.** The 2021 recovery cohort is the largest single-year trade-count contributor (16 of 51) but not aggregate-P&L. Generalising to future regime breaks is not supported by the historical backtest — the over-firing pattern is specific to the post-COVID setup and the design's failure mode in that setup. **Crowding.** If the satellite signal becomes commercially available at scale, the edge will compress within 12–36 months per the signal-decay literature.

## 12.6 Documented portfolio rules versus enforced behaviour

The runner manifest records `max_names: 8` as a documented portfolio-construction parameter. In the corrected sample the cap **never binds** — the maximum simultaneous longs in any quarter is 8 (2021-Q3, all eight then-eligible firms). The cap is not enforced in the inference layer; the headline P&L counts every long the system generated. Because the cap never binds, the headline is unaffected. §8 has been adjusted to describe the cap as a documented parameter that did not bind in this sample rather than a binding rule with priority semantics.
