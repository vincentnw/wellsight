# 6. Multi-Agent Architecture

The system decomposes a single trading decision into five specialist agents arranged in a sequential pipeline followed by an adversarial debate. Each agent represents a distinct role from real institutional workflows — alt-data analyst, modelling analyst, sell-side consensus analyst, news analyst, portfolio committee. Agents communicate through pydantic-validated JSON, which serves as inter-agent contract, audit artifact, and unit of attribution.

## 6.1 Agent inventory

**Agent 1 — GIS Detection (no LLM).** Consumes real Sentinel-1 RTC VV backscatter at FracFocus-derived pad coordinates and applies the change-detection rule (§7.2) to produce per-pad `newly_active` / `continuously_active` / `idle` classifications, aggregated per cell into three counts plus `share_active` and `relative_activity_delta` (normalised against a 30%-of-pads baseline). Normalisation isolates whether activity has *changed*, not whether the operator is large.

**Agent 2 — Revenue Forecast (deterministic core + LLM outlook).** The numerical forecast `forecast = consensus × (1 + α × clip(drilling_signal, −1, +1))` with α = 0.10 frozen ex ante is computed by Python — never by the LLM. The LLM (gpt-4o-mini) reads the deterministic number and writes a qualitative outlook plus key drivers.

**Agent 3 — Consensus Comparison.** Pulls point-in-time IBES consensus at T-14 and classifies divergence as one of `{strong_beat, modest_beat, in_line, modest_miss, strong_miss}` with a confidence rating. Class, percentage, and confidence are deterministic Python after the LLM call (gpt-4o-mini for reasoning text only); a schema validator rejects any output where the LLM's class disagrees with the rule.

**Agent 4 — News Verification (LLM, gpt-4o-mini).** Reads GDELT articles between the prior earnings date and T-14 to determine whether the satellite-detected pattern has already been disclosed in indexed public news. A positive `gdelt_disclosed` finding downgrades conviction one tier.

**Agent 5 — Investment Board (Bull / Bear / Arbiter).** Bull and Bear (gpt-4o-mini) each produce a `BoardMemberOpinion` with a constrained schema. The Arbiter (gpt-5-mini) consumes both opinions plus the upstream summary and emits the final decision plus a structured `upstream_agent_summary` used for attribution. Position size is a fixed lookup from conviction tier to size percentage.

## 6.2 Coordination

The pipeline is sequential at the cell level: each `(ticker × fiscal_quarter_end)` runs Agents 1 → 5, with each agent's pydantic-validated output as the next agent's input. There is no inter-cell communication.

Two coordination choices matter. First, a **hard divergence-class gate** at Agent 3 short-circuits the cell to `no_trade` whenever the divergence class is not in `{modest_beat, strong_beat}`. When the gate fires, Agents 4 and 5 do not run; synthetic `agent4.json` / `agent5.json` files are persisted with `reason = short_circuit_no_beat_divergence` to keep the audit trail intact. Second, **conviction-to-size is a fixed lookup** (`high → 15%`, `medium → 10%`, `low → 5%`, `none → 0%`); the Arbiter chooses tier, code chooses size.

## 6.3 Why multi-agent

A single end-to-end LLM call would be simpler and likely produce comparable headline performance. The multi-agent design is justified on three grounds: (i) explicit role separation makes inference inspectable at every step and supports per-trade attribution; (ii) Bull / Bear / Arbiter debate produces structured disagreement that a single agent cannot represent, enabling debate value as a distinct ablation; (iii) the deterministic numerical core inside Agent 2 cleanly separates "what LLMs are good at" (qualitative interpretation) from "what they are bad at" (numerical magnitude). Whether these benefits translate into measurable performance gains is itself an empirical question.
