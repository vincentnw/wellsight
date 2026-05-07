# 12. Limitations and Threats to Validity

## 12.1 SAR change-detection rule

The Sentinel-1 RTC ingestion is real and the per-pad backscatter time series are real radar pixels — but the change-detection rule is intentionally simple: a fixed +1.5 dB / +0.5 dB threshold on quarterly mean VV backscatter, anchored to Ben-David et al. (2021) and Glaeser, Olsen & Welch (2020). The rule has no CV/DL component, no polarimetric decomposition, and no coherent change detection on SLC products. A more sophisticated pipeline — a U-Net or fine-tuned earth-observation foundation model such as NASA-IBM Prithvi — would catch finer signals and emit per-pad probabilities. We treat this as the system's most consequential simplification.

## 12.2 Sample size, IBES proxy, LLM determinism

The full backtest produces 23 long trades across 200 cells (the gate suppresses ~89%). With n = 23 the firm-clustered bootstrap fails to reject H0 = 50% (p = 0.408). The 52.2% point estimate is slightly above coin-flip but does not support a sharp claim of beating it. The moderate sample is a direct consequence of the high-precision-low-recall design.

The IBES consensus uses `ANNDATS_ACT` as a proxy for true pre-T-14 announcement-date provability (WRDS Wall Street Horizon not subscribed). U.S. mid- and large-cap E&P firms pre-announce earnings calendars 30+ days ahead, so the proxy is unbiased in expectation, but subtly look-ahead-biased when announcement dates shift. The related survivorship leak (Anderson & Akbas 2020) is mitigated by the `(REVDATS == ANNDATS) OR (REVDATS > T)` filter.

LLM determinism: all calls run at temperature 0.0 with a per-call cache. OpenAI does not guarantee bit-for-bit determinism, but variance is small for constrained-JSON outputs and the deterministic-numerical-core means trades are insensitive to small qualitative-text changes. The threat is therefore confined to Agent 3's class assignment, which is purely numerical Python.

## 12.3 Universe, architecture, scope

The ten-firm universe is selected on Permian concentration, correlated with mid-/small-cap status. The coverage audit excludes pre-listing quarters, but the universe was selected knowing all ten firms exist as of 2025 — itself a forward-looking selection. CRGY produces zero FracFocus Permian disclosures. The 25-pad sample is bandwidth-limited at ~12 hours wall-clock. The deterministic conviction-to-size lookup preserves traceability at the cost of bounded achievable Sharpe. Strategies 2–10 are 2024-only; extending them to 2019–2024 is the most direct future-work item.

## 12.4 Regime concentration in 2020-Q1

The headline +\$71,833 aggregate is dominated by SM 2020-Q1 (+91.03% / +\$91,029); the 2020-Q1 cohort (SM and OVV) accounts for +\$107,929. Both trades opened in mid-to-late April 2020, immediately after the negative-pricing event of 2020-04-20, and exited two trading days after late-May 2020 earnings, by which point WTI had partially recovered into the \$20s and the equities had rebounded from multi-decade lows. The trades were mechanically valid at T-14 — the Agent-3 gate fired on legitimate `modest_beat` divergence — but the holding window captured a regime-conditional mean-reversion that should not be projected forward.

Excluding SM 2020-Q1 alone leaves 22 trades at 50.0% and −\$19,196; excluding both leaves 21 trades at 47.6% and −\$36,096. The pre-registered WTI stress veto applied as pre-registered removes the two largest gains rather than the largest losses. We do not retune. A single regime-conditional outcome dominates the aggregate, the system has no built-in mechanism to identify when a candidate falls into such a regime, and the simplest pre-registered macro guardrail is misaligned. A more sophisticated portfolio-construction layer would be required to size 2020-Q1-style entries, deferred to future work.

## 12.5 External validity

**Regime.** The 2019–2024 window covers a wide range of oil-price regimes, but the 2020-Q1 cohort dominates aggregate P&L; the headline is regime-concentrated, not a steady-state estimate. **Crowding.** If the satellite-derived signal becomes commercially available at scale, the edge will compress within 12–36 months per the signal-decay literature. The paper reports a snapshot, not a forward-looking prediction.
