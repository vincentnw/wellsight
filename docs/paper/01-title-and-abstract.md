# Satellite-Anchored Pre-Earnings Trading in Permian E&P:
## A Multi-Agent Framework with a Deterministic Numerical Core

**Vincent N. W.**
**FIN 580 — Spring 2026**
**Version: 2026-05-05**

---

## Abstract

We design and test a five-agent system that combines real Sentinel-1 SAR drilling-pad activity, point-in-time IBES analyst consensus, and LLM-driven news verification to produce pre-earnings long trades for ten Permian-basin E&P firms over Q1 2019 – Q4 2024 (200 firm-quarter cells). The system separates a *deterministic numerical core* (consensus, revenue forecast, divergence threshold, conviction-to-size lookup) from an *LLM-driven qualitative shell* (outlook synthesis, news verification, Bull/Bear/Arbiter board). Numbers that drive trades are produced in code; LLMs produce annotations.

All inputs are real public data: Sentinel-1 RTC backscatter, FracFocus completions, EIA WTI and rig count, IBES Detail-History, GDELT articles, and CRSP+Yahoo prices. The system produced **23 long trades**: **12W / 11L (52.2%)**, **+2.31% mean net return per trade**, total **+\$71,833 on \$1M capital**. The firm-clustered bootstrap fails to reject H0 = 50% (**p = 0.408**, 95% CI **[35.0%, 76.5%]**). Two deterministic ablations produce zero entries: setting α = 0 and forcing Agent 1 to all-idle classifications.

The headline aggregate is dominated by a single 2020-Q1 trade in SM Energy (+91.03% / +\$91,029), entered 2020-04-15 with 4-week WTI return at −24.6% and exited two trading days after late-May 2020 earnings — a regime-conditional outcome we flag prominently. Excluding the SM 2020-Q1 trade alone leaves 22 trades at 11W / 11L (50.0%) and aggregate −\$19,196.

The contribution is methodological: a multi-agent design pattern in which LLM and deterministic components occupy separated roles, with explicit ablations measuring component value and a reproducibility manifest sufficient to replicate every trade. We do not claim profitability after realistic execution costs; we claim that separating deterministic from LLM roles, ablation-validating component contribution, and pre-registering tests is a more defensible foundation for agentic-AI trading than delegating numerical decisions to language models.

**Keywords:** multi-agent LLM systems, alternative data, satellite imagery, point-in-time consensus, ablation testing.
