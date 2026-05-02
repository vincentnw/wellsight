# Phase 1 Status — End-of-Session Snapshot

Date: 2026-04-28.

## Executive Summary

Phase 1 (paper-cheap audits and data foundation) is substantially complete. Three live WRDS pulls landed: I/B/E/S revenue consensus (`tr_ibes` SAL), Compustat quarterly fundamentals (`comp.fundq`), and CRSP daily stock file. The headline target variable (revenue) and the financial-factor baselines (Strategies 8, 9, 10) are now backed by real data. Two known gaps remain (10-K Permian-fraction extraction; CRSP 2025 lag), neither blocking. Phase 2 (data-foundation pipelines) and Phase 3 (SAR validation) can begin.

## Data In Hand

| File | Rows | Window | Use |
|---|---|---|---|
| `phase1/output/ibes_tr_ibes_sal_query11220958.csv` | 22,449 | 2020-01-01 → 2025-12-31 | Raw I/B/E/S analyst-level revenue forecasts. |
| `phase1/output/ibes_revenue_coverage.csv` | 200 | 2021Q1 → 2025Q4 | Per (ticker × quarter) coverage panel: estimate counts, consensus, dispersion. |
| `phase1/output/compustat_fundq.csv` | 276 | 2019Q1 → 2025Q4 | Quarterly fundamentals for value/quality baselines. |
| `phase1/output/crsp_daily.csv` | 13,360 | 2019-12-31 → 2024-12-31 | Daily prices and returns for momentum baseline and market-cap calc. |

## Specs Authored

| Spec | Status |
|---|---|
| `phase1/eligibility_audit_schema.md` | Authored. Column-level schema for the company-quarter eligibility table. |
| `phase1/wrds_ibes_query_spec.md` | Authored (production-target version, superseded by addendum). |
| `phase1/revenue_pivot_addendum.md` | Authored. Canonical for revenue target. |
| `phase1/label_definition.md` | Authored (production-label version, superseded by addendum). |
| `phase1/agent4_scope_narrowing.md` | Authored. Agent 4 narrowing applied to project_overview.md line 22. |
| `phase1/financial_factor_baselines_spec.md` | Authored. Strategies 8, 9, 10 construction logic. |
| `phase1/output/coverage_audit_findings.md` | Authored. Per-ticker per-quarter coverage analysis. |
| `phase1/output/phase1_status.md` | This file. |

## Resolved Open Items

- **Open Item 1 (I/B/E/S revenue coverage)**: Resolved. All 10 candidates retained; 186/200 firm-quarter cells trade-eligible; thin quarters cleanly explained by corporate actions (CTRA Oct-2021 merger, CRGY Dec-2021 IPO, PR Sep-2022 merger). See `coverage_audit_findings.md`.

## Resolved Round 6 Pivot Items

- **Target locked to revenue** (DL #47). Production-volume target unreachable due to user's WRDS subscription not including `tr_ibeskpi`. Drilling-to-revenue chain modeled explicitly inside Agent 2.
- **Project-goal alignment** (DL #48). Codex review framing now includes "innovative thinking, not full correctness." SAR-validation gate softened to transparent reporting.
- **Baseline expansion to 10 strategies** (DL #49). Strategies 8 (momentum), 9 (value), 10 (quality) added; data pulled.
- **Revenue-target ablation update** (DL #50).

## Phase 1 Items Remaining

These are paper-spec items whose execution is light but should be done before any backtest run:

1. **10-K Permian-fraction extraction**: 10 companies × 5 fiscal years = 50 manual lookups of segment-level Permian production share. Used for satellite-side revenue forecast scaling. Light effort, but required input to Agent 2's deterministic forecast model.
2. **Earnings-date provenance pipeline**: Wall Street Horizon (via WRDS) primary, Wayback Machine fallback. 200 announcement dates to verify pre-T-14 provability. Doable in a single afternoon.
3. **Point-in-time equity universe constructor** (Pre-Code Action Item 11): annual eligibility recomputation script. Trivial given the eligibility table.
4. **Drilling-to-revenue forecast model freeze** (Pre-Code Action Item 18): write the deterministic Python function in Agent 2; document assumptions (decline curve, realized-price differential).
5. **LLM determinism manifest**: pin model versions, write JSON schemas for each agent's output, run 5-call stability check. Done before backtest, not before.

## Known Gaps and Documented Limitations

### CRSP 2025 lag

CRSP annual update goes through 2024-12-31 only. 2025 daily prices and returns are not yet in WRDS CRSP annual file. This affects:
- Strategy 8 (12-1 momentum): Q1 2025 onward needs 2025 returns, missing.
- Strategies 9, 10 (value, quality): need market cap (price × shares outstanding) at each T-14, missing for 2025.
- Realized portfolio returns for the satellite system itself (Strategy 1) for 2025.

**Mitigation: LOCKED to option (a) — Yahoo Finance supplement for 2025** (Round 6 cleanup decision). Use CRSP through 2024-12-31 then `yfinance` `Adj Close` for 2025 dates. Yahoo's adjusted-close handles dividends and splits, total-return equivalent. Patch is applied per-ticker by appending Yahoo rows for dates after 2024-12-31 to the CRSP dataframe. Data provenance (CRSP vs Yahoo) is recorded in the reproducibility manifest and acknowledged in the paper's Data section. This is the only Yahoo-Finance-sourced input in the system; all other prices, fundamentals, and consensus data remain WRDS-sourced. Backtest covers the full 20-quarter window (Q1 2021–Q4 2025), not a truncated 16-quarter version.

### Legacy ticker mapping in CRSP

CRSP returned 14 ticker variants instead of 10 because companies that merged or rebranded carry pre-event tickers under different PERMNOs:
- COG (Cabot Oil & Gas) → CTRA (Coterra after Oct 2021 merger).
- CDEV (Centennial Resource) → PR (Permian Resources after Sept 2022 merger).
- ECA (Encana) → OVV (Ovintiv, renamed Jan 2020).
- AMR (likely Alpha Metallurgical, unrelated; may be a name-search false positive).

This is actually useful: continuous price history through corporate actions. The point-in-time equity universe constructor will keep the correct PERMNO active by date and exclude the AMR false positive. To document in Phase 2 alongside the universe constructor.

### 10-K segment data not yet extracted

Phase 1 did not pull per-company per-fiscal-year Permian production fraction from 10-K segment reporting. This is a small manual job (50 lookups). Without it, the satellite-side revenue forecast inside Agent 2 cannot scale Permian-only signal to total-company revenue for non-pure-play names (EOG, OXY, OVV, DVN, CTRA). For pure-play names (FANG, MTDR, PR), Permian fraction ≈ 100% so this is non-blocking for them.

## Gated by Phase 3

The trading-layer backtest cannot run until SAR detection validation has been performed. Per project-goal alignment (DL #48), this is now a transparency gate rather than a hard pivot trigger:
- Validate on 80-site sample against TRC spud/completion records.
- Report precision and recall.
- If weak (<0.70 / <0.60), document in Limitations and continue; do not pivot.

## Suggested Next Steps

In rough priority order:

1. (User, not me) — verify Phase 1 specs. CRSP 2025 mitigation path is now LOCKED to Yahoo Finance supplement.
2. Write the point-in-time equity-universe constructor (Pre-Code #11) as a Python script. ~50 lines, uses the eligibility table.
3. Write the deterministic drilling-to-revenue forecast function (Pre-Code #18). ~100 lines.
4. Manual 10-K segment extraction (50 lookups) for Permian-fraction scaling.
5. Earnings-date provenance via Wall Street Horizon on WRDS (Pre-Code #14).
6. Begin Phase 3 SAR validation pipeline scaffolding (Sentinel-1 ingestion via GEE, change-detection algorithm, TRC ground-truth join).

## Sign-Off

Phase 1 data foundation is sufficient to begin Phase 2 and Phase 3 in parallel. No blocking unknowns remain.
