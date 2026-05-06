# 12. Limitations and Threats to Validity

## 12.1 SAR change-detection rule

The Sentinel-1 RTC ingestion and per-pad backscatter are real, but the change-detection rule is intentionally simple: fixed +1.5/+0.5 dB thresholds on quarterly mean VV, anchored to Ben-David et al. (2021) and Glaeser, Olsen & Welch (2020). No CV/DL, no polarimetric decomposition, no coherent change detection on SLC products. A U-Net or fine-tuned EO foundation model (e.g., NASA-IBM Prithvi) would catch finer signals and emit per-pad probabilities. The system's most consequential simplification.

## 12.2 Sample size, IBES proxy, LLM determinism

n = 51 / 200 cells; bootstrap p = 0.328; 95% CI on mean return [-1.83%, +1.53%] straddles zero.

IBES consensus uses `ANNDATS_ACT` as proxy for pre-T-14 provability (Wall Street Horizon not subscribed). U.S. E&P firms pre-announce calendars 30+ days ahead — unbiased in expectation but subtly biased when announcement dates shift. The survivorship leak (Anderson & Akbas 2020) is mitigated by the `(REVDATS == ANNDATS) OR (REVDATS > T)` filter.

LLM determinism: temperature 0.0 + per-call cache. OpenAI does not guarantee bit-for-bit determinism but variance is small for constrained-JSON outputs; the deterministic core means trades are insensitive to small qualitative-text changes.

## 12.3 Universe, architecture, scope

The ten-firm universe selects on Permian concentration (correlated with mid-/small-cap status); choosing tickers known to exist as of 2025 is itself forward-looking. CRGY produces zero FracFocus Permian disclosures. 25-pad sample bandwidth-limited at ~12 hours wall-clock. Deterministic conviction-to-size lookup preserves traceability at the cost of bounded Sharpe. Strategies 2–10 are 2024-only; extending them is the most direct future-work item.

## 12.4 Recovery-regime over-firing and signal saturation

The most consequential structural limitation is **2021 over-firing**: 16 long trades in 2021 (post-COVID recovery) vs 2–12 in every other year. **13 of 16 (81%) reach `modest_beat` via a clipped `drilling_signal = +1.0`**, pinning divergence at +10.0%. Trailing-4Q active-pad averages in 2021 are dominated by the COVID 2020 trough (most pads idle), so baselines are low (1.25–7.75); 2021 active counts (7–23) divided by these produce raw signals of 1.4–7.5, all clipped.

The clip prevents runaway forecasts but the gate cannot distinguish modest from explosive recovery when the baseline collapsed. Agent-3 loses rank-ordering within the cohort: 16 trades at 62.5% hit but only +0.50% mean. We do not modify the clip post-hoc; §13 lists regime-aware sizing as future work. Excluding the 2021 cohort leaves 35 trades at 48.6% / +\$1,840.

## 12.5 External validity

**Regime.** Generalising to future regime breaks is not supported by the historical backtest — the 2021 over-firing pattern is specific to the post-COVID setup. **Crowding.** If the satellite signal becomes commercially available at scale, the edge compresses within 12–36 months per the signal-decay literature.

## 12.6 Documented portfolio rules vs enforced behaviour

The runner manifest records `max_names: 8` as a documented parameter, but the cap is not enforced in the inference layer. In this sample max simultaneous longs is 8 (2021-Q3, all eight then-eligible firms), so the cap never binds and the headline is unaffected. §8 describes it as documented-but-not-binding.
