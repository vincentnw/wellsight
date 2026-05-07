# Implementation Design — Multi-Agent Satellite-Based Trading System

**Date:** 2026-04-29
**Project:** FIN580 final — Multi-Agent Trading and Investment Systems in the Age of AI
**Direction:** Direction 1 (Multi-Agent Alternative-Data Alpha System)
**Project goal framing:** Innovative thinking + GenAI / agentic-AI design + directional rightness (per project_requirement.md "Final Note"; the system does NOT need to be fully correct, working, or profitable)

This document is the canonical design for the implementation phase. It supersedes earlier ad-hoc decisions in the conversation history. Disagreements between this spec and project_overview.md are resolved in favor of this spec. Decision Log entries in project_overview.md remain as audit trail.

---

## 0. Status Snapshot

**Already complete (Phase 1 preparation, see `/phase1/`):**

- Live WRDS pulls: I/B/E/S `tr_ibes` SAL revenue forecasts (22,449 rows), Compustat `comp.fundq` (276 rows), CRSP daily (13,360 rows through 2024-12-31)
- Coverage audit: all 10 candidate names retained; 186 of 200 firm-quarter cells trade-eligible
- Reference Python modules: `equity_universe.py`, `revenue_forecast.py`, `earnings_dates.py`, `permian_fraction_extractor.py`, `sar_pipeline.py` (scaffold)
- Specs: eligibility schema, revenue pivot addendum, label definition, financial-factor baselines, Agent 4 scope narrowing
- Project overview: 50+ Decision Log entries across 7 review rounds, 18 Pre-Code Action Items

**Implementation phase begins from:**

- Six brainstorming decisions (Section 1.1)
- Six adopted Codex suggestions
- Five tightening items adopted from Codex review of this design (Section 1.2)

---

## 1. Locked Decisions

### 1.1 Brainstorming decisions

| # | Decision | Locked value |
|---|---|---|
| Q1 | Scope | Full multi-agent system + full backtest with synthetic SAR derived from TRC permit/completion records. 5 agents, 10 strategies, 20 quarters, 10 firms (long-only). Real Sentinel-1 ingestion is a stretch goal only. |
| Q2 | LLM provider stack | Hybrid: Qwen 2.5 72B Instruct via HuggingFace Inference API (fallback Qwen 2.5 32B), Llama 3.3 70B via Groq, DeepSeek R1 via Cerebras. Straight Python orchestration; no LangGraph or other framework. |
| Q3 | Implementation order | Slice-by-slice: anchor cell end-to-end first; expand only after all interfaces validate. |
| Q4 | Synthetic SAR realism | TRC + literature-calibrated confusion matrix. Three matrices run as robustness: optimistic, target, pessimistic. |
| Q5 | Anchor slice | FANG Q3 2024 (pure-play Permian, ~21 analysts, no segment-fraction step on first pass). Plus an adverse anchor (Section 9 M1.b) to prevent happy-path validation. |
| Q6 | Paper writing cadence | Parallel: pre-results sections drafted from project_overview.md content during build; Results / Attribution / Discussion / Conclusion drafted after backtest. All pre-results drafting in design-and-hypothesis voice (not implied success). |

### 1.2 Codex suggestions adopted

From four review rounds:
1. (R1) Tighten central claim: "TRC-calibrated synthetic SAR proxy" — paper-text discipline
2. (R1) Point-in-time rule for every Layer 1 input
3. (R1) Multi-confusion-matrix runs as robustness
4. (R1) Anchor slice produces complete final artifact chain — formalized as M1 acceptance criteria
5. (R1) API call budget table before implementation
6. (R1) LLM caching by (prompt_sha, input_json_sha, model_id, model_version, temperature)
7. (R1) Strategies clean of agent code paths — formalized in Section 6 with explicit ablation classification for Strategy 2
8. (R1) Agent 5 constrained decision schema
9. (R2/R3) Round-2 cleanups (SAR validation policy canonical, CRSP 2025 path locked)
10. (R4) Five additional tightening items in Section 1.3

### 1.3 Codex Round-4 tightening adopted

| # | Codex item | Where applied |
|---|---|---|
| 1 | Verify M6/M7 are distinct (no duplicate ablation milestone) | Section 9 — confirmed distinct |
| 2 | Reclassify Strategy 2 as partial-stack ablation, not baseline | Section 6 + 7 — Strategy 2 lives under ablations, not under baselines, in attribution tables |
| 3 | API budget transparency about what the 10,000 includes | Section 8 — explicit per-run breakdown |
| 4 | M1 adverse-case anchor in addition to FANG Q3 2024 | Section 9 M1 |
| 5 | Synthetic SAR aggregation rule + error-dependence + size-confounding | Section 3 — explicit |
| Bonus a | Precise cell-completeness definition for orchestrator | Section 5 |
| Bonus b | Per-component Agent 5 logging (Bull/Bear/Arbiter separate parquet rows) | Section 4 + 5 |
| Bonus c | Paper drafted-during-build voice discipline | Section 10 |

---

## 2. Scope

**In scope:**

- Universe: 10 Permian-focused E&P names — FANG, EOG, DVN, CTRA, OXY, MTDR, PR, OVV, SM, CRGY
- Backtest window: Q1 2021 to Q4 2025 (20 fiscal quarters), 186 trade-eligible firm-quarter cells
- Long-only system, $1M starting capital, 30 bps round-trip transaction cost
- T-14 entry, T+2 exit holding window
- Target variable: revenue surprise vs I/B/E/S consensus (DL #47 — pivot from production volume due to WRDS subscription gap on `tr_ibeskpi`)
- 5 agents: GIS Detection (no LLM), Revenue Forecast (LLM outlook + deterministic numerical core), Consensus Comparison (LLM), News Verification (LLM), Investment Board (3 LLM sub-agents + deterministic sizing)
- 10 strategies in attribution table: Strategy 1 (full agent stack) + 7 deterministic baselines + 2 partial-stack ablations
- Inference: firm-clustered bootstrap, quarter-block bootstrap, three placebo runs, residualization vs XLE+WTI
- Robustness: confusion-matrix sweep (optimistic/target/pessimistic), threshold sweep (5/10/15/20%), regime splits (oil price, drilling cycle)
- Reproducibility: pinned model versions, hash-locked prompts, structured JSON schemas, run manifest, LLM cache, advisory stability check
- Deliverables: 7000-word paper, working repo, 12-slide deck. No live demo (per project requirement, demo is conditional and we are not building a live system in front of judges).

**Out of scope:**

- Live Sentinel-1 SAR ingestion via Google Earth Engine (stretch goal only; not part of headline backtest)
- Wall Street Horizon earnings calendar (not subscribed; using IBES `ANNDATS_ACT` as proxy with documented caveat)
- Production-grade infrastructure (this is a Master's design demonstration, not a hedge fund prototype)
- Git version control (deliberate team decision)
- Operator-level Baker Hughes rig data (paid; out of scope per DL #45 — basin-aggregate substituted)

---

## 3. Synthetic SAR generator

**Purpose:** translate real TRC + NMOCD permit and completion records into the same three-state pad-quarter classification (`newly_active`, `continuously_active`, `idle`) that a real Sentinel-1 detection pipeline would produce. The generator's noise is calibrated to published Sentinel-1 oil-and-gas pad-detection studies. Synthetic SAR is honest data: it is fixed before each run, deterministic given inputs and seed, and Agent 1 runs on its outputs as if they were real classifications.

**File:** `fin580/data/synthetic_sar.py`

### 3.1 Inputs (all point-in-time as of decision date T)

- TRC permit dates for pads attributed to operators in our universe (filter: `permit_filing_date <= T`)
- NMOCD permit dates same rule
- TRC completion records (spud date, completion date) — **subject to a separate point-in-time rule**: only completion records whose **filing date** (not the underlying spud/completion event date) is on or before T are eligible. Completion-record filing lag is typically 30-60 days. Records whose event date is before T but whose filing date is after T are excluded.
- Operator-name attribution at permit filing date (lagged, no later corrections)

### 3.2 Truth mapping (per pad × quarter)

For each pad-quarter cell where the pad is monitored as of T:

| TRC condition (point-in-time) | Truth state |
|---|---|
| Spud event filed in this quarter, before T | `newly_active` |
| Completion + producing status filed before T, no spud this quarter | `continuously_active` |
| No spud or producing status in this or recent (≤2) quarters | `idle` |

### 3.3 Class-conditional confusion matrix (target)

Applied to each pad-quarter independently. Calibrated to published precision/recall for Sentinel-1 pad-construction detection in semi-arid terrain (~78% / 78%). Source citations recorded in `repro/manifest.py`.

| True state | Observed `newly_active` | Observed `continuously_active` | Observed `idle` |
|---|---|---|---|
| `newly_active` | 0.78 (TP) | 0.12 | 0.10 (FN) |
| `continuously_active` | 0.08 | 0.80 (TP) | 0.12 |
| `idle` | 0.05 (FP→active) | 0.10 | 0.85 (TN) |

Three matrices in total:
- **Optimistic**: precision/recall ≈ 0.90 / 0.85
- **Target**: above
- **Pessimistic**: precision/recall ≈ 0.65 / 0.55

Headline backtest uses target. Optimistic and pessimistic feed Robustness Checks (Section 7.4).

### 3.4 Aggregation: pad → firm-quarter (Codex #5)

Per-pad classifications roll up to a firm-quarter signal. The locked rule:

```
n_newly_active(firm, q)        = count of monitored pads classified newly_active
n_continuously_active(firm, q) = count classified continuously_active
n_idle(firm, q)                = count classified idle
total_monitored(firm, q)       = n_newly_active + n_continuously_active + n_idle

# Two complementary signals computed:
absolute_active(firm, q)       = n_newly_active + n_continuously_active
share_active(firm, q)          = absolute_active / total_monitored if total_monitored > 0 else 0
```

Both `absolute_active` and `share_active` are passed to Agent 2. Agent 2's deterministic numerical core uses `absolute_active` (since absolute drilling activity drives production). The `share_active` rate is included in the agent's input dictionary as a context variable so the LLM outlook can comment on whether activity is concentrated or dispersed across the firm's pad portfolio.

### 3.5 Error structure assumption (Codex #5)

**Locked assumption:** confusion-matrix errors are independent and identically distributed (i.i.d.) across pad-quarter cells.

**This is a known simplification.** Real alt-data errors cluster by geography (cloud cover, terrain), operator behavior (consistent fleet types), sensor conditions (orbit and incidence angle), and quarter (seasonal vegetation). The synthetic generator does not model any of these correlation structures.

**Implication for paper claims:** the robustness sweep (target / optimistic / pessimistic confusion matrices) measures sensitivity to **detection accuracy level**, not sensitivity to **realistic spatial or temporal error structure**. The paper's Robustness Checks section names this distinction explicitly. The Discussion section calls it out as a top limitation.

### 3.6 Size-confounding mitigation (Codex #5)

Larger firms have larger pad portfolios, so `absolute_active` mechanically scales with firm size. To avoid downstream performance reflecting size rather than detection insight:

- Agent 2 normalizes the activity signal against the firm's trailing-4-quarter average activity (relative-activity signal) before producing the numerical revenue forecast. Specifically: the deterministic forecast uses `(absolute_active(q) − mean(absolute_active, q-4..q-1))` as the activity-delta input to the production-update calculation, plus the prior production base.
- Inference layer additionally residualizes portfolio returns against firm size (log market cap at T-14) in a sensitivity regression alongside the headline XLE + WTI residualization.

### 3.7 Determinism + reproducibility

- Random seed for each pad-quarter draw = SHA256 prefix of `(ticker, fiscal_quarter_end, pad_id, confusion_matrix_label)`
- Output cached as `runs/<run-id>/synthetic_sar/<ticker>_<quarter>.parquet`
- Manifest records: TRC dump version SHA, NMOCD dump version SHA, completion-record filing-date cutoff date, confusion-matrix label, confusion-matrix SHA, calibration-source citation list

### 3.8 Smoke test for Section 3

Take FANG Q3 2024 inputs, run through generator, validate that:
- Per-pad classifications are deterministic across two runs with the same seed
- Aggregated `share_active` recovers the calibration target ±2 percentage points across 100 quarters of bootstrapped TRC inputs
- Errors are independent across cells (joint-distribution check via χ² test on a random pair sample)

---

## 4. Multi-Agent Architecture

### 4.1 Schemas

All in `fin580/agents/schemas.py` as pydantic models. JSON serialization round-trip required for cache + audit.

```python
class PadClassification(BaseModel):
    pad_id: str
    state: Literal["newly_active", "continuously_active", "idle"]

class Agent1Out(BaseModel):
    ticker: str
    decision_date_T: date
    fiscal_quarter_end: date
    n_newly_active: int
    n_continuously_active: int
    n_idle: int
    absolute_active: int
    share_active: float
    relative_activity_delta: float
    pad_classifications: list[PadClassification]

class Agent2Out(BaseModel):
    ticker: str
    revenue_forecast_usd: float
    components: dict   # {production_boe_d, wti_avg, realized_price_diff, segment_fraction}
    outlook_paragraph: str   # ≤200 words
    key_drivers: list[str]   # max 5

class Agent3Out(BaseModel):
    ticker: str
    our_estimate_usd: float
    consensus_median_usd: float
    consensus_dispersion_usd: float
    n_analysts_at_T_minus_14: int
    divergence_pct: float
    divergence_class: Literal["strong_beat","modest_beat","in_line","modest_miss","strong_miss"]
    confidence: Literal["high","medium","low"]
    reasoning: str   # ≤150 words

class Agent4Out(BaseModel):
    ticker: str
    n_articles_in_window: int
    gdelt_disclosed: bool
    matching_article_ids: list[str]
    conviction_modifier: Literal["none","downgrade_one_tier"]
    reasoning: str   # ≤150 words

class BoardMemberOpinion(BaseModel):
    role: Literal["bull","bear","arbiter"]
    direction: Literal["long","no_trade"]
    confidence: Literal["high","medium","low"]
    key_evidence: list[str]   # max 3 bullets, each must reference an upstream agent (Agent2/3/4)
    counter_evidence: list[str]   # max 3 bullets
    reasoning_short: str   # ≤150 words

class Agent5Out(BaseModel):
    ticker: str
    decision: Literal["long","no_trade"]
    conviction_tier: Literal["high","medium","low","none"]
    final_size_pct: float   # deterministic lookup: high=15, medium=10, low=5, none=0
    bull_opinion: BoardMemberOpinion
    bear_opinion: BoardMemberOpinion
    arbiter_reasoning: str   # ≤300 words
    upstream_agent_summary: dict   # {agent2_decisive: bool, agent3_decisive: bool, agent4_decisive: bool, agent2_weight: float, agent3_weight: float, agent4_weight: float}
```

### 4.2 LLM client and provider routing

`fin580/agents/llm_client.py` exports a single function:

```python
def chat(*, prompt: str, input_json: dict, model_id: str, temperature: float = 0.0) -> dict:
    """Returns parsed JSON response. Cached by (prompt_sha, input_sha, model_id, temperature)."""
```

Provider routing inside `chat`:
- `model_id` starts with `qwen/` → HuggingFace Inference API (fallback Qwen 32B if 72B not on free tier)
- `model_id` starts with `llama-` → Groq
- `model_id` starts with `deepseek-` → Cerebras
- `model_id` starts with `claude-` → reserved for sensitivity tests; not used in headline run

### 4.3 Per-agent assignment

| Agent | LLM (target) | Why |
|---|---|---|
| Agent 1 | None | Computational pad classification; deterministic |
| Agent 2 | Qwen 2.5 72B (HF) | Strong reasoning + JSON; numerical-core-deterministic with LLM outlook |
| Agent 3 | Llama 3.3 70B (Groq) | Best free rate limit; Groq's reasoning quality is sufficient for divergence classification |
| Agent 4 | Llama 3.3 70B (Groq) | Same provider, same prompt template family — reduces cold-start variance |
| Agent 5 Bull | Qwen 2.5 72B (HF) | Diverse model coverage + reasoning |
| Agent 5 Bear | Llama 3.3 70B (Groq) | Provider diversity in adversarial pair |
| Agent 5 Arbiter | DeepSeek R1 (Cerebras) | Reasoning-model-strength; provider diversity |

This assignment supports the diverse-model ablation (DL #50d): re-run with all three Agent 5 sub-agents on Qwen and report performance delta.

### 4.4 Prompts

All loaded from `fin580/agents/prompts/<agent_id>_<role>.txt`. Each prompt:
- Locked before backtest run (file content SHA256 in manifest)
- Specifies output JSON schema verbatim in the prompt body
- Includes a 2-shot example with valid JSON output
- Ends with `Output JSON only, no preamble or postamble.`

Files:
- `agent2_revenue.txt`
- `agent3_consensus.txt`
- `agent4_news.txt`
- `agent5_bull.txt`
- `agent5_bear.txt`
- `agent5_arbiter.txt`

### 4.5 Per-component logging (Codex bonus b)

Each Agent 5 sub-agent's response is persisted as a separate parquet row, not just nested inside `Agent5Out`. The orchestrator writes `runs/<run-id>/strategy_01/agent5_components.parquet` with one row per (ticker, quarter, role) and the full `BoardMemberOpinion` fields plus `key_evidence` exploded into joinable form. Attribution analysis reads this table directly when comparing Bull/Bear/Arbiter contributions.

---

## 5. Orchestrator

**File:** `fin580/agents/orchestrator.py`

### 5.1 Per-cell flow

```python
def run_cell(ticker: str, fiscal_quarter_end: date, run_dir: Path, run_config: RunConfig) -> CellResult:
    decision_date_T = earnings_dates[(ticker, fiscal_quarter_end)] - timedelta(days=14)
    layer1 = load_layer1_inputs(ticker, decision_date_T, fiscal_quarter_end, run_config)

    a1 = agent1.classify(layer1.synthetic_sar)
    persist(a1, run_dir, "agent1")

    a2 = agent2.forecast(a1, layer1)   # numerical core deterministic + LLM outlook call
    persist(a2, run_dir, "agent2")

    a3 = agent3.compare(a2, layer1.ibes_pit_consensus)
    persist(a3, run_dir, "agent3")

    a4 = agent4.verify(a3, layer1.gdelt_articles_pre_T_minus_14)
    persist(a4, run_dir, "agent4")

    a5 = agent5.board_decide(a3, a4, layer1.context_for_board)
    persist(a5, run_dir, "agent5")

    return CellResult(ticker, fiscal_quarter_end, decision=a5.decision, size_pct=a5.final_size_pct, ...)
```

### 5.2 Resumability and cell completeness (Codex bonus a)

A cell is "complete" iff:

1. All five agent JSON files exist at the expected paths
2. Each JSON file parses successfully against its pydantic schema
3. No JSON file contains an `error` field at the top level
4. The cell's CellResult parquet row exists in `cell_results.parquet`

A schema-valid response that the LLM produced under reduced-quality conditions (e.g., after a stricter retry on malformed output) is marked with `low_quality_flag=True` in its agent JSON. Cells with any agent flagged `low_quality_flag=True` are still treated as complete for resumability purposes (so they don't re-fire the API), but they appear separately in `runs/<run-id>/quality_log.csv` and are excluded from the headline backtest unless the run config explicitly opts them in. This addresses the silent-bad-cell concern.

### 5.3 Error handling

| Failure mode | Action |
|---|---|
| HTTP 429 rate limit | Exponential backoff (5s, 30s, 2min, 10min), max 4 retries, then mark cell `error=rate_limit`, skip |
| Network failure | 3 retries with backoff, then mark cell `error=network`, skip |
| Malformed JSON from LLM | 1 retry with stricter `Output JSON only` prompt; if still bad, persist `error=json_parse_failed` with raw output preserved, mark cell `low_quality_flag=True`, set decision to `no_trade` |
| Pydantic validation failure | Same as malformed JSON path |
| Provider returns 5xx | 3 retries with backoff, then mark `error=provider_5xx`, skip |

Per-run aggregate error rate >5% across cells triggers `manifest.warnings += "high_error_rate_<pct>"` and is reported in the paper's Limitations.

### 5.4 Concurrency

Sequential per cell. No intra-cell parallelism (agents depend on prior agents' outputs). Cell-level parallelism would buy throughput but free-tier rate limits on Qwen are the binding constraint, so it would not actually speed up the headline run.

### 5.5 LLM cache (Codex #6)

`fin580/agents/llm_client.py` wraps every API call:

- Cache key: `sha256(prompt_text + canonical_json(input) + model_id + model_version + str(temperature))`
- Cache location: `runs/_global_cache/<key>.json` (symlinked into per-run `runs/<run-id>/llm_cache/`)
- Cache hit returns parsed JSON immediately, logs `cache_hit=True` to the per-cell log
- Cache miss fires the API call; on success the response is parsed, validated against schema, and written to cache
- Cross-run cache reuse is intentional: if the same prompt + input + model is seen again (same cell, different overall run, same confusion matrix), the API call is not repeated

---

## 6. Backtest Harness

**File tree:** `fin580/backtest/`
- `strategies/` — one Python file per strategy; all expose `def signal(ticker: str, decision_date_T: date, run_config: RunConfig) -> TradeDecision`
- `pnl_engine.py`
- `runner.py`

### 6.1 Strategy classification (Codex #2)

Strategy 1 is the headline. Strategies 3-10 are deterministic baselines. Strategy 2 is a **partial-stack ablation**, not a comparable baseline, because it shares orchestration code with Strategy 1.

| ID | Name | Type | LLM? |
|---|---|---|---|
| 1 | Full agent stack | Headline | Yes (5 agents) |
| 2 | Full stack without Agent 4 | **Ablation of Strategy 1** | Yes (4 agents) |
| 3 | Analyst-revision follower | Baseline | No |
| 4 | WTI 3-month momentum | Baseline | No |
| 5 | Baker Hughes Permian rig count | Baseline | No |
| 6 | Equal-weight universe | Baseline | No |
| 7 | XLE buy-and-hold | Baseline | No |
| 8 | Cross-sectional 12-1 momentum | Baseline | No |
| 9 | Value composite | Baseline | No |
| 10 | Quality composite | Baseline | No |

Attribution table presents Strategy 1 vs Strategies 3-10 as the baseline-comparison row, and Strategy 1 vs Strategy 2 + the four other ablations (solo arbiter, no satellite, same-model board, no realized-price diff) as the ablation-attribution row. Strategy 2 is consistently labeled "Ablation: no Agent 4" in all paper tables and slide content.

### 6.2 Strategy implementations (signal logic)

- **3 (analyst-revision)**: sign of 4-week median revenue-consensus revision at T-14, derived from `tr_ibes` panel
- **4 (oil momentum)**: sign of 3-month WTI return at T-14
- **5 (BHI basin)**: sign of 4-week-on-4-week Permian rig count change at T-14
- **6 (equal-weight)**: always long every eligible name
- **7 (XLE buy-hold)**: 100% XLE for full window
- **8 (12-1 momentum)**: rank by trailing 12-1-month total return at T-14, hold top 4
- **9 (value)**: rank by composite (EV/EBITDA, P/B, FCF yield) at T-14, hold top 4
- **10 (quality)**: rank by composite (ROE, D/E, OCF margin) at T-14, hold top 4

Each strategy implementation is intentionally short (~30-60 lines) and contains zero LLM code. Strategies 3-10 are imported only by `runner.py`, never by `agents/*`.

### 6.3 P&L engine

- Entry: ticker close on T-14 (next trading day if weekend/holiday)
- Exit: ticker close on T+2 (earnings date + 2 trading days)
- Returns: total return with dividends reinvested
  - 2021-01-01 to 2024-12-31: CRSP `RET` field
  - 2025-01-01 to 2025-12-31: Yahoo `Adj Close` chained, per locked CRSP-2025 supplement decision (DL #52)
- Position sizing:
  - Strategy 1: per Agent 5's `final_size_pct` (deterministic lookup)
  - Strategy 2: same as Strategy 1 (Agent 5 still emits sizing, just without Agent 4 input)
  - Strategies 3-5: equal-weight among signal-positive names
  - Strategies 6, 7: by definition
  - Strategies 8-10: top-4 equal-weight
- Costs: 30 bps round-trip, applied symmetrically at entry and exit
- Cash sleeve: BIL ETF returns when fewer than 4 names are trade-eligible (Strategy 7 always 100% XLE, no cash sleeve)

### 6.4 Output schema

Per strategy, in `runs/<run-id>/strategy_<NN>/`:
- `trades.parquet`: one row per (ticker, quarter, entry_date, exit_date, gross_return, net_return, position_size_pct, cash_balance_usd)
- `portfolio_pnl.parquet`: per-quarter cumulative portfolio return, Sharpe, max drawdown
- `decisions.parquet`: signal-level decision data including predicted vs actual revenue surprise and hit-rate flag

For Strategy 1 only:
- `agent_outputs/<ticker>_<quarter>_<agent>.json` per agent
- `agent5_components.parquet` per Section 4.5

---

## 7. Inference & Reporting

**File:** `fin580/inference/`

### 7.1 Bootstrap

- **Primary: firm-clustered bootstrap.** Resample 10 firms with replacement, keep all of each firm's trades together. 1,000 iterations. Compute hit rate, mean trade return, Sharpe per iteration.
- **Sensitivity: quarter-block bootstrap.** Resample 20 quarters with replacement. 1,000 iterations.
- **CI:** 95% percentile method.
- **Pre-registered primary test:** revenue-surprise hit rate of Strategy 1 > 50% under firm-clustered bootstrap at 5% level (one-sided).
- **Multiple-testing correction:** Holm-Bonferroni applied to the secondary family (threshold sweep + regime splits + ablations + baseline comparisons).

### 7.2 Placebo runs

| Placebo | Method | Expected result |
|---|---|---|
| Non-Permian universe | Re-run Strategy 1 on RRC, AR, EQT, CHRD, CIVI (Marcellus + Bakken) | Null — Permian-derived synthetic SAR has no information for these names |
| Random-coordinate | Shuffle pad coordinates within Permian boundary (breaks operator mapping) | Null |
| Future-data | Feed Layer 1 inputs dated AFTER each decision date T (intentional forward bias) | Signal degrades or reverses — confirms forward bias is absent from the production pipeline |

### 7.3 Residualization

Per-quarter portfolio returns regressed on contemporaneous `XLE return + WTI return` over the same T-14 to T+2 window (HAC standard errors). Residual alpha = intercept; t-stat reported. Headline performance reported both gross and as residual alpha.

A sensitivity regression additionally controls for log market cap at T-14, addressing the size-confounding concern from Section 3.6.

### 7.4 Robustness

- **Confusion-matrix sweep** (Codex R1 #3): re-run Strategy 1 under target / optimistic / pessimistic confusion matrices. Cache reduces SOME calls (e.g. Agent 4 GDELT calls when pad counts don't change Agent 4's input), but Agent 1's pad-classification counts feed directly into Agent 2 / 3 / 5 inputs, so most downstream calls are genuinely new. Each CM run should be budgeted at ~80-90% of headline-run call volume, not "nearly free."
- **Threshold sweep**: 5/10/15/20% revenue-vs-consensus divergence thresholds.
- **Regime splits**: oil-price high vs low; drilling expansion vs contraction.
- **Site-universe sensitivity**: top-300 monitored pads vs full ~500-1,000 (per DL #25).

### 7.5 Output

Single `runs/<run-id>/inference/` directory:
- `headline_table.parquet`: hit rate, mean return, Sharpe, residual alpha, max DD per strategy with 95% bootstrap CIs
- `regime_split_table.parquet`
- `threshold_sweep_table.parquet`
- `ablation_table.parquet` (Strategies 1 / 2 / four ablations / Strategy 1 in same-model variant)
- `placebo_table.parquet`
- `confusion_matrix_sweep_table.parquet`
- `figures/`: cumulative-return chart, hit-rate bootstrap distribution, residual-alpha histogram, regime-split bar chart

---

## 8. API Budget, Reproducibility Manifest, LLM Caching

### 8.1 API call budget (Codex #5)

**Per-cell call count (Strategy 1):** 6 LLM calls (Agent 2 outlook, Agent 3, Agent 4, Agent 5 Bull, Agent 5 Bear, Agent 5 Arbiter).

**Headline run (target confusion matrix, 186 cells):** 1,116 cell-level calls. Per-provider:
- HF Qwen 72B: 372 (Agent 2 + Agent 5 Bull)
- Groq Llama 70B: 558 (Agent 3 + Agent 4 + Agent 5 Bear)
- Cerebras DeepSeek R1: 186 (Agent 5 Arbiter)

**Full experiment estimated total: ~12,000 LLM calls** (including stability checks and ~5% retries). Per-run breakdown:

| Run | Cells | Calls/cell | Subtotal | Notes |
|---|---|---|---|---|
| Headline (target CM) | 186 | 6 | 1,116 | |
| Optimistic CM | 186 | 6 | 1,116 | |
| Pessimistic CM | 186 | 6 | 1,116 | |
| Ablation: solo arbiter | 186 | 4 | 744 | No Bull, no Bear |
| Ablation: no satellite | 186 | 6 | 1,116 | Agent 1 stubbed all-idle |
| Ablation: same-model board | 186 | 6 | 1,116 | All Agent 5 sub-agents on Qwen |
| Ablation: no realized-price diff | 186 | 6 | 1,116 | |
| Strategy 2 (Agent 4 ablation) | 186 | 5 | 930 | No Agent 4 |
| Placebo: non-Permian | 100 | 6 | 600 | 5 firms × 20 quarters |
| Placebo: random-coord | 186 | 6 | 1,116 | |
| Placebo: future-data | 186 | 6 | 1,116 | |
| **Subtotal (no overhead)** | | | **~11,200** | |
| Stability checks (5-call advisory, 6 agents × 5) | | | 30 | Ignorable |
| Retries (assume ~5%) | | | ~560 | Includes JSON-malformed retries + 429 retries that succeed on 2nd attempt |
| **Total budget** | | | **~12,000** | |

**Cache reduction:** since cache key includes `(prompt_sha, input_sha, model_id, temperature)`, identical inputs across runs are served from cache. Optimistic/pessimistic confusion matrices change Agent 1's pad-count outputs, which propagate into Agent 2's input JSON, so most Agent 2/3/4/5 calls in those runs are genuinely new. But cache is invaluable on retries and prompt iteration during development, where it eliminates 95%+ of duplicate calls.

**Daily limits (free tier):**
- HF Qwen 72B: ~300-1,000/day depending on model popularity. ~3,800 calls assumed across full experiment for Qwen-handled agents (Agent 2 + Agent 5 Bull across 6 runs; placebo cells; same-model-board ablation Bull all on Qwen). With 1,000/day this is ~4 days of clock time. Mitigation: fall back to Qwen 32B if 72B is rate-throttled or not on free tier.
- Groq Llama 70B: ~14,400/day. ~5,500 calls. Single day OK.
- Cerebras DeepSeek R1: free tier varies (typically 1M tokens/day). ~1,100 calls × ~2K tokens each = ~2.2M tokens, may exceed daily; mitigation = run Arbiter calls across 2 days or switch to a Cerebras-hosted alternative.

**Degraded-mode fallback:** if a provider's free tier proves too tight in practice, the same-model-board ablation can be skipped (loses one ablation row in the paper) without affecting the headline, and the Cerebras Arbiter calls can be moved to Groq Llama (loses one provider-diversity claim).

### 8.2 Reproducibility manifest

`runs/<run-id>/manifest.json` per run, capturing:

```json
{
  "run_id": "2026-MM-DD-<run-name>",
  "started_at": "ISO-8601",
  "completed_at": "ISO-8601",
  "code_state": {
    "FINAL_dir_sha": "sha256 of code/ + phase1/ + docs/specs/ + docs/paper/ contents at run start",
    "modules_used": ["fin580.agents.orchestrator", "fin580.backtest.runner", "..."]
  },
  "data_state": {
    "ibes_revenue_panel_sha": "...",
    "compustat_fundq_sha": "...",
    "crsp_daily_sha": "...",
    "yahoo_2025_supplement_pull_date": "...",
    "trc_permits_sha": "...",
    "nmocd_permits_sha": "...",
    "trc_completion_filings_sha": "...",
    "synthetic_sar_seed_function_sha": "...",
    "synthetic_sar_confusion_matrix_label": "target|optimistic|pessimistic",
    "synthetic_sar_confusion_matrix_sha": "..."
  },
  "llm_state": {
    "agent2": {"provider": "huggingface", "model_id": "Qwen/Qwen2.5-72B-Instruct", "model_version_commit": "...", "temperature": 0, "prompt_sha": "...", "stability_check_passed": true},
    "agent3": {"provider": "groq", "model_id": "llama-3.3-70b-versatile", "model_version_id": "...", "temperature": 0, "prompt_sha": "...", "stability_check_passed": true},
    "agent4": {...},
    "agent5_bull": {...},
    "agent5_bear": {...},
    "agent5_arbiter": {...}
  },
  "env": {
    "python_version": "3.12.x",
    "requirements_lock_sha": "...",
    "platform": "darwin"
  },
  "parameters": {
    "threshold_pct": 10,
    "max_position_size_pct": 15,
    "max_names": 8,
    "transaction_cost_bps": 30,
    "starting_capital_usd": 1000000
  },
  "warnings": []
}
```

### 8.3 Stability check (advisory, not gating; Codex weakness #6)

Pre-run, each LLM agent is fired 5 times on a fixed input set:

| Agent | Match criterion | Failure mode |
|---|---|---|
| Agent 2 numerical core | Byte-exact | Bug in deterministic Python — block run |
| Agent 2 outlook | `key_drivers` list intersection ≥ 80%; reasoning text variance documented | Advisory |
| Agent 3 | `divergence_class` + `confidence` identical across 5 calls | Advisory |
| Agent 4 | `gdelt_disclosed` boolean + `matching_article_ids` set identical | Advisory |
| Agent 5 Bull / Bear | `direction` + `confidence` identical | Advisory |
| Agent 5 Arbiter | `decision` + `conviction_tier` identical; `key_evidence` overlap ≥ 60% | Advisory |

Stability check results recorded in manifest. Failures are logged, not blocking, because provider-side nondeterminism is real.

---

## 9. Implementation Milestones (Slice-by-Slice)

### M1 — Anchor slice end-to-end

Two anchor cells, not one, to prevent happy-path validation (Codex #4):

- **M1.a — Clean anchor:** FANG Q3 2024. Pure-play Permian, deep coverage, intuitive expected outcome.
- **M1.b — Adverse anchor:** SM Q1 2023. Mid-cap, multi-basin, modest analyst dispersion. Inputs tuned to be ambiguous: synthetic SAR seeded to produce a borderline `share_active` signal, GDELT window selected to include at least one disclosed-but-ambiguous drilling-related article.

Both must pass:

- `python -m fin580.backtest.runner --strategy 1 --ticker <T> --quarter <Q>` produces all 5 agent JSONs, `cell_results.parquet` row, manifest entry, and 4 cached LLM responses
- Stability check fired for all 4 LLM agents on the clean anchor (advisory only per Section 8.3; results recorded in manifest, failures logged but not gating)
- Re-running the same command takes < 10 seconds on full cache hit
- Adverse anchor surfaces at least one of: `low_quality_flag=True`, `divergence_class=in_line` causing `no_trade`, or `gdelt_disclosed=True` causing one-tier conviction downgrade. Each tested behavior is documented in `runs/<id>/m1_b_adverse_log.md`.

What gets built in M1:
- `fin580/data/synthetic_sar.py`, `ibes_pit.py`, `wti_loader.py`, `gdelt_loader.py`, `trc_permits.py`
- `fin580/agents/schemas.py`, `llm_client.py`, `agent1_gis.py` ... `agent5_board.py`, `orchestrator.py`, all prompt files
- `fin580/repro/manifest.py`, `stability_check.py`
- `fin580/backtest/strategies/s01_full_system.py`, `pnl_engine.py`, `runner.py`

Time budget: 2-3 working sessions.

### M2 — Expand to 10 firms × 1 quarter

Run Strategy 1 over all 10 firms for Q3 2024. Validates Agent 2 segment-fraction handling for multi-basin names (EOG, OXY, OVV, DVN, CTRA, SM, CRGY).

Acceptance: 10 cell_results rows, all valid, < 30 minutes including LLM calls. Manifest captures TRC dump version.

Time budget: 1 working session of code.

### M3 — Full window: 186 eligible cells

Run Strategy 1 over Q1 2021 to Q4 2025. Validates resumability, rate-limit handling, error tolerance.

Acceptance: full cell_results.parquet, < 5% cell-level error rate, resumable across days. Trades parquet has approximately 30-40 long entries per project_overview.md trade-count estimate.

Time budget: 1 working session of code; 1-3 days clock time for LLM calls.

### M4 — Strategies 2-10

All 10 strategies run over the full window. Strategy 7 (XLE buy-hold) sanity-checked against published total return; Strategy 6 (equal-weight) sanity-checked against equal-weighted basket return.

Time budget: 1 working session.

### M5 — Inference layer

Bootstrap, placebo, residualization. Pre-registered primary test result reported.

Time budget: 1 working session.

### M6 — Robustness: confusion-matrix sweep

Re-run Strategy 1 under optimistic + pessimistic confusion matrices. Per Section 7.4 corrected wording: Agent 1's pad-classification counts propagate into Agent 2/3/5 inputs, so most downstream LLM calls are genuinely new. Each CM run is budgeted at ~80-90% of headline-run call volume.

Time budget: 0.5 working session of code; 2-3 days clock time.

### M7 — Ablations

Four ablation runs:
- Solo arbiter (no Bull/Bear)
- Without satellite (Agent 1 stubbed all-idle)
- Same-model board (all Agent 5 sub-agents on Qwen)
- Without realized-price differential

Plus Strategy 2 (Agent 4 ablation, classified per Section 6.1) is run as part of M4 already and contributes to the ablation table here.

Time budget: 0.5 working session of code; 1-2 days clock time.

### M8 — Paper figures + tables

Generate publication-ready figures from inference outputs. Tables auto-populated from parquets via Pandas → Markdown via tabulate.

Time budget: 0.5 working session.

---

## 10. Paper Writing Plan

7,000-word target. 14 sections in `docs/paper/`. Pre-results sections drafted in parallel during M1-M3 from existing project_overview.md content; post-results sections after backtest finishes.

### 10.1 Voice discipline (Codex bonus c)

**Pre-results sections must be written in design-and-hypothesis voice, not implied-success voice.** Examples:

- Bad: "Our multi-agent system extracts alpha from satellite-derived drilling activity..."
- Good: "We design a multi-agent system to test whether a TRC-calibrated synthetic SAR proxy, interpreted through agentic LLM reasoning, can produce risk-adjusted returns above standard financial-factor baselines."

The pre-results draft is reviewed before M5 results land. If the headline backtest underperforms baselines, only the Results / Discussion / Conclusion sections need revision; the framing in earlier sections should already be neutral.

### 10.2 Section plan

| File | Words | Cadence | Source material |
|---|---|---|---|
| 01-abstract.md | 200 | After M8 | After all results |
| 02-introduction.md | 600 | After M3 | project_overview.md "What We Are Building" + "Why This Matters" |
| 03-literature-review.md | 800 | After M3 | New writing — alt-data + multi-agent literature |
| 04-research-gap-hypotheses.md | 400 | After M3 | "Research Gap We Are Addressing" + DL framing |
| 05-data-and-universe.md | 600 | After M2 | "Data Sources" + "Investment Universe" + Phase 1 audit findings |
| 06-multi-agent-architecture.md | 800 | After M1 | Project overview architecture + Section 1, 4 of this design |
| 07-methodology.md | 600 | After M1 | "The Signal We Are Creating" + DL #43 + Section 3 of this design |
| 08-portfolio-construction.md | 300 | After M1 | Agent 5 risk rules |
| 09-backtest-evaluation-design.md | 400 | After M3 | "Backtest Design" + "Robustness Checks" + Section 6 of this design |
| 10-results.md | 800 | After M5 | `runs/<id>/inference/headline_table.parquet` |
| 11-attribution-ablation.md | 600 | After M7 | `ablation_table.parquet` + agent5_components.parquet |
| 12-robustness.md | 500 | After M6 | confusion-matrix sweep + threshold sweep + regime splits |
| 13-discussion-limitations.md | 500 | After M8 | Open Items + Codex deferred concerns + synthetic-SAR caveats + Section 3.5 i.i.d. caveat |
| 14-conclusion.md | 300 | After M8 | New writing |

**Total: ~7,400 words.** Trim 400 words at copy-edit stage.

### 10.3 Format

All sections in `docs/paper/*.md`. Final paper assembled by stitching markdown via Pandoc to PDF. Citations in `docs/paper/references.bib`.

12-slide presentation generated last from final paper content: title, research question, gap, universe, architecture, signal mechanism, baselines, headline result, attribution, robustness, limitations, takeaway.

---

## 11. Repository Structure

```
/Users/vincenw/Documents/FIN580/FINAL/
├── project_overview.md               (existing — Decision Log + design source-of-truth)
├── project_requirement.md            (existing — assignment spec)
├── phase1/                           (existing — Phase 1 specs + raw data outputs)
├── docs/
│   ├── specs/
│   │   └── 2026-04-29-implementation-design.md   (this file)
│   ├── plans/                        (implementation plan from writing-plans skill, populated next)
│   └── paper/                        (14 paper section markdowns, populated during M1-M8)
├── code/
│   ├── phase2/                       (existing — equity_universe, revenue_forecast, earnings_dates, permian_fraction_extractor)
│   ├── phase3/                       (existing — sar_pipeline scaffold)
│   ├── agents/
│   │   ├── schemas.py
│   │   ├── llm_client.py
│   │   ├── prompts/
│   │   ├── agent1_gis.py ... agent5_board.py
│   │   └── orchestrator.py
│   ├── data/
│   │   ├── synthetic_sar.py
│   │   ├── ibes_pit.py
│   │   ├── gdelt_loader.py
│   │   ├── wti_loader.py
│   │   ├── yahoo_supplement.py
│   │   └── trc_permits.py
│   ├── backtest/
│   │   ├── strategies/s01..s10.py
│   │   ├── pnl_engine.py
│   │   └── runner.py
│   ├── inference/
│   │   ├── bootstrap.py
│   │   ├── placebo.py
│   │   └── residualization.py
│   └── repro/
│       ├── manifest.py
│       └── stability_check.py
├── runs/
│   ├── _global_cache/                (LLM cache, cross-run reusable)
│   └── YYYY-MM-DD-<run-name>/
│       ├── manifest.json
│       ├── synthetic_sar/
│       ├── strategy_NN/
│       │   ├── trades.parquet
│       │   ├── portfolio_pnl.parquet
│       │   ├── decisions.parquet
│       │   └── agent_outputs/        (Strategy 1 only)
│       ├── inference/
│       └── llm_cache/                (symlinks into _global_cache)
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

---

## 12. Out-of-Scope Items Explicitly Listed

For audit purposes, items deliberately excluded from this design that could otherwise be reasonably included:

- Live Sentinel-1 SAR ingestion via Google Earth Engine (Phase 3 scaffold exists; not part of headline run)
- Wall Street Horizon earnings calendar (not subscribed; IBES `ANNDATS_ACT` proxy with documented caveat per `fin580/phase2/earnings_dates.py`)
- 10-K Permian-fraction extraction beyond regex hits (29 of 50 entries currently estimates; LLM extraction is a follow-up if time permits, otherwise documented as caveat in paper Limitations)
- Operator-level Baker Hughes rig data (paid; basin-aggregate substituted per DL #45)
- LangGraph or other agent framework (overhead exceeds value for 5 sequential agents per Q2)
- Cell-level parallelism in orchestrator (rate limits make it counterproductive)
- Production-grade monitoring and alerting on the run pipeline
- Multi-tenant or user-account separation in the codebase
- Demo / live walkthrough (project_requirement.md makes demo conditional; we are not building a live system)
- Git version control

---

## 13. Open Questions Tracked

None at the moment of writing. All earlier open items are either resolved or explicitly deferred to a documented follow-up:

- Open Item 1 (I/B/E/S coverage): RESOLVED by live WRDS pull (see `phase1/output/coverage_audit_findings.md`)
- Open Item 2 (SAR detection validation): RELABELED as transparency reporting per DL #29 / DL #48; weak validation does not pivot the project
- 10-K segment LLM extraction: documented as caveat, not blocker
- CRSP 2025 supplementation: LOCKED to Yahoo Finance per DL #52

---

## 14. Sign-off

This document is the canonical implementation design as of 2026-04-29. Changes after sign-off are recorded as a new Decision Log entry in `project_overview.md` plus an addendum in this file.

Next step: superpowers:writing-plans skill to produce the implementation plan from this design.
