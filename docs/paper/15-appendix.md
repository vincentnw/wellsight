# Appendix

## A. Per-trade ledger, Strategy 1, 2019–2024

Each row is a single long entry. Entry price = closing price on T-14, exit price = closing price on the second trading day after the earnings announcement. Net return is after the 30 bps round-trip transaction cost.

| # | Cell | Size | Entry T-14 | Earnings | Exit T+2 | Net return | Outcome |
|---:|---|---:|---|---|---|---:|:---:|
|  1 | FANG 2019-Q2 | 0.05 | \$104.44 (2019-07-23) | 2019-08-06 | \$95.20 (2019-08-08) | −9.15% | ✗ |
|  2 | FANG 2019-Q3 | 0.10 | \$85.69 (2019-10-22) | 2019-11-05 | \$75.56 (2019-11-07) | −12.12% | ✗ |
|  3 | **SM 2020-Q1** | 0.10 | \$1.73 (2020-04-15) | 2020-04-29 | \$3.31 (2020-05-01) | **+91.03%** | ✓ |
|  4 | OVV 2020-Q1 | 0.10 | \$5.00 (2020-04-23) | 2020-05-07 | \$5.86 (2020-05-09) | +16.90% | ✓ |
|  5 | MTDR 2020-Q3 | 0.05 | \$8.77 (2020-10-13) | 2020-10-27 | \$6.91 (2020-10-29) | −21.51% | ✗ |
|  6 | OVV 2021-Q1 | 0.10 | \$24.21 (2021-04-15) | 2021-04-29 | \$24.94 (2021-05-01) | +2.72% | ✓ |
|  7 | MTDR 2021-Q2 | 0.10 | \$35.54 (2021-07-13) | 2021-07-27 | \$30.90 (2021-07-29) | −13.36% | ✗ |
|  8 | MTDR 2021-Q3 | 0.10 | \$42.39 (2021-10-12) | 2021-10-26 | \$42.32 (2021-10-28) | −0.47% | ✗ |
|  9 | FANG 2021-Q3 | 0.10 | \$109.26 (2021-10-18) | 2021-11-01 | \$111.81 (2021-11-03) | +2.03% | ✓ |
| 10 | OVV 2021-Q3 | 0.10 | \$39.27 (2021-10-19) | 2021-11-02 | \$35.74 (2021-11-04) | −9.29% | ✗ |
| 11 | CTRA 2021-Q3 | 0.10 | \$21.41 (2021-10-20) | 2021-11-03 | \$21.58 (2021-11-05) | +0.49% | ✓ |
| 12 | OXY 2021-Q3 | 0.10 | \$32.80 (2021-10-21) | 2021-11-04 | \$34.29 (2021-11-06) | +4.24% | ✓ |
| 13 | DVN 2021-Q4 | 0.10 | \$52.56 (2022-02-01) | 2022-02-15 | \$55.25 (2022-02-17) | +4.82% | ✓ |
| 14 | MTDR 2022-Q3 | 0.10 | \$60.09 (2022-10-11) | 2022-10-25 | \$66.04 (2022-10-27) | +9.60% | ✓ |
| 15 | DVN 2022-Q3 | 0.10 | \$69.77 (2022-10-18) | 2022-11-01 | \$70.73 (2022-11-03) | +1.08% | ✓ |
| 16 | OVV 2022-Q4 | 0.05 | \$48.38 (2023-02-13) | 2023-02-27 | \$45.21 (2023-03-01) | −6.85% | ✗ |
| 17 | CTRA 2023-Q1 | 0.10 | \$25.56 (2023-04-20) | 2023-05-04 | \$24.86 (2023-05-06) | −3.04% | ✗ |
| 18 | DVN 2023-Q2 | 0.10 | \$50.51 (2023-07-18) | 2023-08-01 | \$50.83 (2023-08-03) | +0.33% | ✓ |
| 19 | OVV 2023-Q2 | 0.10 | \$39.80 (2023-07-13) | 2023-07-27 | \$46.09 (2023-07-29) | **+15.50%** | ✓ |
| 20 | EOG 2023-Q3 | 0.10 | \$136.23 (2023-10-19) | 2023-11-02 | \$126.42 (2023-11-04) | −7.50% | ✗ |
| 21 | FANG 2023-Q3 | 0.10 | \$165.32 (2023-10-23) | 2023-11-06 | \$155.97 (2023-11-08) | −5.96% | ✗ |
| 22 | FANG 2024-Q2 | 0.10 | \$204.68 (2024-07-22) | 2024-08-05 | \$191.38 (2024-08-07) | −6.80% | ✗ |
| 23 | FANG 2024-Q3 | 0.10 | \$182.41 (2024-10-21) | 2024-11-04 | \$183.62 (2024-11-06) | +0.36% | ✓ |

## B. Signal-confidence score specification

A 0–100 deterministic score composes five 0–20 sub-scores from inputs already exposed by upstream agents:

1. **SAR activity strength** — `share_active`, binned 0/5/10/15/20 by 0.0/0.15/0.30/0.45/0.60 thresholds.
2. **SAR signal newness** — `n_newly_active / max(n_active, 1)`, binned 0/5/10/15/20.
3. **QoQ activity delta** — `relative_activity_delta`, binned by sign and magnitude (above-baseline gets higher score).
4. **Consensus tightness** — inverse coefficient of dispersion of the active-analyst panel; tighter = higher score.
5. **Analyst panel breadth** — `n_analysts_at_T_minus_14`, binned 0/5/10/15/20 by 3/6/10/15+ analysts.

Tier mapping: `score ≥ 70 → high`, `40 ≤ score < 70 → medium`, `< 40 → low`. WTI/oil-regime is intentionally excluded so that the score and the WTI veto (§11.6) do not double-count.

**Distribution across 200 cells:** 97 low, 91 medium, 12 high. **Distribution across the 23 long trades:** 5 high (scores 72–80), 18 medium (scores 48–72), 0 low. **Hit rate by tier:** high 3W / 2L (60.0%, n=5); medium 9W / 9L (50.0%, n=18). The directional pattern is in the predicted direction but the gap is within bootstrap noise; the score is logged for transparency about input-quality variation and does not enter H1 or any pre-registered test.

## C. Software, data, and computational resources

- **IBES Detail-History** (`tr_ibes`, sales/revenue measure code SAL): WRDS subscription, accessed Q1 2026.
- **Compustat quarterly fundamentals** (`comp.fundq`): WRDS subscription.
- **CRSP daily stock files**: WRDS subscription, through 2024-12-31.
- **yfinance Adj Close**: open-source, used to extend CRSP through 2025.
- **EIA weekly WTI spot**: U.S. Energy Information Administration public release.
- **EIA Drilling Productivity Report Permian rig count**: EIA public release.
- **FracFocus public bulk CSV**: https://fracfocusdata.org/digitaldownload/FracFocusCSV.zip.
- **Microsoft Planetary Computer Sentinel-1 RTC**: https://planetarycomputer.microsoft.com (free, no auth).
- **GDELT 2.0 DOC API**: https://www.gdeltproject.org/.
- **Texas Railroad Commission and New Mexico Oil Conservation Division** permit data: public records via state portals.
- **LLM provider**: OpenAI API. `gpt-4o-mini` for Agent 2 outlook, Agent 3 reasoning text, Agent 4 verification, Agent 5 Bull/Bear; `gpt-5-mini` for the Agent 5 Arbiter.

## D. Reproducibility

Every backtest run writes a `manifest.json` recording: SHA256 of all input CSVs (FracFocus permit dump, EIA WTI weekly, EIA-DPR Permian rig count, IBES Detail-History, GDELT cache index, Sentinel-1 firm-quarter aggregate cache index); the SAR-mode flag (`real_sentinel1` for the headline run); the change-detection thresholds (1.5 dB activation, 0.5 dB sustained); the trailing-baseline coefficient (0.3); the consensus-anchor `α`; the per-agent provider and model identifier (and version where the provider exposes it); prompt-file SHAs; the Python version; and the platform identifier.

The LLM-call cache is keyed on `(prompt_sha, input_sha, model_id, model_version, temperature)` and is included in the supplementary materials; combined with the per-pad Sentinel-1 backscatter cache (`phase1/output/sentinel1_cache/`), re-execution is essentially free up to provider determinism limits.

To reproduce the headline run:

```bash
export FIN580_SAR_MODE=real_sentinel1
export FIN580_SAR_PADS_PER_OP=25
# Execute Strategy 1 over the six yearly windows from 2019Q1-2019Q4 through 2024Q1-2024Q4,
# then regenerate the inference rollups from those yearly run directories.
```

The per-trade ledger, manifest, and caches are sufficient for an external reviewer to spot-check any trade. Caches and manifests are available on request.
