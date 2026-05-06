# 7. Methodology

## 7.1 The signal chain

From raw radar pixels at FracFocus pad coordinates, through a literature-anchored change-detection rule, through five sequential agents, to a long-only trade decision — anchored on point-in-time information available before each earnings.

## 7.2 Sentinel-1 SAR ingestion

Sentinel-1 RTC imagery (VV only) from Microsoft Planetary Computer via STAC API + cloud-optimised GeoTIFF range-reads. Per cell, 25 representative pads (deduplicated, stratified). ~500m × 500m AOI per pad, **one STAC search per firm-quarter** at union bbox, each scene opened once and clipped to all 25 pad windows from the in-memory raster.

Classification rule, with `cur_db` the target-quarter mean VV and `base_db` the trailing-4Q mean for the same pad:

- **`newly_active`** if `cur_db ≥ base_db + 1.5 dB` AND no FracFocus completion record before T;
- **`continuously_active`** if `cur_db ≥ base_db + 0.5 dB` AND a completion within prior 8 quarters;
- **`idle`** otherwise.

Thresholds (1.5 dB / 0.5 dB) anchored to Ben-David et al. (2021) and Glaeser, Olsen & Welch (2020), not tuned in-sample. Activity normalisation `relative_activity_delta = absolute_active − trailing_4Q_avg` mitigates size confounding.

## 7.3 Point-in-time discipline

FracFocus masked to `JobStartDate ≤ T`. Sentinel-1 scenes filtered to `datetime ≤ T`. IBES consensus is the median of estimates with `ANNDATS ≤ T` AND (`REVDATS == ANNDATS` OR `REVDATS > T`) — the REVDATS filter eliminates the survivorship leak in Anderson & Akbas (2020). GDELT filtered to publish dates ≤ T-14. EIA WTI uses prints available before T. Earnings dates use IBES `ANNDATS_ACT` as documented proxy.

## 7.4 Consensus-anchored revenue forecast

Agent 2's deterministic core overlays the IBES prior:

```
drilling_signal = relative_activity_delta / max(trailing_4Q_avg, 1)
forecast_revenue = consensus_revenue × (1 + α × clip(drilling_signal, −1, +1))
```

α frozen ex ante: **α = 0.10** for the headline, **α = 0.0** as no-satellite ablation. Reframes the question from "did our model beat consensus" (a claim we do not make) to "did the satellite signal justify a bounded, principled disagreement with consensus." Documented fallback model when IBES coverage is unavailable.

## 7.5 Trade-decision logic

Long entry requires Agent 3's `divergence_class` ∈ `{modest_beat (≥ +5%), strong_beat (≥ +15%)}`. Under α = 0.10, max achievable divergence is +10%, so `modest_beat` is the operative signal. Agent 4's `gdelt_disclosed` downgrades conviction one tier. Lookup maps Arbiter tier to size (15% / 10% / 5% / 0%). Agent-3 gate short-circuits to `no_trade` otherwise (Agents 4 and 5 do not run).

Trades enter at the close on T-14 and exit on the second trading day strictly after earnings. Total-return-with-dividends; 30 bps round-trip cost; long-only with 15% per-cell cap.
