# 7. Methodology

## 7.1 The signal chain

The chain runs from raw radar pixels at FracFocus-derived pad coordinates, through a literature-anchored change-detection rule, through five sequential agents, to a long-only trade decision, all anchored on point-in-time information available before each company's earnings.

## 7.2 Sentinel-1 SAR ingestion

Real Sentinel-1 RTC imagery (VV only) is fetched from Microsoft Planetary Computer via the STAC API plus cloud-optimised GeoTIFF range-reads. Per cell we sample 25 representative pads (deduplicated, stratified across active / recently-completed / older cohorts). We define a ~500m × 500m AOI around each pad, perform **one STAC search per firm-quarter** at the union bounding box, and pull every Sentinel-1 acquisition the search returns. Each scene's COG is opened once and clipped to all 25 pad windows from the in-memory raster.

The classification rule, with `cur_db` the target-quarter mean VV and `base_db` the trailing-four-quarter mean for the same pad:

- **`newly_active`** if `cur_db ≥ base_db + 1.5 dB` AND no FracFocus completion record exists before T;
- **`continuously_active`** if `cur_db ≥ base_db + 0.5 dB` AND a completion exists within prior eight quarters;
- **`idle`** otherwise.

Thresholds (1.5 dB / 0.5 dB) are anchored to Ben-David et al. (2021) and Glaeser, Olsen & Welch (2020) and not tuned on 2019–2024. The activity normalisation `relative_activity_delta = absolute_active − trailing_4Q_avg` mitigates size confounding.

## 7.3 Point-in-time discipline

FracFocus records are masked to `JobStartDate ≤ T`. Sentinel-1 scenes filtered to `datetime ≤ T`. IBES consensus from `tr_ibes`: estimates with `ANNDATS ≤ T` AND (`REVDATS == ANNDATS` OR `REVDATS > T`); median across the active panel is the consensus (REVDATS filter eliminates the survivorship leak in Anderson & Akbas 2020). GDELT articles filtered to publish dates ≤ T-14. EIA WTI uses prints publicly available before T. Earnings dates use IBES `ANNDATS_ACT` as a documented proxy.

## 7.4 Consensus-anchored revenue forecast

Agent 2's deterministic core computes the forecast as a satellite-adjusted overlay on the IBES prior:

```
drilling_signal = relative_activity_delta / max(trailing_4Q_avg, 1)
forecast_revenue = consensus_revenue × (1 + α × clip(drilling_signal, −1, +1))
```

α is frozen ex ante: **α = 0.10** for the headline, **α = 0.0** as the no-satellite ablation. This reframes the empirical question from "did our model beat consensus" — a claim we do not make — to "did the satellite signal justify a bounded, principled disagreement with consensus." When IBES coverage is unavailable, a documented fallback model is used and flagged in the manifest.

## 7.5 Trade-decision logic

A long entry requires Agent 3's `divergence_class` to be `modest_beat` (≥ +5%) or `strong_beat` (≥ +15%). Under the α = 0.10 cap the maximum achievable divergence is +10%, so `modest_beat` is the operative entry signal. Agent 4's `gdelt_disclosed` finding downgrades conviction one tier. The lookup maps Arbiter tier to size (15% / 10% / 5% / 0%). The Agent-3 gate short-circuits to `no_trade` whenever divergence is not in `{modest_beat, strong_beat}`; when it fires, Agents 4 and 5 do not run.

Trades enter at the close on T = earnings_date − 14 calendar days and exit on the second trading day strictly after earnings. Returns are total-return-with-dividends; round-trip cost 30 bps; long-only with 15% per-cell cap.
