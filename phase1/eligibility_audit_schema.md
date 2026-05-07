# Company-Quarter Eligibility Audit — Schema

## Purpose

For every (company × quarter) pair across the candidate universe over Q1 2021 to Q4 2025, document tradability, data availability, label conformance, and date provability. Output is a single eligibility table that drives the final tradable universe and per-quarter inclusion decisions. Built before any data pipeline or backtest code.

This audit subsumes Open Item 1 (I/B/E/S production-volume coverage check) and resolves Pre-Code Action Items 4, 8, 9, 11, 13, 14 in one pass.

## Scope

- Candidate universe: 10 Permian-focused E&Ps — FANG, EOG, DVN, CTRA, OXY, MTDR, PR, OVV, SM, CRGY.
- Window: 20 fiscal quarters, Q1 2021 through Q4 2025.
- Total rows: 200 (10 firms × 20 quarters), minus any quarters where the firm did not exist as a public entity.

## Output

`phase1/output/eligibility_table.parquet` (and `.csv` mirror for human inspection).

## Schema

### Identity

| Column | Type | Notes |
|---|---|---|
| `ticker` | string | Primary US listing ticker as of decision date T. |
| `company_name` | string | Legal name as of T. |
| `fiscal_quarter` | string | `YYYYQn` format (e.g., `2021Q1`). Aligned to company fiscal calendar (most are calendar-year). |
| `quarter_end_date` | date | Last day of fiscal quarter. |
| `earnings_date_actual` | date | Actual announcement date sourced from EDGAR 8-K filing timestamp. |
| `decision_date_T` | date | `earnings_date_actual − 14 calendar days`. Trade-entry anchor. |

### Tradability (annual recompute on Jan 1, recheck quarterly)

| Column | Type | Decision rule | Source |
|---|---|---|---|
| `listed_us_exchange_at_T` | bool | Required = True. NYSE/Nasdaq common stock. | CRSP via WRDS. |
| `market_cap_at_T_usd` | float | Required ≥ 500M. | CRSP closing price × shares outstanding. |
| `adv_30d_at_T_usd` | float | Sanity ≥ 5M (informational, not gating). | CRSP. |
| `permian_production_fraction_ttm` | float | Required ≥ 0.30. Trailing-12-month Permian production / total production from most recent 10-K segment disclosure. | 10-K segment data, manual extraction or Bloomberg. |
| `permian_fraction_as_of_date` | date | Date of the 10-K from which the fraction was extracted. | 10-K filing date. |

### I/B/E/S Production Coverage

| Column | Type | Decision rule | Source |
|---|---|---|---|
| `ibes_measure_code` | string | Production-volume measure code(s) used (e.g., `PRD`, `OIL`, custom). Documented per ticker in `wrds_ibes_query_spec.md`. | WRDS I/B/E/S detail. |
| `ibes_estimates_count_at_T` | int | Required ≥ 3 for primary spec, ≥ 5 for high-coverage spec. Number of distinct analysts with active production-volume estimates as of T. | WRDS I/B/E/S detail history. |
| `ibes_consensus_at_T` | float | Median analyst production-volume estimate as of T (point-in-time reconstruction). Units: boe/d. | WRDS I/B/E/S detail history. |
| `ibes_estimate_age_days` | int | Days between newest active estimate and T. Sanity flag if > 60 days. | WRDS I/B/E/S detail history. |
| `ibes_dispersion_at_T` | float | Cross-analyst standard deviation of estimates at T. | WRDS I/B/E/S detail history. |

### Label Definition Conformance

| Column | Type | Decision rule | Source |
|---|---|---|---|
| `reports_permian_segment` | bool | Does company disclose Permian-only production in 10-Q operational highlights or earnings release? | 10-Q / 8-K manual review. |
| `reports_consolidated` | bool | Always True for SEC filers; informational. | 10-Q. |
| `target_basis` | enum | `segment` if Permian-segment disclosed, else `consolidated`. Drives per-row prediction target. | Derived. |
| `reporting_basis_net_or_gross` | enum | `net` (royalty-deducted), `gross`, or `mixed`. | 10-Q footnotes. |
| `reporting_basis_continuing_ops` | bool | Required = True. Discontinued ops excluded. | 10-Q. |
| `boe_conversion_ratio` | float | Required = 6.0 (6 Mcf gas = 1 boe). Companies using non-6:1 conversions are flagged for conformance treatment. | 10-Q. |
| `oil_only_or_full_boe` | enum | `full_boe` required for primary spec; `oil_only` accepted only if I/B/E/S also reports oil-only for that ticker. | 10-Q. |
| `label_conformable` | bool | True iff: `target_basis ∈ {segment, consolidated}`, `reporting_basis_net_or_gross == net`, `boe_conversion_ratio == 6.0`, `oil_only_or_full_boe == full_boe`, `reporting_basis_continuing_ops == True`. Required = True for inclusion. | Derived. |

### Earnings-Date Provenance

| Column | Type | Decision rule | Source |
|---|---|---|---|
| `earnings_date_provable_pre_T` | bool | Required = True. Was the earnings date publicly known before T = `earnings_date_actual − 14`? | WSH or Wayback. |
| `earnings_date_source` | enum | `wall_street_horizon` (primary), `wayback_machine` (fallback), `none` (drop). | Derived. |
| `earnings_date_first_announced_date` | date | Date the announcement first became publicly known (WSH first-listed date or earliest Wayback snapshot showing the date). | WSH or Wayback. |
| `earnings_date_archive_url` | string | If Wayback: the snapshot URL. If WSH: the WSH record ID. | WSH or Wayback. |

### Outcome

| Column | Type | Decision rule |
|---|---|---|
| `eligible_for_trading` | bool | True iff ALL of: `listed_us_exchange_at_T == True`, `market_cap_at_T_usd >= 500M`, `permian_production_fraction_ttm >= 0.30`, `ibes_estimates_count_at_T >= 3`, `label_conformable == True`, `earnings_date_provable_pre_T == True`. |
| `ineligibility_reasons` | list[string] | Comma-separated codes if eligible_for_trading == False: `delisted`, `low_cap`, `low_permian_fraction`, `thin_coverage`, `nonconformable_label`, `unprovable_date`. |
| `target_basis_final` | enum | `segment` (use Permian-segment actuals + scaled satellite signal directly) or `consolidated` (use total-company actuals + Permian-fraction-scaled satellite signal). `dropped` if `eligible_for_trading == False`. |
| `notes` | string | Free-text manual annotations (M&A events, segment redefinitions, restatements). |

## Derived Decision Rules

1. **Final tradable universe** = set of tickers where `eligible_for_trading == True` for ≥ 12 of 20 quarters (60% coverage). Tickers below 60% are dropped from the headline strategy but reported in an appendix.
2. **Per-quarter inclusion** = tickers where `eligible_for_trading == True` for that specific quarter. A name may be in the universe overall but excluded from a specific quarter due to thin coverage that quarter, M&A disruption, or unprovable date.
3. **Primary specification** uses only rows where `target_basis_final == segment`. Sensitivity specification adds `target_basis_final == consolidated` rows with the Permian-fraction scaling caveat documented.
4. **Survivorship handling**: companies that delist mid-window (acquisitions, bankruptcies) get `eligible_for_trading == False` from the delisting quarter onward; all positions are exited at last close. The eligibility table preserves the historical record so the final paper can document entries and exits explicitly.

## Manual vs Automated Fields

| Automated (script) | Manual (one-time review) |
|---|---|
| `listed_us_exchange_at_T`, `market_cap_at_T_usd`, `adv_30d_at_T_usd` | `permian_production_fraction_ttm` (10-K segment table extraction) |
| `ibes_estimates_count_at_T`, `ibes_consensus_at_T`, `ibes_estimate_age_days`, `ibes_dispersion_at_T` | `reports_permian_segment`, `target_basis`, `reporting_basis_net_or_gross`, `oil_only_or_full_boe` |
| `earnings_date_actual`, `decision_date_T` | `earnings_date_provable_pre_T`, `earnings_date_source`, `earnings_date_first_announced_date`, `earnings_date_archive_url` (per ticker × quarter — 200 lookups) |
| `eligible_for_trading`, `ineligibility_reasons`, `target_basis_final` (derived) | `notes` |

## Expected Audit Outcomes (Hypotheses to Test)

These are pre-audit expectations to compare against actual findings, not assumptions:

- FANG, MTDR, PR: pure-play Permian, label_conformable likely True, segment disclosure likely True.
- EOG, OXY, OVV: ~30-50% Permian, may report Permian segment but consolidated production is total-company.
- DVN, CTRA, SM: mixed; segment disclosure varies by year.
- CRGY: smallest cap; I/B/E/S coverage is the primary risk.
- Earnings-date provability: WSH coverage on WRDS is generally strong for liquid US equities; Wayback fallback expected for at most 1-2 outlier quarters.

If actual audit results differ materially from these hypotheses, the design must adjust before code is written.

## Sign-off Gate

The eligibility table is reviewed and signed off in writing before Phase 2 begins. The signed table is the canonical input to all downstream pipeline code; any subsequent universe changes require an audit-table revision and a corresponding Decision Log entry.
