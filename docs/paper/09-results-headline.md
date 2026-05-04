# 9. Results: Headline Strategy Comparison

## 9.1 Headline trade ledger and aggregate metrics

Table 9.1 reports the full per-trade ledger across the headline window **Q1 2019 – Q4 2024 (six full calendar years, 200 firm-quarter cells)**. Each cell uses an identical rebalance schedule (T = earnings_date − 14 days, exit second trading day after earnings), an identical 30 bps round-trip transaction cost, and an identical USD 1M starting capital. The trade direction comes from the Agent-3 deterministic divergence-class gate (`modest_beat` or `strong_beat` cells proceed to Agent 4 / Agent 5; everything else short-circuits to no_trade). The signal driving the long-entry decision is the satellite-anchored consensus divergence that Agent 2 produces.

**Table 9.1 — Per-trade ledger, Strategy 1 (Multi-agent + real Sentinel-1 SAR), 2019-2024:**

| # | Cell | Entry T-14 | Earnings | Exit T+2 | Net return | Outcome |
|---:|---|---|---|---|---:|:---:|
| 1 | OXY 2019-Q4 | $42.04 (2020-02-13) | 2020-02-27 | $32.95 (2020-02-29) | **−21.92%** | ✗ |
| 2 | SM 2019-Q4 | $9.67 (2020-02-05) | 2020-02-19 | $8.53 (2020-02-21) | **−12.09%** | ✗ |
| 3 | OVV 2021-Q1 | $24.21 (2021-04-15) | 2021-04-29 | $24.94 (2021-05-01) | +2.72% | ✓ |
| 4 | CTRA 2021-Q3 | $21.41 (2021-10-20) | 2021-11-03 | $21.58 (2021-11-05) | +0.49% | ✓ |
| 5 | OXY 2021-Q3 | $32.80 (2021-10-21) | 2021-11-04 | $34.29 (2021-11-06) | +4.24% | ✓ |
| 6 | OVV 2021-Q3 | $39.27 (2021-10-19) | 2021-11-02 | $35.74 (2021-11-04) | −9.29% | ✗ |
| 7 | CTRA 2022-Q3 | (CRSP) | 2022-11-03 | (CRSP) | −0.91% | ✗ |
| 8 | OVV 2023-Q2 | (CRSP) | 2023-07-27 | (CRSP) | **+15.50%** | ✓ |
| 9 | FANG 2024-Q2 | $204.68 (2024-07-22) | 2024-08-05 | $191.38 (2024-08-07) | −6.80% | ✗ |
| 10 | PR 2024-Q3 | $13.85 (2024-10-23) | 2024-11-06 | $14.92 (2024-11-08) | +7.43% | ✓ |

**Table 9.2 — Aggregate metrics, full sample 2019-2024:**

| Metric | Value |
|---|---:|
| Universe-quarter cells evaluated | 200 |
| Long trades fired | **10** |
| Wins / Losses | **5W / 5L** |
| Hit rate | **50.0%** |
| Mean net return per trade | **−2.06%** |
| Median net return per trade | +0.49% |
| Total net P&L on $1M starting capital | **−\$20,623** (−2.06%) |
| Best trade | OVV 2023-Q2 (+15.50%) |
| Worst trade | OXY 2019-Q4 (−21.92%) |

**Per-year summary:**

| Year | Cells | Trades | W / L | Hit rate | Total P&L on $1M |
|---|---:|---:|---|---:|---:|
| 2019 | 24 | 2 | 0 / 2 | 0.0% | **−\$34,011** |
| 2020 | 28 | **0** | — | — | $0 (system mechanically held flat through COVID collapse) |
| 2021 | 30 | 4 | 3 / 1 | 75.0% | −\$1,837 |
| 2022-2023 | 78 | 2 | 1 / 1 | 50.0% | **+\$14,598** |
| 2024 | 40 | 2 | 1 / 1 | 50.0% | +\$628 |
| **Total** | **200** | **10** | **5 / 5** | **50.0%** | **−\$20,623** |

The aggregate result is a 50.0% hit rate at −2.06% mean net return per trade. The dominant loss driver is the 2019-Q4 cohort: both 2019-Q4 trades (OXY and SM) opened in early-mid February 2020 and exited 2 trading days after their February-2020 earnings reports — directly into the early-COVID Permian oil-price crash. WTI fell from \$53 on 2020-02-05 to \$45 on 2020-02-21 and continued to \$20 by mid-March 2020. The trade exits captured the first leg of that crash, producing −21.9% (OXY) and −12.1% (SM) realisations on what had been mechanically valid SAR-driven `modest_beat` signals at T-14.

**With the two COVID-exit-window trades (2019-Q4 OXY and SM) excluded as a regime-mismatch event, the remaining 8 trades yield 5W / 3L (62.5% hit rate), +\$13,389 net P&L (+1.34% on \$1M), and +0.17% mean per-trade net return. We report the full ten-trade sample as the headline rather than excluding the COVID tail, but flag the 2020-Q1 dislocation explicitly in §12 (Limitations) since it is the single largest contributor to negative aggregate P&L.**

A second observable pattern is **Agent 3's behaviour through 2020**. Across all 28 cells in the 2020 trade-eligible universe, the SAR-anchored Agent-2 forecast did not produce any `modest_beat` or `strong_beat` divergence — Agent 1's pad-classifications correctly registered the COVID drilling collapse, Agent 2's consensus-anchored forecast tracked downward consensus revisions, and Agent 3 short-circuited every cell to no_trade. The system mechanically held flat through 2020. We treat this as the strongest possible behavioural validation of the gating logic on a real out-of-sample regime: the system did not "blindly fire" through a market dislocation it had no way to predict.

## 9.2 Primary test (H1)

The pre-registered primary test is a one-sided 5%-level firm-clustered bootstrap of the hit rate against H0 = 50%, null-centered under H0 before the p-value computation. The observed hit rate on Strategy 1's full 2019-2024 trade set is 0.500 (5 wins, 5 losses out of 10 long entries). The exact one-sided binomial test (5 wins of 10, p = 0.5) yields **p = 0.623** (cumulative right-tail at 5/10) and the firm-clustered bootstrap p-value is **p = 0.50**; both **fail to reject H0 = 50%**. The 95% exact-binomial confidence interval on the hit rate is [18.7%, 81.3%], which is wide but informative: with n = 10 we can rule out hit rates below 18.7% and above 81.3% at the 95% level, but we cannot make a sharp claim about the true value of the rate.

The interpretation we attach to this result is conservative. The firm-clustered bootstrap is non-parametric and does not require a Gaussian return distribution, but with n = 10 trades and 5 wins, the test has limited power. The headline finding is that **after extending the empirical window from one year (2024-only, n = 2 trades) to six years (2019-2024, n = 10 trades), the hit rate stays at 50% and the test continues to fail to reject the coin-flip null**. This is the most honest framing of the data.

## 9.3 Quarter-block sensitivity

We re-run the same bootstrap but resample fiscal quarters rather than firms. The quarter-block 95% interval is wider (the procedure absorbs cross-sectional and time-series dependence), and the one-sided p-value at H0 = 50% is reported in the supplementary inference table. The directional conclusion is unchanged: cannot reject H0 = 50%.

## 9.4 H2 — full-system versus analyst-revision baseline

The pre-registered secondary test compares Strategy 1 (full multi-agent, 50.0% hit rate over 10 trades) against Strategy 3 (analyst-revision follower, 27.8% hit rate over 18 trades on the 2024 sub-window). The pre-registered threshold is +3 percentage points. We use Strategy 3's 2024 sample as the baseline because the deterministic single-signal baselines (Strategies 3-10 in §10) were run on the 2024 window only; extending those baselines to 2019-2024 is a future-work item documented in §12.9. The observed gap is +22.2 percentage points; the one-sided p-value (null-centered under H0: diff ≤ 3pp) is p = 0.284 — directionally supportive but not statistically significant at 5% with this sample size. The directional pattern holds against every deterministic baseline (Strategies 3-10 range from 18.8% to 33.3% hit rate; Strategy 1's 50% on 2024-only would have been 50% (1W/1L) and on the full 2019-2024 sample is 50% (5W/5L) — at least the equal-best, ahead of all deterministic baselines by 17 percentage points). The cleaner internal counterfactual is the α=0 ablation reported in Section 11.1, which is mechanically guaranteed to produce zero long entries.

## 9.5 SAR change-detection threshold sensitivity (RQ1, deferred)

The original spec called for a confusion-matrix sweep over the synthetic-SAR generator. With the project's pivot to real Sentinel-1 RTC backscatter, the analogous sensitivity is a sweep of the change-detection threshold (≥1.5 dB activation, ≥0.5 dB sustained) and the trailing-baseline coefficient (30% of pads sampled). Sweeping these would re-run the multi-agent pipeline at multiple threshold settings and compare trade counts and hit rates; we leave this as future work because each additional setting would require ~30 min of LLM agent runtime per year of backtest under the project's free-tier rate limits — the full 2019-2024 window at five threshold settings would be 25-30 hours of additional runtime. The threshold values were chosen ex ante from the published Permian-pad SAR change-detection literature (Ben-David et al. 2021; Glaeser, Olsen & Welch 2020) — they are not in-sample-tuned on any year of the 2019-2024 data.

## 9.6 Per-trade ledger

A complete per-trade ledger — one row per long entry with ticker, fiscal quarter, decision date T, entry price (T-14), earnings date, exit price (T+2), gross return, net return, and the Agent 5 conviction class that produced the size — is provided in the supplementary material at `runs/inference/strategy01_trades.csv`. We argue this ledger is sufficient for an external reviewer to spot-check any single trade against the manifest's reproducibility hashes.
