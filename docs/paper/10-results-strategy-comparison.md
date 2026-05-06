# 10. Results: Cross-Strategy Comparison

## 10.1 Per-strategy hit-rate ranking — 2024

For the **Q1 2024 – Q4 2024** real-data sub-window, all signals are computed from real data (real EIA WTI, real EIA-DPR rig count, real Sentinel-1 SAR, real IBES consensus, real CRSP+Yahoo prices). Strategies 3–10 are well-known baselines whose pre-earnings hit rate is documented in the empirical asset-pricing literature.

| Rank | Strategy | Hit rate | n_trades |
|---:|---|---:|---:|
| 1 | Strategy 7 — XLE buy-and-hold | 100% | 1 |
| 2 | **Strategy 1 — full multi-agent** | **33.3%** | **12** |
| 3 | Strategy 9 — value composite | 33.3% | 15 |
| 4 | Strategy 6 — equal-weight universe | 32.5% | 40 |
| 5 | Strategy 4 — WTI 3-month momentum | 30.0% | 20 |
| 6 | Strategy 5 — Permian rig count | 30.0% | 10 |
| 7 | Strategy 8 — 12-1 momentum | 28.6% | 14 |
| 8 | Strategy 3 — analyst-revision follower | 27.8% | 18 |
| 9 | Strategy 10 — quality composite | 18.8% | 16 |
| — | Strategy 2 — no-news ablation | not run | — |

**All classical single-signal baselines earned 2024 hit rates between 19% and 33% — well below coin flip**, reflecting 2024's particular regime (rangebound WTI, elevated equity-sector volatility, anti-correlation between pre-earnings drift and several conventional signals). Strategy 7 (XLE) is a single buy-and-hold position. Strategy 1 fired 12 trades in 2024 with a hit rate of 33.3% — tied with Strategy 9 for second place among non-passive strategies, ahead of Strategy 3 by +5.5 percentage points (the H2 comparison in §9.4) — but Strategy 1's 2024 P&L was **-\$26,313**, the system's worst calendar year. Outperforming a poorly-performing baseline on hit rate is not equivalent to making money.

## 10.2 Risk and drawdown

We do not run a Sharpe-difference test against another strategy; small samples make Sharpe noisy. Strategy 1's 2024 drawdown is driven by a string of eight losing entries; the deeper in-universe baseline drawdowns (Strategy 4: −41%; 5: −10%; 6: −62%; 10: −47%) reflect always-long exposure during a rangebound year. Strategy 1's gating step partially reduces drawdown relative to those baselines, but it still fires enough 2024 entries for several losing cells to contribute to drawdown.

## 10.3 Scope of claim

The ranking is descriptive — pre-registered tests are in §§9 and 11. In 2024, every single-signal baseline (including Strategy 1) lost money or barely broke even; Strategy 1 lost less per trade than several baselines but more in aggregate because it fired more trades.
