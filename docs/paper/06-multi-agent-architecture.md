# 6. Multi-Agent Architecture

Five specialist agents in a sequential pipeline followed by an adversarial debate. Each maps to a distinct role from institutional workflows — alt-data analyst, modelling analyst, sell-side consensus analyst, news analyst, portfolio committee. Agents communicate through pydantic-validated JSON, serving as contract, audit artifact, and unit of attribution.

## 6.1 Agent inventory

**Agent 1 — GIS Detection (no LLM).** Consumes real Sentinel-1 RTC VV backscatter at FracFocus pad coordinates and applies the change-detection rule (§7.2) to produce per-pad `newly_active` / `continuously_active` / `idle` classifications, aggregated per cell into three counts, `share_active`, and `relative_activity_delta` (normalised against a 30%-of-pads baseline). Normalisation isolates *change*, not operator size.

**Agent 2 — Revenue Forecast (deterministic core + LLM outlook).** The forecast `forecast = consensus × (1 + α × clip(drilling_signal, −1, +1))` with α = 0.10 frozen ex ante is computed by Python — never the LLM. The LLM (gpt-4o-mini) reads the deterministic number and writes a qualitative outlook plus key drivers.

**Agent 3 — Consensus Comparison.** Pulls IBES consensus at T-14 and classifies divergence as one of `{strong_beat, modest_beat, in_line, modest_miss, strong_miss}` with a confidence rating. Class, percentage, and confidence are deterministic Python after the LLM call (text only); a schema validator rejects any output where the LLM's class disagrees with the rule.

**Agent 4 — News Verification (LLM, gpt-4o-mini).** Reads GDELT articles between prior earnings and T-14; a positive `gdelt_disclosed` finding downgrades conviction one tier.

**Agent 5 — Investment Board.** Bull and Bear (gpt-4o-mini) each produce a constrained `BoardMemberOpinion`. The Arbiter (gpt-5-mini) consumes both plus the upstream summary and emits the final decision plus a structured `upstream_agent_summary` used for attribution. Size is a fixed lookup from conviction tier.

## 6.2 Coordination

Sequential at the cell level: each `(ticker × fiscal_quarter_end)` runs Agents 1 → 5, with each agent's validated output as the next agent's input. No inter-cell communication.

Two coordination choices matter. First, a **hard divergence-class gate** at Agent 3 short-circuits the cell to `no_trade` whenever divergence is not in `{modest_beat, strong_beat}`; when it fires, Agents 4 and 5 do not run. Second, **conviction-to-size is a fixed lookup** (`high → 15%`, `medium → 10%`, `low → 5%`, `none → 0%`); the Arbiter chooses tier, code chooses size.

## 6.3 Why multi-agent

A single end-to-end LLM call would be simpler and likely produce comparable headline performance. The multi-agent design is justified on three grounds: (i) explicit role separation makes inference inspectable and supports per-trade attribution; (ii) Bull/Bear/Arbiter debate produces structured disagreement a single agent cannot represent, enabling debate value as a distinct ablation; (iii) the deterministic core in Agent 2 separates qualitative interpretation (LLMs' strength) from numerical magnitude (their weakness). Whether these benefits translate to measurable gains is itself an empirical question.
