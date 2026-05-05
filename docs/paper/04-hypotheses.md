# 4. Hypotheses and Research Questions

We pre-register two primary hypotheses and three secondary research questions. Every test below was specified before any P&L was computed; the headline test is one-sided at the 5% level.

## 4.1 Primary hypotheses

**H1 (signal-direction).** Strategy 1's hit rate exceeds 50% over Q1 2019 – Q4 2024. Test: firm-clustered bootstrap with 1,000 iterations, null-centered under H0 = 50%, one-sided, reject at p < 0.05 (Harvey & Liu 2014). Firm-clustering accommodates within-firm dependence across repeated quarterly trades without parametric assumptions on the return distribution. The system's high-precision-low-recall design produces ~3.8 long trades per year, so n is small and statistical power is limited.

**H2 (signal-marginal-value).** Strategy 1's hit rate exceeds Strategy 3's (analyst-revision follower) by at least three percentage points. Test: difference of means with quarter-block bootstrap, one-sided at 5%. The 3-pp threshold matches the typical pre-arbitrage edge in Mukherjee et al. (2021). RQ2 (the α = 0 ablation) provides a cleaner internal counterfactual.

## 4.2 Secondary research questions

**RQ1 (SAR threshold sensitivity).** Sweep the change-detection thresholds. Deferred; thresholds are anchored ex ante to Ben-David et al. (2021) and Glaeser, Olsen & Welch (2020), not tuned in-sample.

**RQ2 (α = 0 ablation).** When α is set to zero, Agent 2's forecast equals consensus and the satellite signal cannot influence the divergence class. RQ2 isolates the satellite's marginal contribution: an α = 0 hit rate close to the α = 0.10 rate would imply the edge comes from elsewhere.

**RQ3 (no-satellite ablation).** Force Agent 1 to emit all-idle classifications. RQ3 disables satellite information at the input rather than the weighting stage; it is the cleanest test of whether the LLM scaffolding has signal independent of the satellite input.

## 4.3 Out-of-scope claims

We do not claim a deployable trading product. The 23-trade sample is small; the IBES `ANNDATS_ACT` proxy is documented; the holding-period assumption (T-14 entry, T+2 exit) ignores overnight gap risk and microstructure costs above 30 bps. The paper's claim is methodological: a multi-agent system with a deterministic numerical core can ingest real Sentinel-1 SAR end-to-end across six calendar years and produce gated trade decisions whose component contributions are measurable via mechanical ablations.

## 4.4 What would falsify the paper

Three results would falsify the central thesis. (i) H1 fails — Strategy 1's hit rate does not exceed 50%. (ii) H2 fails — Strategy 1 does not exceed Strategy 3 by the pre-registered 3-pp threshold. (iii) RQ2 / RQ3 produce a hit rate at least as high as the full-system rate, implying the satellite signal is not the source of edge. We pre-register these criteria and report against them in §§9–11 regardless of outcome.
