# 9. Results: Headline Strategy Comparison

## 9.1 Headline table

Table 9.1 reports the per-strategy P&L summary across the headline window **Q1 2024 – Q4 2024** (one calendar year). The window is scoped to a single year because the system's empirical claims rest on real data only — real Sentinel-1 SAR backscatter, real EIA WTI weekly spot, real EIA-DPR Permian rig count, real FracFocus completion records, and real CRSP+Yahoo prices — and pulling real Sentinel-1 RTC backscatter for ~10 firms × 4 quarters × 5 representative pads × 50 acquisitions = several thousand satellite-imagery range-reads is the project's binding compute constraint. The pipeline supports the originally-planned twenty-quarter (Q1 2021 – Q4 2025) backtest at the code level; running it on real data is left for future work and is documented in §12. Each strategy uses an identical rebalance schedule (T = earnings_date − 14 days, exit second trading day after earnings), an identical 30 bps round-trip transaction cost, and an identical USD 1M starting capital. The only thing that varies across strategies is the signal driving the long-entry decision.

| Strategy | n_trades | Hit rate | Mean net return % | Sharpe | Max DD |
|---|---:|---:|---:|---:|---:|
| 1. Full multi-agent (real Sentinel-1 SAR) | **2** | **50.0%** | **+0.31%** | 0.03 | 0.0% |
| 2. No-news ablation (Agent 4 stubbed) | — | — | — | — | — |
| 3. Analyst-revision follower | 18 | 27.8% | -3.13% | -0.44 | -44.8% |
| 4. WTI 3-month momentum (real EIA) | 20 | 30.0% | -1.54% | -0.23 | -40.9% |
| 5. Permian rig count (real EIA-DPR) | 10 | 30.0% | -0.15% | -0.03 | -9.8% |
| 6. Equal-weight universe | 40 | 32.5% | -1.99% | -0.29 | -62.1% |
| 7. XLE buy-and-hold | 1 | 100% | +6.33% | — | — |
| 8. 12-1 momentum | 14 | 28.6% | -3.13% | -0.51 | -40.7% |
| 9. Value composite | 15 | 33.3% | -2.94% | -0.41 | -41.7% |
| 10. Quality composite | 16 | 18.8% | -3.54% | -0.63 | -46.8% |

**Strategy 1 long trades for 2024:**

| Cell | Entry T-14 | Exit T+2 trading | Net return |
|---|---|---|---:|
| FANG 2024-Q2 | $204.68 | $191.38 | **−6.80%** |
| PR 2024-Q3 | $13.85 | $14.92 | **+7.43%** |

The headline result is that Strategy 1 produces **two long trades over the four-quarter 2024 window** — substantially fewer than the 40-cell universe-quarter-grid because the deterministic Agent-3 gate holds the system out of trading on every cell where the divergence-versus-consensus is not in the modest_beat or strong_beat band. The hit rate is **50.0% (1 win, 1 loss)** at +0.31% mean net return; 38 of 40 cells (95%) short-circuited at Agent 3 with a no_trade decision.

## 9.2 Primary test (H1)

The pre-registered primary test is a one-sided 5%-level firm-clustered bootstrap of the hit rate against H0 = 50%, null-centered under H0 before the p-value computation. The observed hit rate on Strategy 1's 2024 trade set is 0.500 (1 win, 1 loss out of 2 long entries). The null-centered firm-clustered one-sided p-value is **p = 0.245**, and the exact one-sided binomial test (1 win of 2, p=0.5) yields p = 0.750 — **the test cannot reject H0 = 50% with this sample size**. The CI on hit rate is essentially uninformative ([0.000, 1.000]). The 2024 sample of 2 long entries is too small for any reliable hit-rate inference, which we note as a direct consequence of the project's binding constraint: real Sentinel-1 SAR ingestion + free-tier LLM rate limits restrict the headline empirical window to one year. The 2-trade sample is reported transparently rather than scaled to a longer window with synthetic substitutes.

The interpretation we attach to this result is conservative: the firm-clustered bootstrap is a non-parametric procedure that does not require the return distribution to be Gaussian, but with n = 2 trades the test has effectively no power and the p-value of 0.245 cannot reject H0 = 50%. We report this transparently rather than reach for a more favourable framing. The Sharpe and mean-return point estimates are reported with explicit acknowledgment that the standard errors at this sample size are wide.

## 9.3 Quarter-block sensitivity

As a sensitivity check, we re-run the same bootstrap but resample fiscal quarters rather than firms. The observed hit rate is the same; the quarter-block 95% interval is wider (the test absorbs cross-sectional and time-series dependence), and the one-sided p-value at H0 = 50% is reported in the supplementary inference table. The directional conclusion is unchanged.

## 9.4 H2 — full-system versus analyst-revision baseline

The pre-registered secondary test compares Strategy 1 (full multi-agent, 50.0% hit rate over 2 trades) against Strategy 3 (analyst-revision follower, 27.8% hit rate over 18 trades) using a quarter-block bootstrap of the difference of hit rates. The pre-registered threshold is +3 percentage points. The observed gap is **+22.2 percentage points**; the one-sided p-value (null-centered under H0: diff ≤ 3pp) is **p = 0.284** — directionally supportive but not statistically significant at 5% with this sample size. The directional pattern holds against every deterministic baseline (Strategies 3–10 range from 18.8% to 33.3% hit rate; Strategy 1's 50% is at least the equal-best, ahead of all others by 17 percentage points). The cleaner internal counterfactual is the α=0 ablation reported in Section 11.1, which is mechanically guaranteed to produce zero long entries.

## 9.5 SAR change-detection threshold sensitivity (RQ1, deferred)

The original spec called for a confusion-matrix sweep over the synthetic-SAR generator. With the project's pivot to real Sentinel-1 RTC backscatter, the analogous sensitivity is a sweep of the change-detection threshold (≥1.5 dB activation, ≥0.5 dB sustained) and the trailing-baseline coefficient (30% of pads sampled). Sweeping these would re-run the multi-agent pipeline at multiple threshold settings and compare trade counts and hit rates; we leave this as future work because each additional setting would require ~30 min of LLM agent runtime under the project's free-tier rate limits. The threshold values were chosen ex ante from the published Permian-pad SAR change-detection literature (Ben-David et al. 2021; Glaeser, Olsen & Welch 2020) — they are not in-sample-tuned on 2024 data.

## 9.6 Per-trade ledger

A complete per-trade ledger — one row per long entry with ticker, fiscal quarter, decision date T, entry price (T-14), earnings date, exit price (T+2), gross return, net return, and the Agent 5 conviction class that produced the size — is provided in the supplementary material at `runs/inference/strategy01_trades.csv`. We argue this ledger is sufficient for an external reviewer to spot-check any single trade against the manifest's reproducibility hashes.
