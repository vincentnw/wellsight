# 10. Results: Cross-Strategy Comparison

## 10.1 Per-strategy hit-rate ranking — 2024

For the **Q1 2024 – Q4 2024** real-data sub-window, all signals are computed from real data (real EIA WTI, real EIA-DPR rig count, real Sentinel-1 SAR, real IBES consensus, real CRSP+Yahoo prices). Strategies 3–10 are well-known baselines whose pre-earnings hit rate is documented in the empirical asset-pricing literature.

| Rank | Strategy | Hit rate | n_trades |
|---:|---|---:|---:|
| 1 | Strategy 7 — XLE buy-and-hold | 100% | 1 |
| 2 | **Strategy 1 — full multi-agent** | **50.0%** | **2** |
| 3 | Strategy 2 — no-news ablation | not run | — |
| 4 | Strategy 9 — value composite | 33.3% | 15 |
| 5 | Strategy 6 — equal-weight universe | 32.5% | 40 |
| 6 | Strategy 4 — WTI 3-month momentum | 30.0% | 20 |
| 7 | Strategy 5 — Permian rig count | 30.0% | 10 |
| 8 | Strategy 8 — 12-1 momentum | 28.6% | 14 |
| 9 | Strategy 3 — analyst-revision follower | 27.8% | 18 |
| 10 | Strategy 10 — quality composite | 18.8% | 16 |

**All classical single-signal baselines earned 2024 hit rates between 19% and 33% — well below coin flip**, reflecting 2024's particular regime (rangebound WTI, elevated equity-sector volatility, anti-correlation between pre-earnings drift and several conventional signals). Strategy 7 (XLE) is a single buy-and-hold position. Strategy 1's 2024 slice is too small (2 trades) for a standalone statistical claim, but its 50.0% is directionally stronger than the deterministic baselines' ~28% average.

## 10.2 Risk and drawdown

We do not run a Sharpe-difference test against another strategy; the small sample makes Sharpe noisy. The ranking is descriptive. Strategy 1's 2024 drawdown is driven by FANG Q2 (−6.80%); the in-universe baselines take much deeper drawdowns (Strategy 4: −41%; 5: −10%; 6: −62%; 10: −47%). The pattern is mechanical: in-universe baselines are structurally always-long-something while Strategy 1 holds cash whenever Agent 3 short-circuits. The drawdown protection is therefore a consequence of the gating step rather than a stochastic property — though at n = 2 the comparison is more defensive than offensive.

## 10.3 Scope of claim

This section is descriptive. It does not formally test Strategy 1 against any of the other nine on Sharpe, mean return, or per-firm hit rate; multi-comparison correction would dominate the small-sample power. Pre-registered tests are reported in §§9 and 11 only. The ranking is expository — for a reader locating the multi-agent result against the spectrum of conventional baselines.
