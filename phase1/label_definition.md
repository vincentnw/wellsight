# Production Label Definition — Locked Specification

## Purpose

Lock a single, unambiguous definition of the production-volume target variable. Every actual, every forecast, every consensus number, and every satellite-derived prediction is conformed to this definition or excluded. Mixing definitions across companies or quarters would contaminate hit-rate evaluation and cross-sectional ranking.

This spec resolves Pre-Code Action Item 13 and supports DL #46.

## The Locked Label

**Quarterly production volume, expressed in barrels of oil equivalent per day (boe/d), reported on the following basis:**

| Dimension | Required value |
|---|---|
| Unit | boe/d (barrels of oil equivalent per day, daily average over the fiscal quarter) |
| Royalty treatment | **Net of royalties** (working-interest production after royalty deductions) |
| Operations scope | **Continuing operations only** (discontinued operations excluded; assets held for sale excluded) |
| Hydrocarbon scope | **Full boe** (oil + NGLs + gas), not oil-only and not gas-only |
| Boe conversion | **6 Mcf gas = 1 boe** (the SEC standard energy-equivalent ratio for E&P companies) |
| Geographic scope | Determined per-row by `target_basis_final` in the eligibility table — either Permian-segment only OR consolidated total. Mixed targets are not allowed within the same row. |

## Per-Source Conformance Rules

### Source 1: Reported Actuals (10-Q operational highlights, 8-K earnings releases)

Most US E&P companies in the candidate universe report production in this format already; conformance is usually a straightforward extraction. Specific cases to handle:

- **Gross vs net**: if the company reports both, take net. If only gross is reported, conformance fails for that row and the quarter is excluded.
- **Three-stream vs two-stream**: three-stream (oil + NGLs + gas separately combined to boe) is the modern standard; two-stream (oil + wet gas) is legacy. Use whichever the company reports as long as the boe conversion is 6:1; flag two-stream rows in `notes`.
- **Discontinued operations / divestitures**: if a divestiture closed mid-quarter, use the company's stated continuing-operations production. If the company restates prior quarters post-divestiture, use the restated figure (the restatement is public information by the time it appears).
- **Boe conversion ratio**: SEC requires 6:1 for reserves disclosure, but some companies use different ratios for energy-equivalent in operational metrics. If `boe_conversion_ratio ≠ 6.0`, the row is excluded from the primary spec and reported as sensitivity only.
- **Permian-segment disclosure**: if the company breaks out Permian or "Delaware" or "Midland" production separately in the operational highlights table, that figure is the segment target. If only Delaware OR only Midland is disclosed (not both), sum them only if both are reported; otherwise mark as `consolidated` target_basis.

### Source 2: I/B/E/S Consensus (production-volume estimates)

I/B/E/S analyst forecasts must be conformed to the same definition as actuals. The matching rules:

- **Measure-code alignment**: the measure code chosen in `wrds_ibes_query_spec.md` must correspond to total boe/d net of royalties from continuing operations. If only oil-only or gas-only forecasts exist for a ticker, that ticker's coverage is treated as zero for the primary spec; sensitivity analysis may use oil-only with explicit footnote.
- **Forecast period**: `FPEDATS` must equal the company's fiscal quarter end. If the analyst forecast covers a non-standard period (e.g., a partial quarter due to a fiscal calendar shift), the row is excluded.
- **Geographic scope mismatch**: I/B/E/S typically reports total-company production, not Permian-segment. For rows with `target_basis_final == segment`, the satellite signal is compared against an internally constructed "implied Permian consensus" derived as `total_company_consensus × most_recent_disclosed_permian_fraction`. This scaling step is documented as an explicit modeling assumption in the paper, not as a data fact. For rows with `target_basis_final == consolidated`, I/B/E/S consensus is used directly.

### Source 3: Compustat (cross-check)

Compustat reports production in the supplemental items (`OG*` series). Used for sanity-check only, not as primary actuals. If Compustat and 10-Q numbers diverge by more than 2%, the row is flagged for manual review; the 10-Q figure is canonical.

### Source 4: EIA Company-Level Estimates (cross-check)

EIA publishes monthly company-level production estimates for the largest US E&P operators. Used for outlier detection only. If EIA and 10-Q diverge by more than 5% for a quarter, flag for manual review.

### Source 5: Satellite-Derived Forecast (model output)

The Production Forecast Agent's numerical output is denominated in the same unit (boe/d) and basis (net, continuing ops, full boe) as the target. Conformance is enforced by the model spec in `production_forecast_model_spec.md` (to be drafted under Pre-Code Action Item 10).

## Conformance Checklist (per company × quarter)

For each row of the eligibility table, the following six checks must pass for `label_conformable == True`:

- [ ] Reported actual is in boe/d (not barrels-only, not Mcf-only).
- [ ] Reported actual is net of royalties (working interest only).
- [ ] Reported actual is continuing operations.
- [ ] Reported boe conversion ratio is 6:1.
- [ ] I/B/E/S consensus exists for a measure code that maps to total boe/d (not oil-only).
- [ ] If `target_basis_final == segment`, the company discloses Permian-segment production for that quarter; if `consolidated`, total-company production is reported.

Any failed check triggers `label_conformable = False` and the row is excluded from the primary spec.

## Pre-Audit Per-Company Expectations (to verify, not assume)

These are the team's prior expectations to compare against actual conformance findings:

| Ticker | Expected target_basis | Risk |
|---|---|---|
| FANG | segment (pure Permian) | Low — pure-play Permian, full boe net continuing ops standard. |
| EOG | consolidated (multi-basin) | Medium — Permian fraction ~40%; need most-recent 10-K segment for scaling. |
| DVN | segment if disclosed, else consolidated | Medium — Delaware Basin emphasis; segment disclosure varies by year. |
| CTRA | consolidated | Medium — formed by Cabot+Cimarex merger 2021, segment reporting changed. |
| OXY | consolidated | Medium — Permian fraction ~30%; large international and Gulf of Mexico ops. |
| MTDR | segment (pure Permian) | Low — pure-play Permian. |
| PR | segment (pure Permian) | Low — formed 2022 from Centennial Resource + Colgate Energy merger; segment is Delaware Basin specific. |
| OVV | consolidated (multi-basin) | High — Permian fraction ~50% but reports Anadarko, Bakken, Montney; segment reporting historically variable. |
| SM | consolidated | Medium — Midland Basin and South Texas Eagle Ford; segment disclosure exists. |
| CRGY | consolidated | High — formed 2021 from Independence Energy + Contango merger; multi-basin (Eagle Ford + Rockies + Permian); Permian fraction may be < 30% historically. |

If actual conformance audit results differ materially from these expectations — particularly if CRGY or OVV fail the 30% Permian threshold or fail label conformance — the universe is reduced and the eligibility table records the dropped names with reasons.

## Sign-off Gate

The label definition is locked in writing before Phase 2 begins. Subsequent changes require a Decision Log revision and a re-run of the eligibility audit.
