# WRDS I/B/E/S Production-Volume Coverage — Query Specification

## Purpose

Pull point-in-time analyst forecasts of quarterly production volume for the 10 candidate universe names over Q1 2021 to Q4 2025, from I/B/E/S detail history via WRDS. Output drives the `ibes_*` columns of the eligibility audit table and locks the final tradable universe.

This spec resolves Open Item 1 and Pre-Code Action Item 4.

## Database and Table

I/B/E/S forecasts split into separate tables by measure type. Production volume is a non-financial KPI, so it lives in the **I/B/E/S Estimates — Detail (Non-Financial / KPI)** database, not the EPS detail file.

- **Library**: `IBES`
- **Primary table**: `IBES.DET_KPI` (US detail history, KPI metrics including production)
  - WRDS naming may vary by vintage; alternates: `IBES.DETU_KPI`, `IBES.KPI_DET`. Verify exact table name in WRDS web interface before scripting.
- **Companion lookup tables**:
  - `IBES.IDSUM` (ticker-CUSIP-name crosswalk; needed because I/B/E/S uses internal `TICKER` codes, not exchange tickers)
  - `IBES.KPIMEASURE` (or equivalent) — measure-code dictionary

## Measure Identification

Production-volume forecasts are typically coded under:

- `OilProd` / `OilProductionForecast` — oil-only production (b/d)
- `GasProd` — natural gas production (Mcf/d)
- `BoeProd` / `TotalProduction` — total production in boe/d (preferred for our target)
- `Hydrocarbon` (older I/B/E/S codings)

**Required step before query**: pull the measure dictionary for each ticker and identify which codes have non-empty estimates for our window. The label-definition spec requires `boe/d total, net of royalties, continuing operations`; map to the I/B/E/S code that aligns most closely. If only oil-only or gas-only is available, that ticker may be dropped or treated as sensitivity.

```sql
SELECT DISTINCT TICKER, MEASURE, COUNT(*) AS n_estimates
FROM IBES.DET_KPI
WHERE TICKER IN ('FANG','EOGE','DVN','CTRA','OXY','MTDR','PR','OVV','SM','CRGY')
  AND ANNDATS BETWEEN '2020-01-01' AND '2025-12-31'
GROUP BY TICKER, MEASURE
ORDER BY TICKER, MEASURE;
```

(Note: I/B/E/S `TICKER` differs from exchange ticker for some names — `EOG` may appear as `EOGE`, etc. Validate via `IBES.IDSUM` mapping against CUSIP. Crescent Energy's I/B/E/S ticker may be `CRGY` or `CRG`.)

## Point-in-Time Reconstruction

For each (firm, fiscal-quarter, decision_date_T) triple, the active analyst forecast set at T is defined as estimates where:

- `ANNDATS ≤ T` (estimate was announced on or before T)
- `(REVDATS IS NULL) OR (REVDATS > T)` (estimate had not been revised away by T)
- `(STOPDATS IS NULL) OR (STOPDATS > T)` (estimate had not been stopped/withdrawn by T)
- `FPEDATS = quarter_end_date` (forecast period ends on the target quarter's last day)
- `FPI IN ('6','7','8','9')` (quarterly forecast period indicators; verify in WRDS docs — `FPI=6` is current-quarter, `FPI=7` next-quarter, etc.)

This produces the analyst panel as known at T, not the panel as known today.

## Per-Row Query (Pseudo-SQL)

For one ticker × one fiscal quarter:

```sql
WITH active_estimates AS (
  SELECT
    e.TICKER,
    e.ANALYST,
    e.ESTIMATOR,
    e.MEASURE,
    e.VALUE,
    e.UNIT,
    e.ANNDATS,
    e.REVDATS,
    e.STOPDATS,
    e.FPEDATS,
    e.FPI
  FROM IBES.DET_KPI e
  WHERE e.TICKER = :ibes_ticker
    AND e.MEASURE = :production_measure_code
    AND e.FPEDATS = :quarter_end_date
    AND e.ANNDATS <= :decision_date_T
    AND (e.REVDATS IS NULL OR e.REVDATS > :decision_date_T)
    AND (e.STOPDATS IS NULL OR e.STOPDATS > :decision_date_T)
)
SELECT
  COUNT(DISTINCT ANALYST) AS estimates_count,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY VALUE) AS consensus_median,
  AVG(VALUE) AS consensus_mean,
  STDDEV(VALUE) AS dispersion,
  MAX(ANNDATS) AS newest_estimate_date,
  :decision_date_T - MAX(ANNDATS) AS estimate_age_days
FROM active_estimates;
```

Run for all 200 (ticker × quarter) combinations.

## Coverage Decision Thresholds

| Threshold | Interpretation | Action |
|---|---|---|
| `estimates_count ≥ 5` | High coverage | Eligible, primary spec. |
| `3 ≤ estimates_count < 5` | Adequate coverage | Eligible, flagged for sensitivity reporting. |
| `1 ≤ estimates_count < 3` | Thin coverage | Quarter excluded; if persistent across name, drop name from headline universe. |
| `estimates_count = 0` | No coverage | Quarter excluded automatically. |

A name is dropped from the **headline tradable universe** if `estimates_count ≥ 3` for fewer than 12 of 20 quarters (60% coverage rule from `eligibility_audit_schema.md`).

## Python Wrapper Spec

Implementation lives in `phase1/code/wrds_ibes_pull.py` (to be written in Phase 2 once spec is signed off):

```python
import wrds
import pandas as pd

def fetch_ibes_coverage(
    db: wrds.Connection,
    ibes_ticker: str,
    quarter_end_date: pd.Timestamp,
    decision_date_T: pd.Timestamp,
    measure_code: str,
) -> dict:
    """
    Returns a dict with: estimates_count, consensus_median, consensus_mean,
    dispersion, newest_estimate_date, estimate_age_days.
    """
    # parameterized query as above
    ...

def build_coverage_panel(
    universe: list[str],          # I/B/E/S tickers
    quarter_ends: list[pd.Timestamp],
    decision_dates_T: dict,       # {(ticker, quarter): T}
    measure_code_map: dict,       # {ticker: measure_code}
) -> pd.DataFrame:
    """
    Returns a 200-row dataframe matching the IBES columns of the eligibility table.
    """
    ...
```

## Validation Checks Before Trusting Output

1. **Sanity vs current consensus**: pull the most recent (today) I/B/E/S consensus for each ticker × FPEDATS already passed; confirm it matches what financial data terminals report. If gaps, the table or measure code is wrong.
2. **Estimate-age distribution**: `estimate_age_days` should be roughly bimodal (clusters at ~14 days post-prior-earnings and just before next earnings). Long tails > 90 days indicate stale or stopped estimates not properly filtered.
3. **Cross-name consistency**: median consensus values for FANG, EOG, DVN should be in the right order of magnitude (hundreds of thousands of boe/d). If values look like dollar amounts or percentages, the measure code is misidentified.

## Out of Scope for This Query

- Revenue forecasts (revenue-prediction fallback was removed in DL #30; revenue I/B/E/S coverage is not pulled).
- EPS, EBITDA, or other financial KPI forecasts.
- Long-horizon (annual or multi-year) production forecasts.
- Non-US-listed I/B/E/S panel (international detail file).

## Deliverable

A signed CSV/Parquet file: `phase1/output/ibes_coverage_panel.parquet` with one row per (ticker × fiscal quarter), containing the columns documented above. This file is then merged into the eligibility audit table (`eligibility_table.parquet`) by ticker × fiscal quarter join keys.
