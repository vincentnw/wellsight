# 5. Data and Investment Universe

## 5.1 Universe and trading window

The universe is ten U.S. E&P firms selected on Permian exposure: FANG, EOG, DVN, CTRA, OXY, MTDR, PR, OVV, SM, and CRGY. Nine derive ≥30% of trailing-12-month production from the Delaware or Midland sub-basins. CRGY is retained for completeness but is a known coverage exception — its footprint is concentrated in the Uinta basin and Eagle Ford, so FracFocus returns zero Permian completion records and Agent 1 mechanically classifies its cells as idle. Global majors are excluded.

The system is **long-only**; when divergence is below the long-entry threshold the system holds cash in BIL. The headline window is **Q1 2019 – Q4 2024** (six full calendar years, 200 firm-quarter cells after corporate-action exclusions), covering pre-COVID, the 2020 collapse and rebound, the 2021–2022 spike, and the 2023–2024 range. Trade-decision date `T = earnings_date − 14 days`; holding window `T-14` entry to `T+2` exit.

## 5.2 Data sources and point-in-time discipline

All sources are free-public or available via the user's WRDS subscription.

**Equity fundamentals.** I/B/E/S Detail-History (`tr_ibes`, measure `SAL`) for point-in-time consensus. The active panel at T is the set of estimates with `ANNDATS ≤ T` AND (`REVDATS == ANNDATS` OR `REVDATS > T`); consensus is the median. Compustat `comp.fundq` for value/quality baselines lagged to the most recent reported quarter as of T. CRSP daily total-return prices through 2024-12-31; yfinance Adj Close for 2025.

**Permits.** FracFocus public bulk CSV filtered to Permian counties (Texas Delaware/Midland + New Mexico Eddy/Lea) and the ten operators (or predecessors after merger), yielding 12,376 real completion records. We approximate completion = JobStartDate, spud = JobStartDate − 60 days, permit = spud − 90 days; only permits with filing date ≤ T are eligible. The same data anchors Sentinel-1 pad selection.

**Satellite SAR.** Real Sentinel-1 RTC VV backscatter from Microsoft Planetary Computer via the STAC API plus cloud-optimised GeoTIFF range-reads. Per cell we sample 25 representative pads (deduplicated, stratified across active / recently-completed / older cohorts) and pull all VV scenes within a 365-day window ending at T. The pipeline performs one STAC search per firm-quarter at the union bounding box and opens each scene once (~12 hours wall-clock for the full sweep). Per-pad caches make re-runs essentially free.

**Other.** Real EIA weekly WTI spot. Real EIA-DPR Permian rig counts (May–Dec 2024 carried-forward, documented limitation). GDELT 2.0 DOC API for Agent 4, window = prior earnings to T-14. Earnings dates use IBES `ANNDATS_ACT` as a proxy for pre-T-14 provability (Wall Street Horizon not subscribed).

## 5.3 Coverage audit

A live point-in-time IBES coverage audit precedes the backtest. Of 200 nominal cells, 186 are trade-eligible (≥3 analysts at T-14). The fourteen exclusions correspond to corporate-action timing: CTRA enters Q3 2021 (Cabot–Cimarex merger), CRGY Q1 2022 (Dec 2021 IPO), PR Q3 2022 (Centennial–Colgate merger).

## 5.4 Reproducibility footprint

Every run writes a `manifest.json` recording SHA256 of all input CSVs, the SAR-mode flag, change-detection thresholds, α, per-agent provider/model identifiers, prompt SHAs, Python version, and platform. The LLM-call cache is keyed on `(prompt_sha, input_sha, model_id, model_version, temperature)`. Full reproducibility material is in Appendix C–D.
