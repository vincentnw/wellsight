# 10. Results: Cross-Strategy Comparison

## 10.1 Per-strategy hit-rate ranking — 2024 (real-data window)

Across the ten strategies, hit rates are ordered as follows for the **Q1 2024 – Q4 2024 real-data window**, with all signals computed from real underlying data (real EIA WTI, real EIA-DPR Permian rig count, real Sentinel-1 SAR backscatter, real IBES revenue consensus, real CRSP+Yahoo prices). The ordering matters because Strategies 3–6, 8–10 are well-known baselines whose hit rate around earnings is documented in the empirical asset-pricing literature; the table also shows that 2024 was a difficult year for short-horizon classical-signal strategies.

| Rank | Strategy | Hit rate | n_trades | Notes |
|---:|---|---:|---:|---|
| 1 | Strategy 7 — XLE buy-and-hold | 100% | 1 | Single buy-hold position; XLE +6.3% net in 2024 |
| 2 | **Strategy 1 — full multi-agent (real Sentinel-1 SAR)** | **50.0%** | **2** | 2024 slice of the headline ledger (FANG Q2 −6.80%, FANG Q3 +0.36%); see §9 |
| 3 | Strategy 2 — no-news ablation | not run for 2024 | — | A 2024 Strategy-2 backtest is left for future work |
| 4 | Strategy 9 — value composite | 33.3% | 15 | EV/EBITDA + P/B + FCF yield |
| 5 | Strategy 6 — equal-weight universe | 32.5% | 40 | Passive in-universe rebalance |
| 6 | Strategy 4 — WTI 3-month momentum (real EIA WTI) | 30.0% | 20 | Macro-momentum baseline |
| 7 | Strategy 5 — Permian rig count (real EIA-DPR) | 30.0% | 10 | Drilling-cycle signal |
| 8 | Strategy 8 — 12-1 momentum | 28.6% | 14 | Cross-sectional momentum |
| 9 | Strategy 3 — analyst-revision follower | 27.8% | 18 | Pure consensus-tracking baseline |
| 10 | Strategy 10 — quality composite | 18.8% | 16 | ROE / debt-to-equity / OCF margin |

The headline observation for 2024 is that **all classical single-signal baselines we tested earned hit rates between 19% and 33% — well below coin flip.** This reflects 2024's particular regime: WTI was rangebound around $70-85 with no strong trend, equity-sector volatility was elevated, and pre-earnings drift was anti-correlated with several conventional signals. Strategy 7 (XLE buy-and-hold) is a pure long-WTI exposure that captured the year's small positive sector return. Strategy 1's 2024 slice is small (two trades) and therefore not a standalone statistical result, but its 50.0% hit rate is still directionally stronger than the deterministic baselines' roughly 28% average hit rate in the same calendar year.

## 10.2 Risk-adjusted ordering

The Sharpe ratio is reported per strategy in §9.1; the small sample size (Strategy 1: 2 trades; deterministic baselines: 10–40 trades over the 2024 window) makes Sharpe a noisy statistic, and we explicitly do not run a Sharpe-difference test against another strategy. The ranking we report is descriptive: at n=2 Strategy 1's 2024 Sharpe is essentially uninformative, while every deterministic baseline reports a negative quarterly Sharpe in 2024.

## 10.3 Drawdown profile

Strategy 1's 2024 drawdown is driven by the FANG Q2 loss (−6.80%), with the later FANG Q3 gain (+0.36%) only partially offsetting it. By contrast, Strategies 3–10 take much deeper drawdowns in 2024 (Strategies 4 and 5 hit −41% and −10%; Strategy 6 (equal-weight) bottoms at −62%; Strategy 10 at −47%). The systematic pattern is that the in-universe baselines are structurally always-long-something, while Strategy 1 holds cash whenever Agent 3 short-circuits. This drawdown protection is mechanical, not stochastic: it is a consequence of the gating step that converts "no clear beat" into "no trade", and is one of the more important structural features of the multi-agent design — though we note that this protection is partly a consequence of the small Strategy-1 sample (2 trades vs 10-40 for baselines), so the drawdown comparison is more defensive than offensive at this sample size.

## 10.4 Per-trade detail

With only two long entries in 2024, per-firm and per-quarter heatmaps are degenerate — Strategy 1 fires twice on FANG (2024-Q2 and 2024-Q3). Both trades were backed by the same upstream condition: real Sentinel-1 SAR over 25 representative pads produced enough activity uplift for Agent 2's consensus-anchored revenue forecast to cross the `modest_beat` threshold. The 2024 slice is therefore best read as an annual checkpoint within the full 2019-2024 ledger, not as an independent proof of the system's performance.

## 10.5 What this section does and does not claim

This section is a descriptive cross-strategy comparison. It does not formally test Strategy 1 against any of the other nine strategies on Sharpe, mean-return, or per-firm-hit-rate; the multi-comparison correction would dominate the small-sample power. The pre-registered tests (H1, H2, RQ1, RQ2, RQ3) are reported in Sections 9 and 11 only. The ranking in this section is expository — for a reader who wants to locate the multi-agent result against the spectrum of conventional baselines.
