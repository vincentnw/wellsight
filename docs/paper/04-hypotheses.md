# 4. Hypotheses and Research Questions

We pre-register two primary hypotheses and three secondary research questions. The pre-registration is operative: every test below was specified before any P&L was computed, and the headline test (H1) is one-sided at the 5% level.

## 4.1 Primary hypotheses

**H1 (signal-direction).** The Strategy 1 (full multi-agent system) trade-direction hit rate exceeds 50% over the headline window **Q1 2019 – Q4 2024** (six full calendar years, all real-data inputs). Test: firm-clustered bootstrap with 1,000 iterations, null-centered under H0 = 50%; one-sided p-value; reject at p < 0.05. Pre-registered as the project's primary test per Harvey & Liu (2014). The firm-clustering choice is conservative: it accounts for cross-sectional dependence within a single firm's repeated quarterly trades but does not require a parametric assumption about the return distribution. We acknowledge ex ante that the system's high-precision-low-recall design produces ~10 long trades over the six-year window, and the test may have limited statistical power; the sample size is a direct consequence of the deterministic Agent-3 gate and is reported alongside the result.

**H2 (signal-marginal-value).** The Strategy 1 hit rate exceeds the Strategy 3 (analyst-revision follower, our closest pure-consensus baseline) hit rate by at least three percentage points. Test: difference of means with quarter-block bootstrap; one-sided at the 5% level. The three-point threshold reflects the literature's typical pre-arbitrage edge (Mukherjee et al. 2021) and is calibrated to be detectable given the post-filter sample size. We also report the cleaner internal counterfactual under RQ2 (the α=0 consensus-anchor ablation), which more strictly isolates the satellite's marginal contribution by holding the rest of the architecture fixed.

## 4.2 Secondary research questions

**RQ1 (SAR change-detection threshold sensitivity).** With the project's pivot from a synthetic-SAR confusion-matrix sweep to real Sentinel-1 RTC backscatter, the original confusion-matrix sweep no longer applies. The analogous sensitivity is over the change-detection threshold (≥1.5 dB activation / ≥0.5 dB sustained). Sweeping these thresholds is left as future work; for the headline run we anchor the thresholds to the Permian-pad SAR change-detection literature (Ben-David et al. 2021; Glaeser, Olsen & Welch 2020) rather than tuning on any in-sample year of the 2019-2024 data.

**RQ2 (ablation: alpha-equals-zero).** When the consensus-anchor coefficient α is set to zero (so that the revenue forecast equals the IBES consensus exactly and the satellite signal has no influence on the forecast), how does Strategy 1 perform? This isolates the marginal contribution of the satellite signal: an α=0 hit rate close to or exceeding the α=0.10 hit rate would imply that the system's edge comes from somewhere other than the satellite signal, falsifying H2.

**RQ3 (ablation: no-satellite).** When Agent 1 is forced to emit all-idle pad classifications (so that the absolute_active count is zero), how does Strategy 1 perform? RQ3 disables satellite information at the input stage rather than at the weighting stage; it is the cleanest ablation for measuring whether the LLM scaffolding has any signal value independent of the satellite signal.

## 4.3 Out-of-scope claims

We do not claim that the system is a deployable trading product. The six-year window with ~10 long trades is small for any robust statistical claim, the IBES consensus reconstruction uses ANNDATS_ACT as a pre-T-14 announcement-date proxy (because the team's WRDS subscription does not include Wall Street Horizon), and the holding-period assumption (entry T-14, exit on the second trading day after earnings) is conservative — real execution would face overnight gap risk and microstructure costs above the 30-bps round-trip we charge. The paper's claim is methodological and educational: that a multi-agent system with a deterministic numerical core can ingest real Sentinel-1 SAR end-to-end across six calendar years (including a regime break in 2020 that the system correctly avoided), run the multi-agent pipeline, and produce conservative, gated trade decisions whose marginal contribution from each component is measurable via mechanical ablations.

## 4.4 What would falsify the paper

Three results would falsify the central thesis. (i) H1 fails — the Strategy 1 hit rate does not statistically exceed 50% — implying that the system is no better than coin-flipping. (ii) H2 fails — Strategy 1 hit rate is no higher than Strategy 3 (analyst-revision follower) by the pre-registered threshold. (iii) RQ2/RQ3 ablations show that α=0 or no-satellite produces a hit rate at least as high as the full-system rate — implying that the satellite signal is not the source of edge. We pre-register these falsification criteria and report results against them in Sections 9–11 regardless of outcome.
