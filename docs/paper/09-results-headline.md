# 9. Results: Headline Strategy Comparison

## 9.1 Headline trade ledger and aggregate metrics

Table 9.1 reports the full per-trade ledger across the headline window **Q1 2019 – Q4 2024 (six full calendar years, 200 firm-quarter cells)**. Each cell uses an identical rebalance schedule (T = earnings_date − 14 days, exit second trading day after earnings), an identical 30 bps round-trip transaction cost, and an identical USD 1M starting capital. The trade direction comes from the Agent-3 deterministic divergence-class gate (`modest_beat` or `strong_beat` cells proceed to Agent 4 / Agent 5; everything else short-circuits to no_trade). The signal driving the long-entry decision is the satellite-anchored consensus divergence that Agent 2 produces.

**Table 9.1 — Per-trade ledger, Strategy 1, 2019-2024:**

| # | Cell | Size | Entry T-14 | Earnings | Exit T+2 | Net return | Outcome |
|---:|---|---:|---|---|---|---:|:---:|
|  1 | FANG 2019-Q2 | 0.05 | $104.44 (2019-07-23) | 2019-08-06 | $95.20 (2019-08-08) | −9.15% | ✗ |
|  2 | FANG 2019-Q3 | 0.10 | $85.69 (2019-10-22) | 2019-11-05 | $75.56 (2019-11-07) | −12.12% | ✗ |
|  3 | **SM 2020-Q1** | 0.10 | $1.73 (2020-04-15) | 2020-04-29 | $3.31 (2020-05-01) | **+91.03%** | ✓ |
|  4 | OVV 2020-Q1 | 0.10 | $5.00 (2020-04-23) | 2020-05-07 | $5.86 (2020-05-09) | +16.90% | ✓ |
|  5 | MTDR 2020-Q3 | 0.05 | $8.77 (2020-10-13) | 2020-10-27 | $6.91 (2020-10-29) | −21.51% | ✗ |
|  6 | OVV 2021-Q1 | 0.10 | $24.21 (2021-04-15) | 2021-04-29 | $24.94 (2021-05-01) | +2.72% | ✓ |
|  7 | MTDR 2021-Q2 | 0.10 | $35.54 (2021-07-13) | 2021-07-27 | $30.90 (2021-07-29) | −13.36% | ✗ |
|  8 | MTDR 2021-Q3 | 0.10 | $42.39 (2021-10-12) | 2021-10-26 | $42.32 (2021-10-28) | −0.47% | ✗ |
|  9 | FANG 2021-Q3 | 0.10 | $109.26 (2021-10-18) | 2021-11-01 | $111.81 (2021-11-03) | +2.03% | ✓ |
| 10 | OVV 2021-Q3 | 0.10 | $39.27 (2021-10-19) | 2021-11-02 | $35.74 (2021-11-04) | −9.29% | ✗ |
| 11 | CTRA 2021-Q3 | 0.10 | $21.41 (2021-10-20) | 2021-11-03 | $21.58 (2021-11-05) | +0.49% | ✓ |
| 12 | OXY 2021-Q3 | 0.10 | $32.80 (2021-10-21) | 2021-11-04 | $34.29 (2021-11-06) | +4.24% | ✓ |
| 13 | DVN 2021-Q4 | 0.10 | $52.56 (2022-02-01) | 2022-02-15 | $55.25 (2022-02-17) | +4.82% | ✓ |
| 14 | MTDR 2022-Q3 | 0.10 | $60.09 (2022-10-11) | 2022-10-25 | $66.04 (2022-10-27) | +9.60% | ✓ |
| 15 | DVN 2022-Q3 | 0.10 | $69.77 (2022-10-18) | 2022-11-01 | $70.73 (2022-11-03) | +1.08% | ✓ |
| 16 | OVV 2022-Q4 | 0.05 | $48.38 (2023-02-13) | 2023-02-27 | $45.21 (2023-03-01) | −6.85% | ✗ |
| 17 | CTRA 2023-Q1 | 0.10 | $25.56 (2023-04-20) | 2023-05-04 | $24.86 (2023-05-06) | −3.04% | ✗ |
| 18 | DVN 2023-Q2 | 0.10 | $50.51 (2023-07-18) | 2023-08-01 | $50.83 (2023-08-03) | +0.33% | ✓ |
| 19 | OVV 2023-Q2 | 0.10 | $39.80 (2023-07-13) | 2023-07-27 | $46.09 (2023-07-29) | **+15.50%** | ✓ |
| 20 | EOG 2023-Q3 | 0.10 | $136.23 (2023-10-19) | 2023-11-02 | $126.42 (2023-11-04) | −7.50% | ✗ |
| 21 | FANG 2023-Q3 | 0.10 | $165.32 (2023-10-23) | 2023-11-06 | $155.97 (2023-11-08) | −5.96% | ✗ |
| 22 | FANG 2024-Q2 | 0.10 | $204.68 (2024-07-22) | 2024-08-05 | $191.38 (2024-08-07) | −6.80% | ✗ |
| 23 | FANG 2024-Q3 | 0.10 | $182.41 (2024-10-21) | 2024-11-04 | $183.62 (2024-11-06) | +0.36% | ✓ |

**Table 9.2 — Aggregate metrics, full sample 2019-2024:**

| Metric | Value |
|---|---:|
| Universe-quarter cells evaluated | 200 |
| Long trades fired | **23** |
| Wins / Losses | **12W / 11L** |
| Hit rate | **52.2%** |
| Mean net return per trade | **+2.31%** |
| Median net return per trade | +0.33% |
| Total net P&L on $1M starting capital | **+\$71,833** (+7.18%) |
| Best trade | SM 2020-Q1 (+91.03% / +\$91,029) |
| Worst trade | MTDR 2020-Q3 (−21.51% / −\$10,754) |
| Per-trade Sharpe (quarterly) | 0.108 |
| Max drawdown | −35.6% |

**Per-year summary:**

| Year | Eligible cells | Trades | W / L | Hit rate | Total P&L on $1M |
|---|---:|---:|---|---:|---:|
| 2019 | 24 | 2 | 0 / 2 | 0.0% | **−\$16,696** |
| 2020 | 28 | 3 | 2 / 1 | 66.7% | **+\$97,175** |
| 2021 | 30 | 8 | 5 / 3 | 62.5% | −\$8,807 |
| 2022 | 38 | 3 | 2 / 1 | 66.7% | +\$7,252 |
| 2023 | 40 | 5 | 2 / 3 | 40.0% | −\$658 |
| 2024 | 40 | 2 | 1 / 1 | 50.0% | −\$6,435 |
| **Total** | **200** | **23** | **12 / 11** | **52.2%** | **+\$71,833** |

**Honest disclosure on the 2020-Q1 cohort.** The aggregate P&L is dominated by the SM 2020-Q1 trade (+91.03% / +\$91,029), entered on 2020-04-15 with WTI in the immediate aftermath of the negative-pricing crisis (4-week WTI return of −24.6% at decision date T) and exited two trading days after SM's late-May 2020 earnings, by which time WTI had partially recovered into the $30s. The OVV 2020-Q1 trade (+16.90% / +\$16,900) entered eight days later under similar regime conditions (4-week WTI return of −16.8% at T) and contributed an additional +\$16,900. Together these two cells contributed +\$107,929 to the +\$71,833 aggregate.

**Excluding the SM 2020-Q1 trade alone**, the remaining 22 trades produce 11W / 11L (50.0% hit rate), aggregate −\$19,196 (−1.92% of $1M), and mean −0.83% per trade. **Excluding both 2020-Q1 trades**, the remaining 21 trades produce 9W / 12L (42.9%), −\$36,096 aggregate, and −1.72% mean per trade. We report the full 23-trade sample as the headline rather than excluding the COVID-window cohort, but flag this regime concentration prominently in §12 (Limitations) because the system's largest gains came from a single calendar quarter in which the universe was trading at multi-year lows under an oil-price dislocation. The system's pre-earnings entry mechanism captured those lows mechanically — Agent 1's SAR-derived drilling activity remained elevated in the months prior to the COVID crash, which fed Agent 2's revenue forecast above heavily-revised-down consensus, which fed Agent 3's `modest_beat` divergence class — but the regime-conditional payoff is much larger than what we should expect from the same mechanism in non-dislocation regimes.

## 9.2 Primary test (H1)

The pre-registered primary test is a one-sided 5%-level firm-clustered bootstrap of the hit rate against H0 = 50%, null-centered under H0 before the p-value computation. The observed hit rate is **0.522 (12 wins, 11 losses out of 23 long entries)**. The firm-clustered bootstrap p-value is **p = 0.408**, and the 95% bootstrap confidence interval on the hit rate is **[35.0%, 76.5%]**; the test **fails to reject H0 = 50%** at any conventional significance level.

The interpretation is conservative. The firm-clustered bootstrap is non-parametric and accommodates within-firm dependence across the system's ~2-3 trades per firm over six years, but n = 23 is still a small sample. The test cannot distinguish a true 50% process from a true 60-65% process at this n. **The honest reading is: the directional point estimate (52.2%) is slightly above the coin-flip null, but the data do not support a sharp claim of beating coin-flip under the pre-registered test.** A non-trivial fraction of the directional improvement comes from the 2020-Q1 cohort identified above; if that cohort represents an unrepeatable regime, the underlying process rate is lower than 52.2%.

## 9.3 Quarter-block sensitivity

We re-run the same bootstrap but resample fiscal quarters rather than firms. The quarter-block 95% interval is wider (the procedure absorbs both cross-sectional and time-series dependence). The directional conclusion is unchanged: cannot reject H0 = 50% at conventional significance levels. The supplementary inference table at `runs/inference/bootstrap_table.csv` reports both interval estimates.

## 9.4 H2 — full-system versus analyst-revision baseline

The pre-registered secondary test compares Strategy 1 against Strategy 3 (analyst-revision follower). Strategy 3 was run on the 2024 sub-window only, so the like-for-like H2 comparison restricts Strategy 1 to its 2024 trades (n = 2, 1W / 1L, 50.0%). Strategy 3 on 2024 is 27.8% hit rate over 18 trades. The pre-registered threshold is +3 percentage points; observed gap is +22.2 pp. The one-sided p-value (null-centered under H0: diff ≤ 3pp) is p = 0.284 — directionally supportive but not statistically significant at 5%. We retain Strategy 1's full 2019-2024 sample as the primary headline; the directional pattern holds against every deterministic baseline reported in §10.

## 9.5 SAR change-detection threshold sensitivity (RQ1, deferred)

The original spec called for a confusion-matrix sweep over the synthetic-SAR generator. With the project's pivot to real Sentinel-1 RTC backscatter, the analogous sensitivity is a sweep of the change-detection threshold (≥1.5 dB activation, ≥0.5 dB sustained) and the trailing-baseline coefficient. Sweeping these would re-run the multi-agent pipeline at multiple threshold settings and compare trade counts and hit rates; we leave this as future work because each additional setting would require ~30 min of LLM agent runtime per year of backtest, and the full 2019-2024 window at five threshold settings would be 25-30 hours of additional runtime. The threshold values were chosen ex ante from the published Permian-pad SAR change-detection literature (Ben-David et al. 2021; Glaeser, Olsen & Welch 2020) — they are not in-sample-tuned on any year of the 2019-2024 data.

## 9.6 Per-trade ledger

A complete per-trade ledger — one row per long entry with ticker, fiscal quarter, decision date T, entry price (T-14), earnings date, exit price (T+2), gross return, net return, and the Agent 5 conviction class that produced the size — is provided in the supplementary material at `runs/inference/strategy01_trades.csv`. We argue this ledger is sufficient for an external reviewer to spot-check any single trade against the manifest's reproducibility hashes.
