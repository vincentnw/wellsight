# 7. Methodology

## 7.1 The signal chain

The system tests whether a free, reproducible alternative-data signal — real Sentinel-1 SAR drilling-activity classifications produced by change-detection on cloud-optimised radar imagery — can produce a tradable revenue-surprise prediction for ten Permian-focused U.S. oil producers when interpreted through a multi-agent LLM workflow. The chain of inference proceeds from raw radar pixels at FracFocus-derived pad coordinates, through a literature-anchored change-detection rule, through five sequential agents, to a long-only trade decision, all anchored on point-in-time information available before each company's earnings announcement.

## 7.2 Sentinel-1 SAR ingestion

We process actual Sentinel-1 RTC (Radiometric Terrain Corrected) imagery — VV polarisation only — fetched from Microsoft Planetary Computer (https://planetarycomputer.microsoft.com), free of charge with no authentication, via the STAC API plus cloud-optimised GeoTIFF range-reads. For each (firm × fiscal quarter) cell we sample 25 representative pads, deduplicated by `(pad_id, rounded coordinates)` so that the panel is 25 distinct radar-target locations rather than 25 FracFocus rows that may include duplicates. The pads are stratified across the active-drilling, recently-completed, and older-completion cohorts of the operator's FracFocus history. We define a ~500m × 500m AOI around each pad's lat/lon, perform one STAC search per firm-quarter at the union bounding box of all 25 pads, and pull every Sentinel-1 acquisition returned by that search. Each scene's COG is opened once per firm-quarter and clipped to all 25 pad windows from the in-memory raster — yielding up to 25 mean-VV backscatter values per scene (in linear scale, converted to dB), with off-scene clips skipped. Per pad-year we typically obtain ~50 acquisitions, producing a per-pad time series.

The classification rule is a literature-anchored change-detection over the per-pad VV time series. Let `cur_db` be the mean VV backscatter (in dB) over the target quarter, and let `base_db` be the trailing-four-quarter mean of VV for the same pad. We classify:

- *newly_active* if `cur_db ≥ base_db + 1.5 dB` AND the pad has no completion record in FracFocus before T (a fresh +1.5 dB jump on an as-yet-uncompleted pad is the radar signature of cleared land + heavy drilling equipment);
- *continuously_active* if `cur_db ≥ base_db + 0.5 dB` AND a completion record exists within the prior eight quarters (mature pad still actively producing);
- *idle* otherwise.

Threshold values (1.5 dB activation, 0.5 dB sustained) are anchored to peer-reviewed Permian-pad SAR change-detection literature (Ben-David et al. 2021; Glaeser, Olsen & Welch 2020) and are not tuned on the 2019-2024 sample. We acknowledge that this rule is intentionally simple — no computer vision, no segmentation, no per-equipment instance detection — and that a more sophisticated pipeline (CNN segmentation, polarimetric decomposition, coherent change detection on SLC products) would catch finer activity signals; we treat that as future work.

The relative-activity normalization (`relative_activity_delta = absolute_active − trailing_4Q_avg`, where `trailing_4Q_avg` is computed from cached prior-quarter SAR aggregates when available, falling back to 30% of pads sampled — anchored to long-run Permian-basin pads-actively-drilling share) is applied to mitigate size confounding: larger operators mechanically have more pads in their FracFocus history, so without normalisation they would appear systematically more active.

## 7.3 Point-in-time discipline

Every Layer-1 input has an explicit point-in-time rule. FracFocus completion records are masked so that only disclosures whose `JobStartDate` is on or before the decision date `T = earnings_date − 14 days` are visible (we approximate spud_filing_date = JobStartDate − 60 days, permit_filing_date = spud − 90 days, since FracFocus only reports the frac-job timestamp). Sentinel-1 RTC scenes are filtered by acquisition `datetime ≤ T`. IBES revenue consensus is reconstructed from the I/B/E/S Detail-History file `tr_ibes`: each analyst's most recent revenue forecast with `ANNDATS ≤ T` AND (`REVDATS == ANNDATS` (un-revised) OR `REVDATS > T` (still active at T)) is retained, and the median across the active panel is the point-in-time consensus (the REVDATS filter eliminates the survivorship leak documented by Anderson & Akbas 2020). GDELT articles are filtered to those with publish dates strictly on or before T-14, and the cached read-path defensively re-applies the cutoff. EIA WTI prices use prints publicly available before T. Earnings dates are sourced from IBES `ANNDATS_ACT` as a documented proxy for true pre-T-14 provability (Wall Street Horizon access not subscribed).

## 7.4 Consensus-anchored revenue forecast

Agent 2's deterministic numerical core computes the revenue forecast as a satellite-adjusted overlay on the IBES consensus prior, not as an independent absolute estimate. Specifically:

```
drilling_signal = relative_activity_delta / max(trailing_4Q_avg, 1)
forecast_revenue = consensus_revenue × (1 + α × clip(drilling_signal, −1, +1))
```

The calibration parameter α is frozen before any results are observed: `α = 0.10` for the headline run and `α = 0.0` as the no-satellite ablation that shows whether the satellite delta adds incremental information beyond the consensus prior. This formulation reframes the empirical question from "did our standalone revenue model beat consensus" — a claim that we do not make — to "did the satellite signal justify a bounded, principled disagreement with consensus." When IBES coverage is unavailable for a quarter, the documented fallback model (production-base × wells-per-pad × type-curve × WTI × differential) is used and flagged in the reproducibility manifest.

## 7.5 Trade-decision logic

A long entry requires Agent 3's `divergence_class` to be `modest_beat` (forecast ≥ +5% above consensus) or `strong_beat` (≥ +15%). Under the α = 0.10 cap, the maximum achievable divergence is +10%, so `strong_beat` cannot fire by construction; modest-beat is the operative entry signal. Agent 4's `gdelt_disclosed` finding downgrades the conviction tier by one step. Agent 5's Arbiter selects the final conviction tier (`high`, `medium`, `low`, or `none`); the lookup table maps tiers to position sizes (15%, 10%, 5%, 0%). The Agent-3 gate short-circuits the cell to `no_trade` whenever the divergence class is not in `{modest_beat, strong_beat}` (DL #61); when this gate fires, Agents 4 and 5 do not run, so the LLM cannot override the deterministic classification rule.

Trades are entered at the closing price on T = earnings_date − 14 calendar days and exited on the second trading day strictly after earnings (counted in trading-day terms, not calendar days, per `_exit_price()` in `fin580/inference/pnl.py`). All returns are total-return-with-dividends: CRSP daily through 2024-12-31, yfinance Adj Close for 2025 dates. Transaction costs are 30 basis points round-trip. The portfolio is long-only with a per-cell position cap of 15% (the conviction-tier-to-size lookup is `high → 15%`, `medium → 10%`, `low → 5%`, `none → 0%`). Cells where the multi-agent system declines to fire (Agent-3 short-circuit, or Agent-5 Arbiter votes `no_trade`) hold cash for that quarter rather than entering an alternative position.
