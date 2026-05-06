# 9. Results: Headline

## 9.1 Aggregate metrics, 2019–2024

Across **Q1 2019 – Q4 2024 (200 cells)**, the system produced 51 long entries. Rebalance T = earnings_date − 14 (exit T+2 trading days), 30 bps round-trip, \$1M capital. Full ledger in Appendix A.

**Table 9.1 — Aggregate metrics, 2019–2024:**

| Metric | Value |
|---|---:|
| Cells evaluated | 200 |
| Long trades fired | **51** |
| Wins / Losses | **27W / 24L** |
| Hit rate | **52.9%** |
| Mean net return per trade | **+0.18%** |
| Median net return per trade | +0.88% |
| Total net P&L on \$1M | **+\$6,634** (+0.66%) |
| Best trade | SM 2021-Q3 (+24.45% / +\$24,453) |
| Worst trade | MTDR 2020-Q3 (−21.51% / −\$21,509) |
| Per-trade Sharpe (quarterly) | 0.021 |
| Max drawdown | −47.06% |

**Per-year:**

| Year | Cells | Trades | W/L | Hit | P&L on \$1M |
|---|---:|---:|---|---:|---:|
| 2019 | 24 | 2 | 2/0 | 100.0% | +\$5,846 |
| 2020 | 28 | 3 | 2/1 | 66.7% | -\$464 |
| 2021 | 30 | 16 | 10/6 | 62.5% | +\$4,794 |
| 2022 | 38 | 9 | 5/4 | 55.6% | +\$10,210 |
| 2023 | 40 | 9 | 4/5 | 44.4% | +\$12,562 |
| 2024 | 40 | 12 | 4/8 | 33.3% | -\$26,313 |
| **Total** | **200** | **51** | **27/24** | **52.9%** | **+\$6,634** |

## 9.2 Distribution of returns

The distribution is diffuse rather than outlier-dominated. Top gains: SM 2021-Q3 (+\$24,453), OVV 2023-Q2 (+\$15,504), SM 2022-Q3 (+\$12,605), EOG 2022-Q3 (+\$10,605). Top losses: MTDR 2020-Q3 (−\$21,509), MTDR/OVV 2021-Q2 (−\$13,400 each), EOG 2022-Q4 (−\$10,059). No single trade exceeds 2.5% of capital. Excluding the single best leaves 50 trades at -\$17,819; the two best, 49 at -\$33,323 — moderately resilient to single-trade exclusion but not beyond, typical of a small-sample result. The 2020-Q1 cohort contributes one trade (OVV 2020-Q1, +\$16,900); SM 2020-Q1 does not fire (2019 trailing baseline of 9.5 active pads puts the forecast 0.5% *below* consensus, `in_line`).

## 9.3 Primary test (H1)

Pre-registered one-sided 5%-level firm-clustered bootstrap vs H0 = 50%. Observed **0.529**; **p = 0.328** (exact-binomial 0.390); 95% CI **[39.5%, 65.1%]**. **Fails to reject H0.** 95% CI on mean return [-1.83%, +1.53%] straddles zero. Quarter-block bootstrap yields [33.3%, 67.8%]. Directional estimate sits modestly above coin-flip but does not support a sharp claim of beating it.

## 9.4 Secondary test (H2)

H2 vs Strategy 3 (analyst-revision follower) was run on 2024 only; restricting S1 to 2024 trades (n = 12, 33.3%, **-\$26,313**) vs S3 (27.8% over 18 trades) — observed gap +5.5 pp exceeds the pre-registered +3 pp threshold on hit rate. Caveat: S1 exceeds S3 on hit rate but its 2024 P&L is more negative; H2 is technically supported on the metric but is not a positive-return claim — both lost money in 2024.
