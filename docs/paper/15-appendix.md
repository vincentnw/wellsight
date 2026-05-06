# Appendix

## A. Per-trade ledger, Strategy 1, 2019–2024

Long entries in chronological order; net return after 30 bps round-trip cost. Entry/earnings/exit dates and prices are in `runs/inference/strategy01_trades.csv`.

| # | Cell | Size | Tier | Net return | W/L |
|---:|---|---:|:---|---:|:---:|
|  1 | SM 2019-Q2 | 0.05 | low | +2.27% | W |
|  2 | DVN 2019-Q3 | 0.05 | low | +9.42% | W |
|  3 | OVV 2020-Q1 | 0.10 | medium | +16.90% | W |
|  4 | MTDR 2020-Q2 | 0.10 | medium | +4.14% | W |
|  5 | **MTDR 2020-Q3** | 0.10 | medium | **-21.51%** | L |
|  6 | OVV 2021-Q1 | 0.10 | medium | +2.72% | W |
|  7 | SM 2021-Q1 | 0.10 | medium | -5.47% | L |
|  8 | FANG 2021-Q1 | 0.10 | medium | +6.72% | W |
|  9 | OVV 2021-Q2 | 0.10 | medium | -13.72% | L |
| 10 | MTDR 2021-Q2 | 0.10 | medium | -13.36% | L |
| 11 | SM 2021-Q2 | 0.10 | medium | -8.63% | L |
| 12 | FANG 2021-Q2 | 0.10 | medium | +4.11% | W |
| 13 | OXY 2021-Q2 | 0.10 | medium | +2.93% | W |
| 14 | MTDR 2021-Q3 | 0.10 | medium | -0.47% | L |
| 15 | **SM 2021-Q3** | 0.10 | medium | **+24.45%** | W |
| 16 | FANG 2021-Q3 | 0.10 | medium | +2.03% | W |
| 17 | DVN 2021-Q3 | 0.10 | medium | +4.81% | W |
| 18 | OVV 2021-Q3 | 0.10 | medium | -9.29% | L |
| 19 | CTRA 2021-Q3 | 0.10 | medium | +0.49% | W |
| 20 | EOG 2021-Q3 | 0.05 | low | +6.40% | W |
| 21 | OXY 2021-Q3 | 0.10 | medium | +4.24% | W |
| 22 | DVN 2022-Q3 | 0.10 | medium | +1.08% | W |
| 23 | EOG 2022-Q3 | 0.10 | medium | +10.61% | W |
| 24 | SM 2022-Q3 | 0.10 | medium | +12.61% | W |
| 25 | FANG 2022-Q3 | 0.05 | low | +2.50% | W |
| 26 | OXY 2022-Q3 | 0.10 | medium | -1.16% | L |
| 27 | OVV 2022-Q3 | 0.10 | medium | +5.41% | W |
| 28 | DVN 2022-Q4 | 0.05 | low | -12.19% | L |
| 29 | EOG 2022-Q4 | 0.10 | medium | -10.06% | L |
| 30 | OVV 2022-Q4 | 0.05 | low | -6.85% | L |
| 31 | SM 2023-Q1 | 0.10 | medium | -9.73% | L |
| 32 | CTRA 2023-Q1 | 0.10 | medium | -3.04% | L |
| 33 | MTDR 2023-Q2 | 0.10 | medium | -1.41% | L |
| 34 | OVV 2023-Q2 | 0.10 | medium | +15.50% | W |
| 35 | FANG 2023-Q2 | 0.10 | medium | +8.06% | W |
| 36 | SM 2023-Q2 | 0.10 | medium | +9.97% | W |
| 37 | FANG 2023-Q3 | 0.10 | medium | -5.96% | L |
| 38 | CTRA 2023-Q3 | 0.10 | medium | -5.65% | L |
| 39 | OXY 2023-Q4 | 0.10 | medium | +4.82% | W |
| 40 | DVN 2024-Q1 | 0.10 | medium | -2.49% | L |
| 41 | OVV 2024-Q2 | 0.10 | medium | -8.51% | L |
| 42 | FANG 2024-Q2 | 0.10 | medium | -6.80% | L |
| 43 | PR 2024-Q2 | 0.10 | medium | -7.58% | L |
| 44 | SM 2024-Q2 | 0.05 | low | -3.42% | L |
| 45 | MTDR 2024-Q3 | 0.10 | medium | -1.75% | L |
| 46 | CTRA 2024-Q3 | 0.10 | medium | -4.45% | L |
| 47 | SM 2024-Q3 | 0.10 | medium | -6.23% | L |
| 48 | PR 2024-Q3 | 0.10 | medium | +7.43% | W |
| 49 | OVV 2024-Q3 | 0.05 | low | +6.93% | W |
| 50 | OXY 2024-Q3 | 0.10 | medium | +0.88% | W |
| 51 | OVV 2024-Q4 | 0.10 | medium | +1.43% | W |

## B. Signal-confidence score specification

A 0–100 deterministic score composing five 0–20 sub-scores from upstream-agent outputs: (1) SAR activity strength (`share_active`, binned by 0.0/0.15/0.30/0.45/0.60); (2) SAR newness (`n_newly_active / max(n_active, 1)`); (3) QoQ activity delta (`relative_activity_delta`, by sign/magnitude); (4) consensus tightness (inverse dispersion coefficient); (5) analyst panel breadth (binned by 3/6/10/15+). Tier mapping: `≥ 70 high`, `40–70 medium`, `< 40 low`. WTI is excluded so the score and the WTI veto (§11.6) do not double-count. Logged at `runs/inference/signal_confidence.csv`; does not enter H1. The 2021 over-firing pattern (§12.4) — 13 of 16 longs at identical clipped +1.0 signal — is a regime the score's sub-scores cannot rank-order.

## C. Software, data, and computational resources

- **IBES Detail-History / Compustat / CRSP**: WRDS subscription.
- **yfinance Adj Close**: open-source, extends CRSP through 2025.
- **EIA weekly WTI spot** and **EIA-DPR Permian rig count**: EIA public release.
- **FracFocus public bulk CSV**: https://fracfocusdata.org/digitaldownload/FracFocusCSV.zip.
- **Microsoft Planetary Computer Sentinel-1 RTC**: https://planetarycomputer.microsoft.com (free, no auth).
- **GDELT 2.0 DOC API**: https://www.gdeltproject.org/.
- **LLM provider**: OpenAI API — `gpt-4o-mini` for Agents 2/3/4 and Bull/Bear; `gpt-5-mini` for the Arbiter.

## D. Reproducibility

Every run writes `manifest.json` with SHA256 of input CSVs, SAR-mode flag, thresholds (1.5/0.5 dB), trailing-baseline coefficient (0.3), α, per-agent provider/model identifiers, prompt SHAs, Python runtime, and platform. LLM-call cache keyed on `(prompt_sha, input_sha, model_id, provider_model_id, temperature)`. To reproduce: set `FIN580_SAR_MODE=real_sentinel1`, `FIN580_SAR_PADS_PER_OP=25`, execute Strategy 1 over the six yearly windows 2019Q1–2024Q4, then run `python -m fin580.inference.build_evidence_pack`.
