# 10. Results: Cross-Strategy Comparison

## 10.1 Per-strategy hit-rate ranking — 2024

For the **Q1 2024 – Q4 2024** real-data sub-window, all signals are computed from real data (EIA WTI, EIA-DPR rig count, Sentinel-1 SAR, IBES consensus, CRSP+Yahoo prices). Strategies 3–10 are baselines whose pre-earnings hit rate is documented in the empirical asset-pricing literature.

| Rank | Strategy | Hit rate | n_trades |
|---:|---|---:|---:|
| 1 | S7 — XLE buy-and-hold | 100% | 1 |
| 2 | **S1 — full multi-agent** | **33.3%** | **12** |
| 3 | S9 — value composite | 33.3% | 15 |
| 4 | S6 — equal-weight universe | 32.5% | 40 |
| 5 | S4 — WTI 3-month momentum | 30.0% | 20 |
| 6 | S5 — Permian rig count | 30.0% | 10 |
| 7 | S8 — 12-1 momentum | 28.6% | 14 |
| 8 | S3 — analyst-revision follower | 27.8% | 18 |
| 9 | S10 — quality composite | 18.8% | 16 |
| — | S2 — no-news ablation | not run | — |

All classical single-signal baselines earned 2024 hit rates between 19% and 33% — well below coin flip — reflecting 2024's regime (rangebound WTI, elevated sector volatility, anti-correlation between pre-earnings drift and several conventional signals). S7 is a single buy-and-hold. S1 fired 12 trades at 33.3% — tied with S9 for second among non-passive strategies, ahead of S3 by +5.5 pp (the H2 comparison in §9.4) — but S1's 2024 P&L was **-\$26,313**, the worst year. Outperforming a poorly-performing baseline on hit rate is not equivalent to making money.

## 10.2 Risk and drawdown

Small samples make Sharpe noisy; we do not run formal Sharpe-difference tests. S1's 2024 drawdown is driven by eight losing entries; in-universe baseline drawdowns are deeper (S4: −41%; S5: −10%; S6: −62%; S10: −47%) due to always-long exposure. S1's gating partially reduces drawdown but still fires enough losers to contribute.

## 10.3 Scope of claim

Descriptive ranking; pre-registered tests are in §§9 and 11. In 2024 every single-signal baseline lost money or barely broke even; S1 lost less per trade than several but more in aggregate because it fired more trades.
