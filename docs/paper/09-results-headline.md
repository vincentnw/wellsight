# 9. Results: Headline

## 9.1 Aggregate metrics, 2019–2024

Across **Q1 2019 – Q4 2024 (six full calendar years, 200 firm-quarter cells)**, the system produced 51 long entries. All cells use an identical rebalance schedule (T = earnings_date − 14 days, exit second trading day after earnings), 30 bps round-trip cost, and \$1M starting capital. The full per-trade ledger is in Appendix A.

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

The corrected ledger has a diffuse return distribution rather than one dominated by outliers. Largest contributors: SM 2021-Q3 (+\$24,453), OVV 2023-Q2 (+\$15,504), SM 2022-Q3 (+\$12,605), EOG 2022-Q3 (+\$10,605). Largest losses: MTDR 2020-Q3 (−\$21,509), MTDR/OVV 2021-Q2 (−\$13,400 each), EOG 2022-Q4 (−\$10,059). No single trade exceeds 2.5% of capital. Excluding the single best trade leaves 50 trades at -\$17,819; excluding the two best leaves 49 at -\$33,323 — the aggregate is moderately resilient to single-trade exclusion but is not robust beyond that, characteristic of a small-sample result.

The 2020-Q1 cohort contributes a single trade: OVV 2020-Q1 (+16.90% / +\$16,900). SM 2020-Q1 does not fire under the corrected gate (its 2019 trailing baseline of 9.5 active pads places the satellite-anchored forecast 0.5% *below* consensus, classified `in_line`). The "dominant 2020-Q1 trade" framing carried in earlier versions is no longer applicable.

## 9.3 Primary test (H1)

Pre-registered: one-sided 5%-level firm-clustered bootstrap of hit rate against H0 = 50%. Observed hit rate **0.529**; bootstrap **p = 0.328** (exact-binomial cross-check: 0.390); 95% CI **[39.5%, 65.1%]**. The test **fails to reject H0 = 50%**. The firm-clustered 95% CI on mean net return [-1.83%, +1.53%] straddles zero — the data are also consistent with no average edge. The quarter-block bootstrap yields [33.3%, 67.8%], wider as expected. The directional estimate sits modestly above coin-flip but the test does not support a sharp claim of beating it.

## 9.4 Secondary test (H2)

H2 compares Strategy 1 against Strategy 3 (analyst-revision follower). Strategy 3 was run on 2024 only, so the like-for-like comparison restricts Strategy 1 to its 2024 trades (n = 12, **33.3%**, P&L **-\$26,313**). Strategy 3 on 2024 is 27.8% over 18 trades. Pre-registered threshold +3 pp; observed gap +5.5 pp — exceeds the threshold on hit rate. **Caveat**: Strategy 1 exceeds Strategy 3 on hit rate but Strategy 1's 2024 P&L is more negative. H2 is technically supported on the pre-registered metric but does not amount to a positive return claim — both baselines lost money in 2024.
