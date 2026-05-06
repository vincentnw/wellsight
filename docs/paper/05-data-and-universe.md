# 5. Data and Investment Universe

## 5.1 Universe and trading window

Ten U.S. E&P firms selected on Permian exposure: FANG, EOG, DVN, CTRA, OXY, MTDR, PR, OVV, SM, CRGY. Nine derive ≥30% of trailing-12-month production from the Delaware or Midland sub-basins. CRGY is a known coverage exception (Uinta/Eagle Ford footprint, zero Permian FracFocus records — Agent 1 classifies its cells as idle). Global majors are excluded.

System is **long-only**; below-threshold divergence holds cash in BIL. Headline window **Q1 2019 – Q4 2024** (six full calendar years, 200 firm-quarter cells after corporate-action exclusions), covering pre-COVID, the 2020 collapse and rebound, the 2021–2022 spike, and the 2023–2024 range. Decision date `T = earnings_date − 14 days`; holding window `T-14` entry to `T+2` exit.

## 5.2 Data sources and point-in-time discipline

All sources free-public or via WRDS.

**Equity fundamentals.** IBES Detail-History (`tr_ibes`, `SAL`): active panel at T is estimates with `ANNDATS ≤ T` AND (`REVDATS == ANNDATS` OR `REVDATS > T`); consensus = median. Compustat `comp.fundq` for value/quality baselines lagged to most recent reported quarter as of T. CRSP daily total-return through 2024-12-31; yfinance Adj Close for 2025.

**Permits.** FracFocus bulk CSV filtered to Permian counties and the ten operators (or predecessors after merger): 12,376 completion records. Approximations: completion = JobStartDate, spud = JobStartDate − 60d, permit = spud − 90d; only filings ≤ T eligible. Same data anchors Sentinel-1 pad selection.

**Satellite SAR.** Sentinel-1 RTC VV from Microsoft Planetary Computer via STAC API + cloud-optimised GeoTIFF range-reads. Per cell: 25 representative pads (deduplicated, stratified across active / recently-completed / older); all VV scenes within 365 days ending at T. One STAC search per firm-quarter at union bbox, each scene opened once (~12 hours full-sweep wall-clock). Per-pad caches make re-runs free.

**Other.** EIA weekly WTI spot. EIA-DPR Permian rig counts (May–Dec 2024 carried-forward, documented). GDELT 2.0 DOC API for Agent 4 (prior earnings to T-14). Earnings dates use IBES `ANNDATS_ACT` as proxy for pre-T-14 provability (Wall Street Horizon not subscribed).

## 5.3 Coverage audit

A live IBES coverage audit precedes the backtest. Of 200 nominal cells, 186 are trade-eligible (≥3 analysts at T-14). The 14 exclusions correspond to corporate-action timing: CTRA enters Q3 2021 (Cabot–Cimarex merger), CRGY Q1 2022 (Dec 2021 IPO), PR Q3 2022 (Centennial–Colgate merger).

## 5.4 Reproducibility footprint

Every run writes `manifest.json` recording SHA256 of input CSVs, SAR-mode flag, change-detection thresholds, α, per-agent provider/model identifiers, prompt SHAs, Python version, platform. LLM-call cache is keyed on `(prompt_sha, input_sha, model_id, model_version, temperature)`. Full material in Appendix C–D.
