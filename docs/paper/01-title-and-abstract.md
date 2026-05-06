# Satellite-Anchored Pre-Earnings Trading in Permian E&P:
## A Multi-Agent Framework with a Deterministic Numerical Core

**Vincent N. W.**
**FIN 580 — Spring 2026**

---

## Abstract

We design and test a five-agent system that combines real Sentinel-1 SAR drilling-pad activity, point-in-time IBES analyst consensus, and LLM-driven news verification to produce pre-earnings long trades for ten Permian-basin E&P firms over Q1 2019 – Q4 2024 (200 firm-quarter cells). The system separates a *deterministic numerical core* (consensus, revenue forecast, divergence threshold, conviction-to-size lookup) from an *LLM-driven qualitative shell* (outlook synthesis, news verification, Bull/Bear/Arbiter board). Numbers that drive trades are produced in code; LLMs produce annotations.

All inputs are real public data: Sentinel-1 RTC backscatter, FracFocus completions, EIA WTI and rig count, IBES Detail-History, GDELT, CRSP+Yahoo. The system produced **51 long trades** across 2019–2024: **27W / 24L (52.9%)**, **+0.18% mean net return per trade**, **+0.88% median**, **+\$6,634 on \$1M capital** (+0.66%). Firm-clustered bootstrap fails to reject H0 = 50% (**p = 0.328**, 95% CI **[39.5%, 65.1%]**); 95% CI on mean return **[-1.83%, +1.53%]** straddles zero. Two deterministic ablations produce zero entries: α = 0 and forcing Agent 1 to all-idle.

The aggregate is not driven by a single dominant trade. Top contributors: SM 2021-Q3 (+\$24,453), OVV 2023-Q2 (+\$15,504); worst MTDR 2020-Q3 (−\$21,509). The most consequential structural pattern is **2021 over-firing**: 16 long trades in 2021 (post-COVID drilling recovery), 13 clipped at `drilling_signal = +1.0`, pinning forecast divergence at exactly +10% and triggering `modest_beat`. The clip works as designed but collapses signal differentiation across the recovery cohort: the gate cannot distinguish a modest recovery from an explosive one. We disclose rather than tune post-hoc.

The contribution is methodological: a multi-agent design pattern with clearly separated LLM and deterministic roles, explicit ablations measuring component value, and a reproducibility manifest sufficient to replicate every trade. We do not claim profitability after realistic execution costs — the aggregate (+0.66% over 6 years, +0.18% mean per trade) is within the 30 bps round-trip cost band. We claim that separating deterministic from LLM roles, ablation-validating component contribution, and pre-registering tests is a more defensible foundation for agentic-AI trading than delegating numerical decisions to language models.

**Keywords:** multi-agent LLM, alternative data, satellite imagery, point-in-time consensus, ablation testing.
