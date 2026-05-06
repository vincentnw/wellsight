# 13. Conclusion

We documented a multi-agent trading system for Permian E&P in which satellite-derived drilling activity feeds a deterministic revenue forecast assessed by an LLM investment board. Financial logic runs in code; qualitative outlook synthesis, news verification, and Bull/Bear/Arbiter debate run in language models.

This decomposition addresses the principal failure mode of agentic-AI trading: delegating unverifiable numerical decisions to language models, evaluated ex-post by P&L rather than ex-ante calibration. Our system avoids it by construction — every long trade traces to explicit numerical inputs; each LLM agent's marginal contribution is measurable by ablation. The α = 0 and no-satellite ablations both produce zero long trades.

Empirical results on the real-data 2019–2024 window: **51 long trades**, 27W / 24L (52.9%), +0.18% mean net return per trade, median +0.88%, total **+\$6,634 on \$1M** (+0.66% of capital). Firm-clustered bootstrap fails to reject H0 = 50% (p = 0.328, 95% CI on hit rate [39.5%, 65.1%]); 95% CI on mean return [-1.83%, +1.53%] straddles zero. No single trade dominates; largest contributor is SM 2021-Q3 (+\$24,453). The pre-registered WTI stress veto blocks one trade (OVV 2020-Q1, +\$16,900) and shifts the aggregate to -\$10,266 — a single-threshold macro guardrail removes a gain, not a loss, in this window.

The most consequential structural finding is **2021 over-firing** (§12.4): 16 long trades in 2021, 13 clipped at `drilling_signal = +1.0` with identical +10.0% divergence. The clip works as designed but collapses signal differentiation across the recovery cohort. We disclose rather than tune.

We do not claim profitability after realistic execution costs (the +0.18% mean is within the 30-bps round-trip band), statistical sufficiency at n = 51, optimality of the SAR rule, or that the IBES `ANNDATS_ACT` proxy is fully look-ahead-clean. The contribution is methodological — a multi-agent design pattern with deterministic core, end-to-end real-data ingestion, and ablation-validated component contribution — portable to other alt-data-meets-fundamentals settings.

Four future-work avenues: (1) upgrade SAR change detection to a CV/DL pipeline; (2) regime-aware sizing/gating that conditions on trailing-baseline magnitude, restoring rank-ordering in recovery cohorts; (3) extend Strategies 2–10 to the full 2019–2024 window; (4) implement the documented 8-name concurrency cap or drop it.

The result is statistically modest: the system produces a directionally-positive signal whose marginal contribution is mechanically measurable, but the aggregate is small and not significant against the coin-flip null. The contribution is a discipline of separating deterministic from LLM roles, pre-registering tests, and running ablations that could falsify the central thesis — most important when an LLM is in the pipeline and when the result is unflattering.
