# Financial-Factor Baselines (Strategies 8, 9, 10) — Spec

## Purpose

The project requirement explicitly mandates testing whether the alternative-data signal improves performance beyond momentum, value, quality, and (carry-equivalent) sentiment baselines. The original 7-strategy comparison set covered macro-momentum, alt-data-without-satellite, and naive diversification, but lacked single-stock momentum, value, and quality baselines. This spec defines Strategies 8, 9, 10 added under DL #49.

This spec resolves Pre-Code Action Item 16. Per the project-goal alignment in DL #48, baselines are specified ambitiously here for the paper but execution emphasis is on demonstrating coherent design, not production-grade reproduction of every academic factor convention.

## Common Conventions

All three strategies share the following shape:

- **Universe**: same point-in-time eligible universe used by the satellite system at each decision date T (per DL #44, equity universe constructed annually with eligibility re-checked).
- **Holding rule**: top 4 names ranked by the strategy's signal, equal-weighted, rebalanced quarterly at the same T-14 anchor used by Strategy 1.
- **Holding period**: T-14 entry, T+2 exit (matched to Strategy 1 to keep transaction-cost and timing exposure comparable).
- **Long-only**, 30 bps round-trip cost, total return with dividends reinvested.
- **Cash sleeve**: BIL (per DL #24) when the universe has fewer than 4 eligible names in a quarter.
- **Bootstrap inference**: same firm-clustered bootstrap as Strategy 1 for hit-rate / return statistics; placebo and residualization tests applied uniformly.

## Strategy 8 — Cross-Sectional 12-1 Stock Momentum

The classic single-stock momentum factor adapted to the small Permian universe.

- **Signal**: trailing 12-month total return of the stock excluding the most recent month, as of T-14. That is, return from `T - 14 - 12 months` to `T - 14 - 1 month`. The 1-month skip avoids short-term reversal contamination.
- **Source**: CRSP daily total-return file (`crsp.dsf`) via WRDS, joined to share counts and adjustment factors. Use `ret` (with-dividends) and reinvest splits.
- **Ranking**: at each T-14, rank eligible names by the 12-1 momentum value descending. Take the top 4. Ties broken by larger market cap.
- **Edge cases**: if a name has fewer than 12 months of CRSP history at T-14 (e.g., CRGY's 2021 IPO, PR's 2022 merger), it is excluded from the ranking that quarter.
- **Pre-code: implementable as a 30-line pandas script after the eligibility table is built.**

## Strategy 9 — Value Composite

A long-only value tilt using three standard valuation ratios for E&Ps.

- **Signal**: equal-weighted z-score composite of the inverse of three ratios, all computed from Compustat fundamentals (`comp.fundq` for quarterly) lagged to the most recently reported quarter as of T-14:
  1. **EV/EBITDA**: `(market_cap + total_debt − cash) / ebitda`. Lower is better, so the signal is the negative of this ratio.
  2. **P/B**: `price / book_value_per_share`. Lower is better; signal is the negative.
  3. **FCF yield**: `(operating_cash_flow − capex) / market_cap`. Higher is better; signal is the value itself.
- **Compustat fields**:
  - EBITDA: `oibdpq` (operating income before depreciation, quarterly).
  - Total debt: `dlttq + dlcq` (long-term + current debt).
  - Cash: `cheq`.
  - Book value: `ceqq` (common equity, quarterly).
  - Operating cash flow: `oancfy` (year-to-date) differenced quarterly.
  - Capex: `capxy` (year-to-date) differenced quarterly.
- **Market cap, price** from CRSP joined via the IBES-CRSP-Compustat linker (`wrdsapps_link_crsp_ibes` + Compustat-CRSP CCM linker).
- **Lag rule**: a Compustat quarterly observation is "available" at T-14 if its filing date (`rdq`) is on or before T-14. Otherwise the prior quarter is used.
- **Ranking**: at each T-14, rank eligible names by the composite z-score descending. Take the top 4.
- **Edge cases**: any field missing or undefined (e.g., negative EBITDA, negative book equity) makes that ratio NA; the composite uses the available subset of ratios; if all three are NA, the name is excluded from ranking.

## Strategy 10 — Quality Composite

A long-only quality tilt using three standard quality metrics adapted for capital-intensive E&Ps.

- **Signal**: equal-weighted z-score composite of:
  1. **Trailing-12-month return on equity**: `sum(niq, last 4 quarters) / mean(ceqq, last 4 quarters)`. Higher is better.
  2. **Inverse debt-to-equity**: `−(dlttq + dlcq) / ceqq`. Lower D/E is better, so signal is the negative.
  3. **Operating cash flow margin**: `oancfy_diff / saleq` for the most recent quarter. Higher is better.
- **Source**: same Compustat `comp.fundq` lagged-to-`rdq` rule as Strategy 9.
- **Ranking**: same top-4 equal-weight rule as Strategies 8 and 9.
- **Edge cases**: same NA / fallback rule.

## Data Pull Plan (single WRDS pass)

A single WRDS Compustat + CRSP pull supports both Strategy 9 and Strategy 10 (and is reusable for the residualization and ablation analyses in Robustness Checks):

1. **Compustat fundq** for the 10 candidate tickers, fields: `gvkey, datadate, fyearq, fqtr, rdq, saleq, oibdpq, niq, oancfy, capxy, ceqq, dlttq, dlcq, cheq` over 2019-01-01 to 2025-12-31 (need 2019 for trailing-12-month inputs at the 2021 start).
2. **CRSP dsf** for the same names, fields: `permno, date, prc, ret, shrout, vol, cfacshr, cfacpr` over 2019-12-31 to 2024-12-31 (CRSP annual update lag — see CRSP 2025 supplementation note below). Need 12 months pre-window for momentum.
3. **CCM linktable** to map gvkey ↔ permno over the relevant period.
4. **IBES-CRSP linker** (`wrdsapps_link_crsp_ibes`) to map IBES ticker ↔ permno; combined with the CCM link this gives us all three identifier crosswalks.

All three sources are subscribed (verified during Phase 1 WRDS access check).

**CRSP 2025 supplementation (locked decision per Round 6 cleanup):** the WRDS CRSP annual update covers 2019-12-31 through 2024-12-31. For Q1-Q4 2025 (the final 4 quarters of the backtest), daily prices and total returns are supplemented from Yahoo Finance via the `yfinance` Python package. Yahoo's `Adj Close` field provides total-return-adjusted prices that handle splits and dividends. The patch is applied per-ticker by appending Yahoo rows for dates after 2024-12-31 to the CRSP dataframe. Data provenance (CRSP vs Yahoo) is recorded in the reproducibility manifest and acknowledged in the paper's Data section. This is the only Yahoo-Finance-sourced input in the system; all other prices, fundamentals, and consensus data remain WRDS-sourced.

## Output

`phase1/output/financial_factor_signals.parquet`: one row per (ticker × T-14 decision date), columns:

- `ticker`, `decision_date_T`
- `mom_12_1` (Strategy 8 raw signal)
- `value_score` (Strategy 9 composite z-score)
- `quality_score` (Strategy 10 composite z-score)
- `mom_rank`, `value_rank`, `quality_rank` (within-quarter rank, 1 = best)
- `mom_top4`, `value_top4`, `quality_top4` (boolean)

This file is consumed by the backtest harness when running Strategies 8, 9, 10 and feeds the residualization regression (DL #33).

## Sign-off Gate

This spec is final once the Compustat + CRSP pull confirms field availability across all 10 candidates and the 2019-2025 window. If any field is missing for a name, that name's value/quality scores are NA for the affected quarters; the strategy still runs on the rest of the universe.
