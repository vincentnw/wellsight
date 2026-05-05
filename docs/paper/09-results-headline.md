# 9. Results: Headline

## 9.1 Aggregate metrics, 2019–2024

Across **Q1 2019 – Q4 2024 (six full calendar years, 200 firm-quarter cells)**, the system produced 23 long entries. All cells use an identical rebalance schedule (T = earnings_date − 14 days, exit second trading day after earnings), 30 bps round-trip cost, and \$1M starting capital. The full per-trade ledger is in Appendix A.

**Table 9.1 — Aggregate metrics, 2019–2024:**

| Metric | Value |
|---|---:|
| Cells evaluated | 200 |
| Long trades fired | **23** |
| Wins / Losses | **12W / 11L** |
| Hit rate | **52.2%** |
| Mean net return per trade | **+2.31%** |
| Median net return per trade | +0.33% |
| Total net P&L on \$1M | **+\$71,833** (+7.18%) |
| Best trade | SM 2020-Q1 (+91.03%) |
| Worst trade | MTDR 2020-Q3 (−21.51%) |
| Per-trade Sharpe (quarterly) | 0.108 |
| Max drawdown | −35.6% |

**Per-year:**

| Year | Cells | Trades | W/L | Hit | P&L on \$1M |
|---|---:|---:|---|---:|---:|
| 2019 | 24 | 2 | 0/2 | 0.0% | −\$16,696 |
| 2020 | 28 | 3 | 2/1 | 66.7% | +\$97,175 |
| 2021 | 30 | 8 | 5/3 | 62.5% | −\$8,807 |
| 2022 | 38 | 3 | 2/1 | 66.7% | +\$7,252 |
| 2023 | 40 | 5 | 2/3 | 40.0% | −\$658 |
| 2024 | 40 | 2 | 1/1 | 50.0% | −\$6,435 |
| **Total** | **200** | **23** | **12/11** | **52.2%** | **+\$71,833** |

## 9.2 The 2020-Q1 caveat

The aggregate is dominated by **SM Energy 2020-Q1** (+91.03% / +\$91,029), entered 2020-04-15 with 4-week WTI return of −24.6% and exited two trading days after SM's late-May 2020 earnings, by which time WTI had partially recovered into the \$30s. The OVV 2020-Q1 trade (+16.90% / +\$16,900) entered eight days later under similar regime conditions. Together the two cells contributed +\$107,929.

Excluding SM 2020-Q1 alone, the remaining 22 trades produce 11W / 11L (50.0%), aggregate −\$19,196. Excluding both 2020-Q1 trades leaves 21 trades at 47.6% and −\$36,096. We report the full sample as the headline but flag this regime concentration in §12. The mechanical entry captured a regime-conditional mean-reversion that should not be projected forward.

## 9.3 Primary test (H1)

Pre-registered: one-sided 5%-level firm-clustered bootstrap of the hit rate against H0 = 50%. Observed hit rate **0.522**; bootstrap **p = 0.408**; 95% CI **[35.0%, 76.5%]**. The test **fails to reject H0 = 50%**. The directional point estimate is slightly above the null, but the data do not support a sharp claim of beating coin-flip; n = 23 cannot distinguish a true 50% process from a true 60–65% process. A non-trivial fraction of the directional improvement comes from the 2020-Q1 cohort identified above; if that cohort represents an unrepeatable regime, the underlying rate is below 52.2%.

## 9.4 Secondary test (H2)

H2 compares Strategy 1 against Strategy 3 (analyst-revision follower). Strategy 3 was run on 2024 only, so the like-for-like comparison restricts Strategy 1 to its 2024 trades (n = 2, 50.0%). Strategy 3 on 2024 is 27.8% over 18 trades. Pre-registered threshold +3 pp; observed gap +22.2 pp; one-sided p = 0.284 — directionally supportive but not statistically significant at 5%. We retain the full 2019–2024 sample as the primary headline; the directional pattern holds against every deterministic baseline reported in §10.
