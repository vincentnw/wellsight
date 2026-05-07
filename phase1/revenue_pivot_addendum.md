# Phase 1 Specs — Revenue Pivot Addendum

This addendum records the changes that flow through the three earlier Phase 1 specs (`eligibility_audit_schema.md`, `label_definition.md`, `wrds_ibes_query_spec.md`) after the Round 6 pivot from production-volume target to revenue target. Per Decision Log entries #47 and #48 in `project_overview.md`, the target was pivoted because the user's WRDS subscription does not include `tr_ibeskpi`, and because the project requirement explicitly mandates testing improvement beyond financial-factor baselines (which requires a tradable financial signal, not a signal-validation result).

This addendum is canonical where it conflicts with the earlier specs.

## 1. Locked Target — Revenue (replaces production-volume label spec)

| Dimension | Required value |
|---|---|
| Variable | Quarterly total revenue, USD millions |
| Source for actual | SEC EDGAR 10-Q income statement, point-in-time accurate via filing date |
| Source for consensus | I/B/E/S Detail History (`tr_ibes`) sales/revenue measure code via WRDS, point-in-time as of T-14 |
| Operations scope | Continuing operations only (discontinued ops excluded) |
| Geographic scope | Total-company consolidated (Permian-segment revenue is not a separate label in I/B/E/S; segment-level disclosure is used only inside the satellite-side forecast for Permian-revenue-share scaling) |
| Currency | USD; companies that report in another reporting currency (none expected in this universe) are out of scope |

The locked threshold rule remains: if our satellite-derived revenue forecast exceeds I/B/E/S consensus revenue by more than 10% (default; threshold sweep at 5/10/15/20% per Robustness Checks), the signal is "beat" — go long. Within ±10%, no trade. Below −10%, no trade in long-only. The directional logic is unchanged from the production version; only the label, source, and forecast-construction mechanics change.

## 2. WRDS Query Update — `tr_ibes` Sales/Revenue (replaces `tr_ibeskpi` plan)

The earlier `wrds_ibes_query_spec.md` targeted `IBES.DET_KPI` (full KPI database). The user's institution does not subscribe to `tr_ibeskpi`. The revised target is `tr_ibes` Detail History.

Library: `IBES`
Primary table: `IBES.DET_EPSUS` (US detail history; `tr_ibes` schema). Sales/revenue measure is one of the supported `MEASURE` codes in this table — the standard I/B/E/S measure code for sales/revenue is `SAL` (verify against the WRDS measure dictionary at first query).

Discovery query (run before the full pull, on the user's WRDS account):

```sql
SELECT DISTINCT TICKER, MEASURE, COUNT(*) AS n_estimates
FROM IBES.DET_EPSUS
WHERE TICKER IN ('FANG','EOG','DVN','CTRA','OXY','MTDR','PR','OVV','SM','CRGY')
  AND ANNDATS BETWEEN '2020-01-01' AND '2025-12-31'
  AND MEASURE IN ('SAL','REV','SALES')
GROUP BY TICKER, MEASURE
ORDER BY TICKER, MEASURE;
```

(I/B/E/S `TICKER` may differ from exchange ticker for some names. Validate via `IBES.IDSUM` mapping against CUSIP. Confirm exact measure code from WRDS measure dictionary at first run; `SAL` is the standard but legacy data may use `REV`.)

Point-in-time reconstruction logic, coverage thresholds, and per-row query template otherwise carry over from `wrds_ibes_query_spec.md` unchanged, with `MEASURE = 'SAL'` substituted for the production measure.

Output file: `phase1/output/ibes_revenue_coverage.parquet` (and `.csv` mirror).

## 3. Eligibility Audit Schema — Column Updates

The schema defined in `eligibility_audit_schema.md` carries forward, with these column changes:

**Replace** these columns (production-volume specific):

- `ibes_measure_code` — now references the sales/revenue measure code (typically `SAL`).
- `ibes_estimates_count_at_T` — now counts revenue estimates, not production estimates.
- `ibes_consensus_at_T` — now units USD millions, not boe/d.
- `ibes_dispersion_at_T` — units USD millions.
- `reports_permian_segment` — repurposed from "Permian-segment production disclosed" to "Permian-segment revenue or operating income disclosed in segment reporting note." Optional, used only for scaling the satellite forecast.
- `target_basis`, `target_basis_final` — collapse to a single value `consolidated_revenue` for all rows. The `segment` value is retired (revenue consensus is total-company by default in I/B/E/S).
- `reporting_basis_net_or_gross`, `boe_conversion_ratio`, `oil_only_or_full_boe` — retired (not applicable to revenue label).

**Retain unchanged**:

- All identity columns.
- All tradability columns (`listed_us_exchange_at_T`, `market_cap_at_T_usd`, `adv_30d_at_T_usd`, `permian_production_fraction_ttm`, `permian_fraction_as_of_date`).
- Earnings-date provenance columns.
- `eligible_for_trading`, `ineligibility_reasons`, `notes`.

**New column**:

- `permian_revenue_share_estimate` — float, fraction of company's revenue attributable to Permian assets, derived from segment revenue disclosure or production-share approximation. Lagged to most recent 10-K. Used only inside the satellite-side revenue forecast to scale the Permian-derived production signal to the company's total revenue context. Not used for label conformance.

## 4. Drilling-to-Revenue Forecast Model — Inside Agent 2

The deterministic forecast inside the (renamed) Revenue Forecast Agent has three steps:

1. **Drilling → production**: from active site count attributed to operator at decision date T (point-in-time site universe), apply per-operator wells-per-pad ratio (TRC completion records, lagged) and EIA Permian type-curve decline applied to existing wells. Output: estimated incremental Permian production (boe/d) for the target quarter.

2. **Production → Permian revenue**: multiply estimated Permian production by the average WTI spot price for the target quarter, restricted to WTI prints publicly available before T-14 (use the realized average up to T-14 as the proxy for the full-quarter average). Multiply by the company-specific historical realized-price differential (oil + NGL + gas blended realized price ÷ WTI, computed from prior 4-quarter 10-Q disclosures, lagged). Output: estimated Permian revenue for the target quarter.

3. **Permian revenue → total-company revenue**: divide the Permian revenue estimate by the company's most recently disclosed Permian revenue share (or production-share approximation) to scale up to total-company revenue. For pure-play Permian names (FANG, MTDR, PR), this division factor is ≈1.

The LLM in Agent 2 reads the resulting numerical forecast and writes a qualitative outlook paragraph; the LLM does not generate the number. All assumptions (decline curve, differential, scaling factor) are public-information-only, lagged, and recorded in the reproducibility manifest per Pre-Code Action Item 6.

## 5. Coverage Thresholds (unchanged from earlier spec)

| Threshold | Action |
|---|---|
| `estimates_count ≥ 5` | High coverage, primary spec. |
| `3 ≤ estimates_count < 5` | Adequate coverage, flagged for sensitivity. |
| `estimates_count < 3` | Quarter excluded. |

A name is dropped from the headline universe if `estimates_count ≥ 3` for fewer than 12 of 20 quarters.

## 6. Pre-Audit Per-Company Expectations (revised for revenue)

Sales/revenue coverage for US-listed liquid mid-and-large-cap E&Ps in `tr_ibes` is generally strong (typically 8-15 analysts). The risk profile differs from the production-volume case:

| Ticker | Revenue coverage risk |
|---|---|
| FANG, EOG, DVN, OXY, OVV | Low — large-cap, deep coverage expected. |
| CTRA, MTDR, PR, SM | Medium — mid-cap, coverage 5-10 analysts typical. |
| CRGY | Higher — recent IPO, smaller cap, may have 3-5 analyst coverage initially expanding over the window. |

The verification query in section 2 confirms or revises these expectations.

## 7. Sign-off Gate

This addendum supersedes the conflicting sections of the three earlier Phase 1 specs. Phase 1 sign-off requires the eligibility audit table to be filled using the revised column set, with the I/B/E/S coverage check executed against `tr_ibes` sales/revenue rather than `tr_ibeskpi` production.
