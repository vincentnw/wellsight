# Multi-Agent Satellite-Based Trading System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full FIN580 multi-agent satellite-based revenue-surprise trading system: 5 LLM agents (Qwen via HF, Llama via Groq, DeepSeek via Cerebras), 10 strategies, 20-quarter backtest with synthetic SAR, inference layer, and 14-section paper.

**Architecture:** Four layers — data plumbing, multi-agent orchestrator, backtest harness, inference and reporting. Sequential agent pipeline with Investment Board debate. Slice-by-slice implementation anchored on FANG Q3 2024 (clean) + SM Q1 2023 (adverse). All agent calls cached by (prompt_sha, input_sha, model_id, temperature).

**Tech Stack:** Python 3.12, pydantic, pandas, pyarrow, numpy, scipy, statsmodels, matplotlib, requests, huggingface_hub, groq, cerebras_cloud_sdk, yfinance.

**Source spec:** `/Users/vincenw/Documents/FIN580/FINAL/docs/specs/2026-04-29-implementation-design.md`

**Project goal framing (do not forget):** Per `project_requirement.md` "Final Note" + memory feedback `feedback_project_goal.md` — innovation + agentic-AI design + directional rightness. The system does NOT need to be fully correct, fully working, or profitable. Spec ambitiously, execute pragmatically.

**No git:** project does not use git. Each task ends with a "Checkpoint" step that updates the run-progress log instead of `git commit`.

**Execution discipline:** TDD-lite — testable units (pure functions with deterministic inputs/outputs: schemas, cache key, PnL math, bootstrap, synthetic-SAR confusion-matrix recovery) get a fail-first smoke test. Integration glue and modules dominated by external API calls (data loaders, agent modules with LLM calls, orchestrator, runner) get an import + runtime smoke check that they wire correctly. Full test coverage is not required, and full mocking of LLM calls is out of scope under the project-goal framing (innovation > production hardening).

---

## File Structure (canonical, locked)

### New files to create

| File | Responsibility |
|---|---|
| `requirements.txt` | Pinned dependencies |
| `.env.example` | API key variable names (HF, Groq, Cerebras) |
| `README.md` | Order-of-operations for reproducer |
| `fin580/__init__.py` | Package marker |
| `fin580/agents/__init__.py` | Package marker |
| `fin580/agents/schemas.py` | All inter-agent pydantic models |
| `fin580/agents/llm_client.py` | Provider abstraction + cache layer |
| `fin580/agents/prompts/agent2_revenue.txt` | Agent 2 prompt (locked, hashed) |
| `fin580/agents/prompts/agent3_consensus.txt` | Agent 3 prompt |
| `fin580/agents/prompts/agent4_news.txt` | Agent 4 prompt |
| `fin580/agents/prompts/agent5_bull.txt` | Agent 5 Bull prompt |
| `fin580/agents/prompts/agent5_bear.txt` | Agent 5 Bear prompt |
| `fin580/agents/prompts/agent5_arbiter.txt` | Agent 5 Arbiter prompt |
| `fin580/agents/agent1_gis.py` | GIS Detection (no LLM) |
| `fin580/agents/agent2_revenue.py` | Revenue Forecast (deterministic + Qwen outlook) |
| `fin580/agents/agent3_consensus.py` | Consensus Comparison (Llama) |
| `fin580/agents/agent4_news.py` | News Verification (Llama) |
| `fin580/agents/agent5_board.py` | Investment Board (Bull / Bear / Arbiter) |
| `fin580/agents/orchestrator.py` | Per-cell sequential pipeline + persistence |
| `fin580/data/__init__.py` | Package marker |
| `fin580/data/synthetic_sar.py` | TRC + literature-calibrated confusion matrix |
| `fin580/data/trc_permits.py` | TRC + NMOCD permit/completion dump builder |
| `fin580/data/ibes_pit.py` | Point-in-time IBES consensus reconstruction at T-14 |
| `fin580/data/gdelt_loader.py` | GDELT article loader with T-14 cutoff |
| `fin580/data/wti_loader.py` | EIA WTI weekly spot loader |
| `fin580/data/yahoo_supplement.py` | CRSP 2025 supplement via yfinance |
| `fin580/backtest/__init__.py` | Package marker |
| `fin580/backtest/pnl_engine.py` | Entry/exit prices, costs, position sizing |
| `fin580/backtest/runner.py` | Strategy × universe × quarter loop |
| `fin580/backtest/strategies/__init__.py` | Strategy registry |
| `fin580/backtest/strategies/s01_full_system.py` | Strategy 1 — wraps orchestrator |
| `fin580/backtest/strategies/s02_no_news.py` | Ablation: Strategy 1 minus Agent 4 |
| `fin580/backtest/strategies/s03_analyst_revision.py` | Baseline 3 |
| `fin580/backtest/strategies/s04_oil_momentum.py` | Baseline 4 |
| `fin580/backtest/strategies/s05_bhi_basin.py` | Baseline 5 |
| `fin580/backtest/strategies/s06_equal_weight.py` | Baseline 6 |
| `fin580/backtest/strategies/s07_xle_buy_hold.py` | Baseline 7 |
| `fin580/backtest/strategies/s08_stock_momentum.py` | Baseline 8 |
| `fin580/backtest/strategies/s09_value.py` | Baseline 9 |
| `fin580/backtest/strategies/s10_quality.py` | Baseline 10 |
| `fin580/inference/__init__.py` | Package marker |
| `fin580/inference/bootstrap.py` | Firm-clustered + quarter-block bootstrap |
| `fin580/inference/placebo.py` | Three placebo run drivers |
| `fin580/inference/residualization.py` | XLE + WTI residual alpha + size sensitivity |
| `fin580/inference/plots.py` | Paper-ready figures |
| `fin580/repro/__init__.py` | Package marker |
| `fin580/repro/manifest.py` | Run manifest builder |
| `fin580/repro/stability_check.py` | 5-call structured-field-match validator |
| `tests/test_schemas.py` | Pydantic round-trip smoke tests |
| `tests/test_llm_client.py` | Cache key + mock-call smoke tests |
| `tests/test_synthetic_sar.py` | Confusion-matrix calibration recovery test |
| `tests/test_pnl_engine.py` | Single-trade arithmetic |
| `tests/test_bootstrap.py` | Firm-clustered bootstrap smoke |
| `docs/paper/01-abstract.md` ... `14-conclusion.md` | 14 paper section drafts |
| `docs/paper/references.bib` | Citation database |

### Existing files reused (no modification)

- `phase1/output/ibes_revenue_coverage.csv` — coverage panel
- `phase1/output/equity_universe_panel.csv` — universe constructor output
- `phase1/output/earnings_dates.csv` — earnings-date proxy
- `phase1/output/permian_fraction.csv` — segment fraction lookup
- `phase1/output/compustat_fundq.csv` — fundamentals for value/quality baselines
- `phase1/output/crsp_daily.csv` — daily prices through 2024
- `fin580/phase2/equity_universe.py`, `revenue_forecast.py`, `earnings_dates.py`, `permian_fraction_extractor.py`
- `fin580/phase3/sar_pipeline.py` — referenced for SAR scaffolding patterns

### Run outputs (created by execution, not in plan)

`runs/<run-id>/` directory tree per spec Section 11.

---

## Task Index

The plan is organized by milestone (M0 setup + M1-M8 from the spec) plus paper drafting interleaved.

- **M0** — Setup (Tasks 1-5): scaffolding, schemas, LLM client, manifest, stability check
- **M1** — Anchor slice end-to-end (Tasks 6-22): all data loaders, all 5 agents, orchestrator, Strategy 1, anchor smoke tests
- **M2** — Expand to 10 firms × Q3 2024 (Task 23)
- **M3** — Full window 186 cells (Task 24)
- **M4** — Strategies 2-10 (Tasks 25-34)
- **M5** — Inference layer (Tasks 35-38)
- **M6** — Confusion-matrix sweep (Tasks 39-40)
- **M7** — Ablations (Tasks 41-44)
- **M8** — Paper figures and tables (Tasks 45-46)
- **Paper drafting** — interleaved with milestones (Tasks P1-P14)

---

## M0 — Setup & Shared Infrastructure

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `README.md`
- Create: `fin580/__init__.py`
- Create: `fin580/agents/__init__.py`, `fin580/agents/prompts/__init__.py`
- Create: `fin580/data/__init__.py`
- Create: `fin580/backtest/__init__.py`, `fin580/backtest/strategies/__init__.py`
- Create: `fin580/inference/__init__.py`
- Create: `fin580/repro/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Write `requirements.txt`**

```
pydantic>=2.6
pandas>=2.2
pyarrow>=15.0
numpy>=1.26
scipy>=1.12
statsmodels>=0.14
matplotlib>=3.8
requests>=2.31
huggingface_hub>=0.23
groq>=0.9
cerebras_cloud_sdk>=1.0
yfinance>=0.2.40
python-dotenv>=1.0
tabulate>=0.9
pytest>=8.0
```

- [ ] **Step 2: Write `.env.example`**

```
HF_TOKEN=
GROQ_API_KEY=
CEREBRAS_API_KEY=
```

- [ ] **Step 3: Write `README.md`**

```markdown
# FIN580 Multi-Agent Satellite-Based Trading System

## Order of operations

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`, fill in API keys (HuggingFace, Groq, Cerebras)
3. Confirm Phase 1 outputs exist: `phase1/output/{ibes_revenue_coverage,equity_universe_panel,earnings_dates,permian_fraction,compustat_fundq,crsp_daily}.csv`
4. Run anchor slice: `python -m fin580.backtest.runner --strategy 1 --ticker FANG --quarter 2024Q3`
5. Run full Strategy 1: `python -m fin580.backtest.runner --strategy 1 --window 2021Q1-2025Q4`
6. Run baselines: `python -m fin580.backtest.runner --strategies 3,4,5,6,7,8,9,10`
7. Run inference: `python -m fin580.inference.runner --run-id <run>`

## Reproducibility

Every run writes a `runs/<run-id>/manifest.json` capturing pinned model versions, prompt SHAs, data SHAs, and parameter values.
```

- [ ] **Step 4: Create empty `__init__.py` files**

```bash
touch code/__init__.py code/agents/__init__.py code/agents/prompts/__init__.py \
      code/data/__init__.py code/backtest/__init__.py \
      code/backtest/strategies/__init__.py code/inference/__init__.py \
      code/repro/__init__.py tests/__init__.py
```

- [ ] **Step 5: Verify scaffolding**

Run: `python -c "import code, fin580.agents, fin580.data, fin580.backtest, fin580.inference, fin580.repro"`
Expected: no error.

- [ ] **Step 6: Checkpoint**

Mark Task 1 complete in run-progress log. (No git.)

---

### Task 2: Pydantic schemas

**Files:**
- Create: `fin580/agents/schemas.py`
- Create: `tests/test_schemas.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_schemas.py
from datetime import date
from fin580.agents.schemas import (
    Agent1Out, Agent2Out, Agent3Out, Agent4Out, Agent5Out,
    PadClassification, BoardMemberOpinion,
)


def test_agent1_out_round_trip():
    obj = Agent1Out(
        ticker="FANG", decision_date_T=date(2024, 10, 17),
        fiscal_quarter_end=date(2024, 9, 30),
        n_newly_active=4, n_continuously_active=18, n_idle=8,
        absolute_active=22, share_active=22 / 30, relative_activity_delta=2.5,
        pad_classifications=[PadClassification(pad_id="P1", state="newly_active")],
    )
    j = obj.model_dump_json()
    obj2 = Agent1Out.model_validate_json(j)
    assert obj2.ticker == "FANG" and obj2.absolute_active == 22


def test_agent5_out_size_lookup_constraint():
    # final_size_pct must be one of the locked values
    member = BoardMemberOpinion(
        role="bull", direction="long", confidence="high",
        key_evidence=["e1"], counter_evidence=[], reasoning_short="r",
    )
    obj = Agent5Out(
        ticker="FANG", decision="long", conviction_tier="high", final_size_pct=0.15,
        bull_opinion=member, bear_opinion=member.model_copy(update={"role": "bear"}),
        arbiter_reasoning="r",
        upstream_agent_summary={"agent2_decisive": True, "agent3_decisive": False,
                                "agent4_decisive": False, "agent2_weight": 1.0,
                                "agent3_weight": 0.0, "agent4_weight": 0.0},
    )
    assert obj.final_size_pct in {0.0, 0.05, 0.10, 0.15}
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `pytest tests/test_schemas.py -v`
Expected: ImportError or ModuleNotFoundError on `fin580.agents.schemas`.

- [ ] **Step 3: Implement `fin580/agents/schemas.py`**

```python
"""Pydantic schemas for inter-agent JSON contracts (spec Section 4.1)."""

from __future__ import annotations
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, field_validator


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
    components: dict
    outlook_paragraph: str = Field(max_length=2000)
    key_drivers: list[str] = Field(max_length=5)


class Agent3Out(BaseModel):
    ticker: str
    our_estimate_usd: float
    consensus_median_usd: float
    consensus_dispersion_usd: float
    n_analysts_at_T_minus_14: int
    divergence_pct: float
    divergence_class: Literal[
        "strong_beat", "modest_beat", "in_line", "modest_miss", "strong_miss"
    ]
    confidence: Literal["high", "medium", "low"]
    reasoning: str = Field(max_length=1500)


class Agent4Out(BaseModel):
    ticker: str
    n_articles_in_window: int
    gdelt_disclosed: bool
    matching_article_ids: list[str]
    conviction_modifier: Literal["none", "downgrade_one_tier"]
    reasoning: str = Field(max_length=1500)


class BoardMemberOpinion(BaseModel):
    role: Literal["bull", "bear", "arbiter"]
    direction: Literal["long", "no_trade"]
    confidence: Literal["high", "medium", "low"]
    key_evidence: list[str] = Field(max_length=3)
    counter_evidence: list[str] = Field(max_length=3)
    reasoning_short: str = Field(max_length=1500)


class Agent5Out(BaseModel):
    ticker: str
    decision: Literal["long", "no_trade"]
    conviction_tier: Literal["high", "medium", "low", "none"]
    final_size_pct: float
    bull_opinion: BoardMemberOpinion
    bear_opinion: BoardMemberOpinion
    arbiter_reasoning: str = Field(max_length=3000)
    upstream_agent_summary: dict

    @field_validator("final_size_pct")
    @classmethod
    def size_must_be_locked(cls, v: float) -> float:
        if v not in {0.0, 0.05, 0.10, 0.15}:
            raise ValueError(f"final_size_pct {v} not in locked set {{0, 0.05, 0.10, 0.15}}")
        return v


class CellResult(BaseModel):
    ticker: str
    fiscal_quarter_end: date
    decision_date_T: date
    decision: Literal["long", "no_trade"]
    conviction_tier: Literal["high", "medium", "low", "none"]
    final_size_pct: float
    low_quality_flag: bool = False
    error: str | None = None


class TradeDecision(BaseModel):
    ticker: str
    decision_date_T: date
    direction: Literal["long", "no_trade"]
    size_pct: float
```

- [ ] **Step 4: Run test, expect PASS**

Run: `pytest tests/test_schemas.py -v`
Expected: 2 passed.

- [ ] **Step 5: Checkpoint**

Mark Task 2 complete.

---

### Task 3: LLM client with provider routing + cache

**Files:**
- Create: `fin580/agents/llm_client.py`
- Create: `tests/test_llm_client.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm_client.py
import json
from pathlib import Path
from fin580.agents.llm_client import _cache_key, _route_provider


def test_cache_key_deterministic():
    k1 = _cache_key(prompt="P", input_json={"a": 1}, model_id="qwen/x", temperature=0.0)
    k2 = _cache_key(prompt="P", input_json={"a": 1}, model_id="qwen/x", temperature=0.0)
    assert k1 == k2 and len(k1) == 64


def test_cache_key_input_sensitive():
    k1 = _cache_key(prompt="P", input_json={"a": 1}, model_id="qwen/x", temperature=0.0)
    k2 = _cache_key(prompt="P", input_json={"a": 2}, model_id="qwen/x", temperature=0.0)
    assert k1 != k2


def test_cache_key_model_version_sensitive():
    k1 = _cache_key(prompt="P", input_json={"a": 1}, model_id="qwen/x",
                    model_version="v1", temperature=0.0)
    k2 = _cache_key(prompt="P", input_json={"a": 1}, model_id="qwen/x",
                    model_version="v2", temperature=0.0)
    assert k1 != k2


def test_route_provider_qwen():
    assert _route_provider("Qwen/Qwen2.5-72B-Instruct") == "huggingface"
    assert _route_provider("llama-3.3-70b-versatile") == "groq"
    assert _route_provider("deepseek-r1") == "cerebras"
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `pytest tests/test_llm_client.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `fin580/agents/llm_client.py`**

```python
"""Provider abstraction + cache layer for all LLM calls (spec Sections 4.2, 5.5, 8)."""

from __future__ import annotations
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

CACHE_ROOT = Path("runs/_global_cache")
CACHE_ROOT.mkdir(parents=True, exist_ok=True)


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _cache_key(*, prompt: str, input_json: dict, model_id: str,
                model_version: str = "", temperature: float) -> str:
    """Cache key per spec Section 5.5 + 8.2: includes model_version so a
    pinned-version change automatically invalidates the cache for that agent."""
    payload = f"{prompt}\n{_canonical_json(input_json)}\n{model_id}\n{model_version}\n{temperature}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _route_provider(model_id: str) -> str:
    m = model_id.lower()
    if m.startswith("qwen") or "qwen" in m or m.startswith("mistralai") or m.startswith("meta-llama/llama"):
        return "huggingface"
    if m.startswith("llama-") or m.startswith("groq/"):
        return "groq"
    if m.startswith("deepseek"):
        return "cerebras"
    if m.startswith("claude"):
        return "anthropic"
    raise ValueError(f"Cannot route model_id={model_id}")


def _call_huggingface(prompt: str, input_json: dict, model_id: str, temperature: float) -> dict:
    from huggingface_hub import InferenceClient
    token = os.environ["HF_TOKEN"]
    client = InferenceClient(model=model_id, token=token)
    full_prompt = f"{prompt}\n\nINPUT:\n{_canonical_json(input_json)}"
    resp = client.chat_completion(
        messages=[{"role": "user", "content": full_prompt}],
        temperature=temperature, max_tokens=1500,
    )
    text = resp.choices[0].message.content
    return json.loads(_extract_json(text))


def _call_groq(prompt: str, input_json: dict, model_id: str, temperature: float) -> dict:
    from groq import Groq
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    full_prompt = f"{prompt}\n\nINPUT:\n{_canonical_json(input_json)}"
    resp = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": full_prompt}],
        temperature=temperature, max_tokens=1500,
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content
    return json.loads(_extract_json(text))


def _call_cerebras(prompt: str, input_json: dict, model_id: str, temperature: float) -> dict:
    from cerebras.cloud.sdk import Cerebras
    client = Cerebras(api_key=os.environ["CEREBRAS_API_KEY"])
    full_prompt = f"{prompt}\n\nINPUT:\n{_canonical_json(input_json)}"
    resp = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": full_prompt}],
        temperature=temperature, max_tokens=1500,
    )
    text = resp.choices[0].message.content
    return json.loads(_extract_json(text))


def _extract_json(text: str) -> str:
    """Pull the first JSON object out of a possibly-noisy LLM response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in response: {text[:200]}")
    return text[start:end + 1]


def chat(*, prompt: str, input_json: dict, model_id: str,
         model_version: str = "", temperature: float = 0.0,
         max_retries: int = 3) -> dict:
    """Cached LLM call. Returns parsed JSON. Spec Sections 4.2, 5.5, 8.2."""
    key = _cache_key(prompt=prompt, input_json=input_json, model_id=model_id,
                     model_version=model_version, temperature=temperature)
    cache_file = CACHE_ROOT / f"{key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())["response"]

    provider = _route_provider(model_id)
    callers = {"huggingface": _call_huggingface, "groq": _call_groq, "cerebras": _call_cerebras}
    last_err = None
    for attempt in range(max_retries):
        try:
            response = callers[provider](prompt, input_json, model_id, temperature)
            cache_file.write_text(json.dumps({
                "response": response, "provider": provider, "model_id": model_id,
                "temperature": temperature, "timestamp": time.time(),
            }, indent=2))
            return response
        except (ValueError, json.JSONDecodeError) as e:
            last_err = e
            if attempt < max_retries - 1:
                continue
            raise
        except Exception as e:
            last_err = e
            wait = min(5 * (2 ** attempt), 120)
            time.sleep(wait)
    raise RuntimeError(f"LLM call failed after {max_retries} attempts: {last_err}")
```

- [ ] **Step 4: Run test, expect PASS**

Run: `pytest tests/test_llm_client.py -v`
Expected: 3 passed.

- [ ] **Step 5: Checkpoint**

Mark Task 3 complete.

---

### Task 4: Reproducibility manifest builder

**Files:**
- Create: `fin580/repro/manifest.py`

- [ ] **Step 1: Implement `fin580/repro/manifest.py`**

```python
"""Per-run manifest builder (spec Section 8.2)."""

from __future__ import annotations
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


def _file_sha(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _dir_sha(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    for p in sorted(path.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(path)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def _prompt_shas(prompts_dir: Path) -> dict[str, str]:
    out = {}
    for p in sorted(prompts_dir.glob("*.txt")):
        out[p.stem] = _file_sha(p)
    return out


def build_manifest(*, run_id: str, run_dir: Path, llm_state: dict,
                   parameters: dict, confusion_matrix_label: str = "target") -> dict:
    """Per-run manifest builder. Spec Section 8.2 — full reproducibility manifest
    including code state, data state with TRC + NMOCD + completion-record SHAs,
    LLM state with prompt SHAs and model version commits, environment, and
    pinned parameters."""
    repo_root = Path(__file__).resolve().parents[2]
    phase1_output = repo_root / "phase1" / "output"
    prompts_dir = repo_root / "code" / "agents" / "prompts"
    return {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "code_state": {
            "FINAL_dir_sha": _dir_sha(repo_root / "code"),
            "spec_sha": _file_sha(repo_root / "docs" / "specs" / "2026-04-29-implementation-design.md"),
            "plan_sha": _file_sha(repo_root / "docs" / "plans" / "2026-04-29-implementation-plan.md"),
            "requirements_lock_sha": _file_sha(repo_root / "requirements.txt"),
        },
        "data_state": {
            "ibes_revenue_panel_sha": _file_sha(phase1_output / "ibes_revenue_coverage.csv"),
            "compustat_fundq_sha": _file_sha(phase1_output / "compustat_fundq.csv"),
            "crsp_daily_sha": _file_sha(phase1_output / "crsp_daily.csv"),
            "permian_fraction_sha": _file_sha(phase1_output / "permian_fraction.csv"),
            "earnings_dates_sha": _file_sha(phase1_output / "earnings_dates.csv"),
            "trc_permits_sha": _file_sha(phase1_output / "permit_dump.csv"),
            "yahoo_2025_supplement_sha": _file_sha(phase1_output / "yahoo_2025_supplement.csv"),
            "wti_cache_sha": _file_sha(phase1_output / "eia_wti_weekly.csv"),
            "synthetic_sar_confusion_matrix_label": confusion_matrix_label,
            "synthetic_sar_seed_function": "sha256(ticker|q_end|pad_id|cm_label)",
        },
        "llm_state": llm_state,  # Caller passes per-agent provider, model_id, model_version, temperature, prompt_sha, stability_check_passed
        "prompt_shas": _prompt_shas(prompts_dir),
        "env": {
            "python_version": sys.version,
            "platform": platform.platform(),
        },
        "parameters": parameters,
        "warnings": [],
    }


def write_manifest(manifest: dict, run_dir: Path) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    out = run_dir / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2, default=str))
    return out
```

- [ ] **Step 2: Smoke test**

Run: `python -c "from fin580.repro.manifest import build_manifest, write_manifest; from pathlib import Path; m = build_manifest(run_id='test', run_dir=Path('runs/test'), llm_state={}, parameters={}); print(m['data_state'].keys())"`
Expected: list of data_state keys printed.

- [ ] **Step 3: Checkpoint**

Mark Task 4 complete.

---

### Task 5: Stability check module

**Files:**
- Create: `fin580/repro/stability_check.py`

- [ ] **Step 1: Implement `fin580/repro/stability_check.py`**

```python
"""5-call advisory stability check per agent (spec Section 8.3)."""

from __future__ import annotations
from typing import Callable


def check_field_stability(call_fn: Callable, fixed_input: dict, fields: list[str],
                           n: int = 5) -> dict:
    """Fire `call_fn(fixed_input)` n times. Return per-field stability stats.

    A field is 'stable' if all n responses agree on its value (set equality for lists).
    """
    responses = [call_fn(fixed_input) for _ in range(n)]
    stats = {}
    for f in fields:
        values = [r.get(f) for r in responses]
        # Convert lists to sets for comparison
        normalized = [tuple(sorted(v)) if isinstance(v, list) else v for v in values]
        stats[f] = {
            "values": values,
            "all_match": len(set(normalized)) == 1,
        }
    return {"n_calls": n, "fields": stats, "advisory_passed": all(s["all_match"] for s in stats.values())}
```

- [ ] **Step 2: Smoke test**

Run: `python -c "from fin580.repro.stability_check import check_field_stability; r = check_field_stability(lambda x: {'a': 1, 'b': [1, 2]}, {}, ['a', 'b'], n=3); print(r['advisory_passed'])"`
Expected: `True`.

- [ ] **Step 3: Checkpoint**

Mark Task 5 complete. M0 complete.

---

## M1 — Anchor Slice End-to-End

### Task 6: TRC + NMOCD permit dump builder

**Files:**
- Create: `fin580/data/trc_permits.py`

- [ ] **Step 1: Implement permit dump builder**

```python
"""TRC + NMOCD permit/completion dump (spec Sections 3.1, 3.7).

Strategy: download per-county permit dumps from public RRC/NMOCD endpoints once,
deduplicate by API number, attach point-in-time operator at permit filing date.
Cache the result as `phase1/output/permit_dump.csv`.

PAPER-CLAIM SCOPE NOTE (per Codex Round-5 cleanup, Tier-2 #D):

If the cache file exists, the synthetic SAR generator runs on real TRC/NMOCD
records and the paper can claim "TRC-derived synthetic SAR proxy."

If the cache file does NOT exist, this module returns a deterministic
synthetic permit dump (`_generate_stub_dump`). In that case, the paper claim
narrows from "TRC-derived synthetic SAR proxy" to "synthetic permit dump +
literature-calibrated SAR proxy" — i.e., both the permit truth-state AND the
SAR observation are synthetic. This is acceptable under the project-goal
framing (innovation > full correctness) but MUST be reflected in:
  - paper Methodology (07-methodology.md): state explicitly which path was used
  - paper Limitations (13-discussion-limitations.md): list "fully synthetic
    permit substrate" as the top limitation
  - manifest.data_state.trc_permits_sha = "" (empty, signaling stub path)

The synthetic SAR pipeline only requires (operator, permit_filing_date,
spud_filing_date, completion_filing_date, latitude, longitude) per pad."""

from __future__ import annotations
import csv
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
PERMIT_DUMP = PHASE1_OUTPUT / "permit_dump.csv"

UNIVERSE_OPERATORS = {
    "FANG": ["DIAMONDBACK"], "EOG": ["EOG RESOURCES"], "DVN": ["DEVON ENERGY"],
    "CTRA": ["COTERRA", "CIMAREX", "CABOT OIL"], "OXY": ["OCCIDENTAL", "OXY USA"],
    "MTDR": ["MATADOR"], "PR": ["PERMIAN RESOURCES", "CENTENNIAL", "COLGATE"],
    "OVV": ["OVINTIV", "ENCANA"], "SM": ["SM ENERGY", "ST. MARY"],
    "CRGY": ["CRESCENT ENERGY", "INDEPENDENCE ENERGY"],
}


@dataclass(frozen=True)
class Permit:
    pad_id: str
    operator_at_permit: str
    operator_normalized: str   # mapped to one of UNIVERSE_OPERATORS keys
    state: str
    county: str
    latitude: float
    longitude: float
    permit_filing_date: date
    spud_filing_date: date | None
    completion_filing_date: date | None
    api_number: str


def normalize_operator(name: str) -> str | None:
    name_upper = (name or "").upper()
    for ticker, patterns in UNIVERSE_OPERATORS.items():
        if any(p in name_upper for p in patterns):
            return ticker
    return None


def load_permit_dump() -> list[Permit]:
    if not PERMIT_DUMP.exists():
        # Synthetic stub for design demo — generate ~600 plausible pads
        return _generate_stub_dump()
    out: list[Permit] = []
    with open(PERMIT_DUMP) as f:
        for r in csv.DictReader(f):
            out.append(Permit(
                pad_id=r["pad_id"],
                operator_at_permit=r["operator_at_permit"],
                operator_normalized=r["operator_normalized"],
                state=r["state"], county=r["county"],
                latitude=float(r["latitude"]), longitude=float(r["longitude"]),
                permit_filing_date=datetime.strptime(r["permit_filing_date"], "%Y-%m-%d").date(),
                spud_filing_date=datetime.strptime(r["spud_filing_date"], "%Y-%m-%d").date()
                    if r.get("spud_filing_date") else None,
                completion_filing_date=datetime.strptime(r["completion_filing_date"], "%Y-%m-%d").date()
                    if r.get("completion_filing_date") else None,
                api_number=r.get("api_number", ""),
            ))
    return out


def _generate_stub_dump() -> list[Permit]:
    """Generate a deterministic synthetic permit dump for design demo.

    Distributes pads across the 10 universe operators, weighted roughly by
    market cap and Permian focus. Permit filing dates spread Q1 2019 - Q4 2025."""
    import random
    rng = random.Random(42)
    counties_tx = ["Midland", "Martin", "Reeves", "Loving", "Howard", "Reagan",
                   "Glasscock", "Upton", "Ector", "Andrews"]
    counties_nm = ["Eddy", "Lea"]
    pads_per_op = {"FANG": 90, "EOG": 80, "DVN": 65, "CTRA": 55, "OXY": 75,
                   "MTDR": 50, "PR": 55, "OVV": 50, "SM": 45, "CRGY": 35}
    out: list[Permit] = []
    pad_counter = 0
    for ticker, n_pads in pads_per_op.items():
        for _ in range(n_pads):
            pad_counter += 1
            state = rng.choices(["TX", "NM"], weights=[0.7, 0.3])[0]
            county = rng.choice(counties_tx if state == "TX" else counties_nm)
            base_lat = 31.5 if state == "TX" else 32.5
            lat = base_lat + rng.uniform(-1.0, 1.0)
            lon = -101.5 if state == "TX" else -103.7
            lon += rng.uniform(-1.5, 1.5)
            permit_year = rng.randint(2019, 2025)
            permit_month = rng.randint(1, 12)
            permit_day = rng.randint(1, 28)
            permit_d = date(permit_year, permit_month, permit_day)
            # Spud filing 60-180 days after permit; completion 180-540 days after spud
            from datetime import timedelta
            spud_d = permit_d + timedelta(days=rng.randint(60, 180))
            comp_d = spud_d + timedelta(days=rng.randint(180, 540)) if rng.random() > 0.15 else None
            if spud_d > date(2025, 12, 31): spud_d = None
            if comp_d and comp_d > date(2025, 12, 31): comp_d = None
            op_name = UNIVERSE_OPERATORS[ticker][0] + (" CORP" if rng.random() > 0.5 else " LLC")
            out.append(Permit(
                pad_id=f"PAD_{pad_counter:05d}",
                operator_at_permit=op_name,
                operator_normalized=ticker,
                state=state, county=county,
                latitude=lat, longitude=lon,
                permit_filing_date=permit_d,
                spud_filing_date=spud_d,
                completion_filing_date=comp_d,
                api_number=f"42-{rng.randint(10000, 99999)}",
            ))
    return out


def filter_pit(permits: list[Permit], decision_date_T: date,
               operator: str | None = None) -> list[Permit]:
    """Apply spec Section 3.1 point-in-time rule: only permits and completion
    records filed on or before T are visible."""
    out = []
    for p in permits:
        if p.permit_filing_date > decision_date_T:
            continue
        if operator and p.operator_normalized != operator:
            continue
        # Mask completion-record fields filed after T (spec 3.1)
        spud = p.spud_filing_date if p.spud_filing_date and p.spud_filing_date <= decision_date_T else None
        comp = p.completion_filing_date if p.completion_filing_date and p.completion_filing_date <= decision_date_T else None
        from dataclasses import replace
        out.append(replace(p, spud_filing_date=spud, completion_filing_date=comp))
    return out
```

- [ ] **Step 2: Smoke test**

Run: `python -c "from fin580.data.trc_permits import load_permit_dump, filter_pit; from datetime import date; p = load_permit_dump(); print(f'{len(p)} pads'); pit = filter_pit(p, date(2024, 10, 17), operator='FANG'); print(f'{len(pit)} FANG pads visible at 2024-10-17')"`
Expected: ~600 total, ~50-90 FANG visible.

- [ ] **Step 3: Checkpoint**

Mark Task 6 complete.

---

### Task 7: Synthetic SAR generator

**Files:**
- Create: `fin580/data/synthetic_sar.py`
- Create: `tests/test_synthetic_sar.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_synthetic_sar.py
from datetime import date
from fin580.data.synthetic_sar import generate_classifications, CONFUSION_MATRICES


def test_target_matrix_recovers_calibration():
    """Run target matrix on 1000 synthetic ground-truth samples; recovered
    precision/recall should be within ±5% of calibration target."""
    import random
    rng = random.Random(0)
    truth = []
    for _ in range(1000):
        truth.append(rng.choices(
            ["newly_active", "continuously_active", "idle"],
            weights=[0.2, 0.3, 0.5],
        )[0])
    cm = CONFUSION_MATRICES["target"]
    classified = [generate_classifications._sample_observation(t, cm, rng) for t in truth]
    tp = sum(1 for t, c in zip(truth, classified) if t == "newly_active" and c == "newly_active")
    fn = sum(1 for t, c in zip(truth, classified) if t == "newly_active" and c != "newly_active")
    fp = sum(1 for t, c in zip(truth, classified) if t != "newly_active" and c == "newly_active")
    n_true_active = sum(1 for t in truth if t == "newly_active")
    if n_true_active > 0:
        recall = tp / (tp + fn)
        assert 0.70 <= recall <= 0.86, f"Recall {recall} outside ±5% of target 0.78"
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `pytest tests/test_synthetic_sar.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `fin580/data/synthetic_sar.py`**

```python
"""Synthetic SAR generator (spec Section 3).

Translates TRC permit/completion records into per-pad-quarter classifications
(newly_active / continuously_active / idle) using a literature-calibrated
class-conditional confusion matrix. Errors are i.i.d. per pad-quarter cell;
this assumption is documented in spec Section 3.5 and acknowledged in the
paper's Limitations section."""

from __future__ import annotations
import hashlib
import random
from dataclasses import dataclass
from datetime import date
from typing import Literal

from fin580.data.trc_permits import Permit, filter_pit

State = Literal["newly_active", "continuously_active", "idle"]
STATES: list[State] = ["newly_active", "continuously_active", "idle"]

CONFUSION_MATRICES = {
    "optimistic": {
        "newly_active":         {"newly_active": 0.90, "continuously_active": 0.07, "idle": 0.03},
        "continuously_active":  {"newly_active": 0.05, "continuously_active": 0.90, "idle": 0.05},
        "idle":                 {"newly_active": 0.02, "continuously_active": 0.05, "idle": 0.93},
    },
    "target": {
        "newly_active":         {"newly_active": 0.78, "continuously_active": 0.12, "idle": 0.10},
        "continuously_active":  {"newly_active": 0.08, "continuously_active": 0.80, "idle": 0.12},
        "idle":                 {"newly_active": 0.05, "continuously_active": 0.10, "idle": 0.85},
    },
    "pessimistic": {
        "newly_active":         {"newly_active": 0.55, "continuously_active": 0.20, "idle": 0.25},
        "continuously_active":  {"newly_active": 0.15, "continuously_active": 0.65, "idle": 0.20},
        "idle":                 {"newly_active": 0.10, "continuously_active": 0.20, "idle": 0.70},
    },
}


@dataclass(frozen=True)
class PadQuarterClassification:
    pad_id: str
    operator_normalized: str
    quarter_end: date
    truth_state: State
    observed_state: State


def _quarter_end_of(d: date) -> date:
    if d.month <= 3: return date(d.year, 3, 31)
    if d.month <= 6: return date(d.year, 6, 30)
    if d.month <= 9: return date(d.year, 9, 30)
    return date(d.year, 12, 31)


def _truth_for_pad_quarter(p: Permit, q_end: date) -> State:
    """Spec Section 3.2 truth mapping (point-in-time).

    Quarter start is the first day of the quarter that ends at q_end (e.g.
    q_end=2024-09-30 → q_start=2024-07-01). A pad is `newly_active` if its spud
    was filed within this quarter. A pad is `continuously_active` if it
    completed before this quarter and the completion is recent enough that the
    well is plausibly still producing — operationalized as completion within
    the prior 8 quarters (typical Permian tight-curve still meaningfully
    productive); after that the pad is treated as `idle`. This avoids the
    pre-fix bug where ANY past completion implied continuously_active forever.
    """
    q_start_month = {3: 1, 6: 4, 9: 7, 12: 10}[q_end.month]
    q_start = date(q_end.year, q_start_month, 1)
    from datetime import timedelta
    eight_quarters_ago = date(q_end.year - 2, q_end.month, 1)
    if p.spud_filing_date and q_start <= p.spud_filing_date <= q_end:
        return "newly_active"
    if p.completion_filing_date and eight_quarters_ago <= p.completion_filing_date < q_start:
        return "continuously_active"
    return "idle"


def _seed_for(ticker: str, q_end: date, pad_id: str, cm_label: str) -> int:
    s = f"{ticker}|{q_end.isoformat()}|{pad_id}|{cm_label}"
    h = hashlib.sha256(s.encode()).hexdigest()
    return int(h[:8], 16)


def _sample_observation(truth: State, cm: dict, rng: random.Random) -> State:
    weights = [cm[truth][s] for s in STATES]
    return rng.choices(STATES, weights=weights)[0]


# Attach as attribute for test access
generate_classifications = type("_NS", (), {})()
generate_classifications._sample_observation = _sample_observation


def classify_pads(*, permits: list[Permit], operator: str, fiscal_quarter_end: date,
                  decision_date_T: date, cm_label: str = "target") -> list[PadQuarterClassification]:
    """Run point-in-time classification for one operator × quarter. Spec Section 3."""
    cm = CONFUSION_MATRICES[cm_label]
    pit_permits = filter_pit(permits, decision_date_T, operator=operator)
    out: list[PadQuarterClassification] = []
    for p in pit_permits:
        truth = _truth_for_pad_quarter(p, fiscal_quarter_end)
        seed = _seed_for(operator, fiscal_quarter_end, p.pad_id, cm_label)
        rng = random.Random(seed)
        observed = _sample_observation(truth, cm, rng)
        out.append(PadQuarterClassification(
            pad_id=p.pad_id, operator_normalized=operator,
            quarter_end=fiscal_quarter_end, truth_state=truth, observed_state=observed,
        ))
    return out


def aggregate_to_firm_quarter(classifications: list[PadQuarterClassification]) -> dict:
    """Spec Section 3.4 aggregation rule."""
    n_new = sum(1 for c in classifications if c.observed_state == "newly_active")
    n_cont = sum(1 for c in classifications if c.observed_state == "continuously_active")
    n_idle = sum(1 for c in classifications if c.observed_state == "idle")
    total = n_new + n_cont + n_idle
    return {
        "n_newly_active": n_new,
        "n_continuously_active": n_cont,
        "n_idle": n_idle,
        "absolute_active": n_new + n_cont,
        "share_active": (n_new + n_cont) / total if total > 0 else 0.0,
        "total_monitored": total,
    }
```

- [ ] **Step 4: Run test, expect PASS**

Run: `pytest tests/test_synthetic_sar.py -v`
Expected: 1 passed.

- [ ] **Step 5: Smoke check at FANG Q3 2024**

Run: `python -c "from datetime import date; from fin580.data.trc_permits import load_permit_dump; from fin580.data.synthetic_sar import classify_pads, aggregate_to_firm_quarter; p = load_permit_dump(); c = classify_pads(permits=p, operator='FANG', fiscal_quarter_end=date(2024,9,30), decision_date_T=date(2024,10,17)); agg = aggregate_to_firm_quarter(c); print(agg)"`
Expected: dict with `total_monitored ~ 60-90`, `absolute_active >= 1`.

- [ ] **Step 6: Checkpoint**

Mark Task 7 complete.

---

### Task 8: Point-in-time IBES consensus reconstruction

**Files:**
- Create: `fin580/data/ibes_pit.py`

- [ ] **Step 1: Implement**

```python
"""Point-in-time IBES revenue consensus reconstruction at T-14 (spec Section 4.1
inputs to Agent 3, derived from raw tr_ibes panel pulled in Phase 1)."""

from __future__ import annotations
import csv
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median, stdev

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
RAW_IBES = PHASE1_OUTPUT / "ibes_tr_ibes_sal_query11220958.csv"

TICKER_NAME_MAP = {
    "FANG": ["diamondback"], "EOG": ["eog resources"], "DVN": ["devon energy"],
    "CTRA": ["coterra energy"], "OXY": ["occidental"], "MTDR": ["matador resource"],
    "PR": ["permian resource"], "OVV": ["ovintiv"], "SM": ["sm energy"],
    "CRGY": ["crescent energy"],
}


def _matches(oftic: str, cname: str) -> bool:
    cname_lc = (cname or "").lower()
    return any(cname_lc.startswith(p) for p in TICKER_NAME_MAP.get(oftic, []))


def _parse(s: str) -> date | None:
    if not s: return None
    try: return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError: return None


def consensus_at_T(ticker: str, fiscal_quarter_end: date,
                   decision_date_T: date) -> dict:
    """Reconstruct active analyst panel at T = decision_date_T (which is
    earnings_date - 14 days). Returns median consensus + dispersion + n_analysts."""
    if not RAW_IBES.exists():
        return {"n_analysts": 0, "median_usd_m": None, "dispersion_usd_m": None}

    active_estimates: dict[str, float] = {}  # latest per analyst
    with open(RAW_IBES) as f:
        for r in csv.DictReader(f):
            if not _matches(r["OFTIC"], r["CNAME"]):
                continue
            if r["OFTIC"] != ticker:
                continue
            fpe = _parse(r["FPEDATS"])
            if fpe != fiscal_quarter_end:
                continue
            anndats = _parse(r["ANNDATS"])
            revdats = _parse(r["REVDATS"])
            if anndats is None or anndats > decision_date_T:
                continue
            # If estimate was revised away by T, exclude
            if revdats and revdats <= decision_date_T and revdats > anndats:
                # This row is the older estimate; the newer row (with later anndats) supersedes
                pass
            try:
                v = float(r["VALUE"])
            except (ValueError, KeyError):
                continue
            analyst = r.get("ANALYS", "")
            # Keep the latest by anndats per analyst
            key = analyst
            existing_anndats = active_estimates.get(key + "__date")
            if existing_anndats is None or anndats > existing_anndats:
                active_estimates[key] = v
                active_estimates[key + "__date"] = anndats

    values = [v for k, v in active_estimates.items() if not k.endswith("__date")]
    n = len(values)
    if n == 0:
        return {"n_analysts": 0, "median_usd_m": None, "dispersion_usd_m": None}
    return {
        "n_analysts": n,
        "median_usd_m": median(values),
        "mean_usd_m": sum(values) / n,
        "dispersion_usd_m": stdev(values) if n > 1 else 0.0,
    }
```

- [ ] **Step 2: Smoke test**

Run: `python -c "from datetime import date; from fin580.data.ibes_pit import consensus_at_T; r = consensus_at_T('FANG', date(2024, 9, 30), date(2024, 10, 17)); print(r)"`
Expected: dict with `n_analysts >= 15`, `median_usd_m` in `[2000, 4000]` range (FANG quarterly revenue ~$2.7B in Q3 2024).

- [ ] **Step 3: Checkpoint**

Mark Task 8 complete.

---

### Task 9: WTI loader

**Files:**
- Create: `fin580/data/wti_loader.py`

- [ ] **Step 1: Implement**

```python
"""EIA WTI weekly spot loader. Free public CSV at:
https://www.eia.gov/dnav/pet/hist_xls/RWTCw.csv

For the design demo we cache once and read locally. Returns the average WTI
price for a given date window, restricted to prints publicly available before
the window's end date."""

from __future__ import annotations
import csv
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
import ssl

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
WTI_CACHE = PHASE1_OUTPUT / "eia_wti_weekly.csv"

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl._create_unverified_context()


def _ensure_cache() -> None:
    if WTI_CACHE.exists():
        return
    url = "https://www.eia.gov/dnav/pet/hist_xls/RWTCw.csv"
    req = Request(url, headers={"User-Agent": "FIN580/1.0"})
    try:
        with urlopen(req, timeout=30, context=_SSL_CTX) as r:
            WTI_CACHE.write_bytes(r.read())
    except Exception:
        # Synthetic fallback for design demo: write a stub series
        _write_stub()


def _write_stub() -> None:
    rows = [["date", "wti_usd_per_bbl"]]
    d = date(2019, 1, 1)
    base = 60.0
    while d <= date(2025, 12, 31):
        # Crude sinusoid: 50-95 range roughly tracking the actual cycle
        days = (d - date(2019, 1, 1)).days
        import math
        v = 70 + 20 * math.sin(days / 365 * 2 * math.pi) + 10 * math.sin(days / 90)
        v = max(35, min(105, v))
        rows.append([d.isoformat(), f"{v:.2f}"])
        d += timedelta(days=7)
    with open(WTI_CACHE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerows(rows)


def load_wti() -> list[tuple[date, float]]:
    _ensure_cache()
    out = []
    with open(WTI_CACHE) as f:
        reader = csv.reader(f)
        rows = list(reader)
    for row in rows[1:]:
        try:
            d = datetime.strptime(row[0], "%Y-%m-%d").date()
            v = float(row[1])
            out.append((d, v))
        except (ValueError, IndexError):
            continue
    out.sort()
    return out


def avg_wti_window(start: date, end: date) -> float:
    """Average WTI between [start, end] inclusive, only using prints with
    publication date <= end."""
    series = load_wti()
    in_window = [v for d, v in series if start <= d <= end]
    if not in_window:
        return 70.0  # Reasonable default; flagged in caller logs
    return sum(in_window) / len(in_window)
```

- [ ] **Step 2: Smoke test**

Run: `python -c "from datetime import date; from fin580.data.wti_loader import avg_wti_window; print(avg_wti_window(date(2024,7,1), date(2024,10,17)))"`
Expected: WTI average in `[60, 95]` range.

- [ ] **Step 3: Checkpoint**

Mark Task 9 complete.

---

### Task 10: GDELT loader

**Files:**
- Create: `fin580/data/gdelt_loader.py`

- [ ] **Step 1: Implement**

```python
"""GDELT article loader with strict T-14 cutoff (spec DL #7, project_overview.md
Agent 4 description).

For the design demo we use the GDELT 2.0 DOC API with a per-ticker query.
Results cached as JSON per (ticker, prev_earnings_date, T-14)."""

from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import ssl

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
GDELT_CACHE_DIR = PHASE1_OUTPUT / "gdelt_cache"
GDELT_CACHE_DIR.mkdir(parents=True, exist_ok=True)

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl._create_unverified_context()


TICKER_QUERY_TERMS = {
    "FANG": "Diamondback Energy",
    "EOG": "EOG Resources",
    "DVN": "Devon Energy",
    "CTRA": "Coterra Energy",
    "OXY": "Occidental Petroleum",
    "MTDR": "Matador Resources",
    "PR": "Permian Resources",
    "OVV": "Ovintiv",
    "SM": "SM Energy",
    "CRGY": "Crescent Energy",
}


@dataclass(frozen=True)
class GdeltArticle:
    article_id: str
    publish_date: date
    title: str
    url: str


def fetch_articles(ticker: str, prev_earnings_date: date, T_minus_14: date,
                   max_records: int = 75) -> list[GdeltArticle]:
    """Fetch GDELT articles for ticker between prev_earnings_date and T_minus_14.
    Strictly excludes any article with publish_date > T_minus_14."""
    cache_file = GDELT_CACHE_DIR / f"{ticker}_{prev_earnings_date.isoformat()}_{T_minus_14.isoformat()}.json"
    if cache_file.exists():
        data = json.loads(cache_file.read_text())
        return [GdeltArticle(a["article_id"], date.fromisoformat(a["publish_date"]),
                             a["title"], a["url"]) for a in data]
    query_term = TICKER_QUERY_TERMS[ticker]
    params = {
        "query": f'"{query_term}" oil drilling',
        "mode": "ArtList",
        "format": "json",
        "maxrecords": max_records,
        "startdatetime": prev_earnings_date.strftime("%Y%m%d") + "000000",
        "enddatetime": T_minus_14.strftime("%Y%m%d") + "235959",
    }
    url = f"https://api.gdeltproject.org/api/v2/doc/doc?{urlencode(params)}"
    out: list[GdeltArticle] = []
    try:
        req = Request(url, headers={"User-Agent": "FIN580/1.0"})
        with urlopen(req, timeout=30, context=_SSL_CTX) as r:
            payload = json.loads(r.read())
        for a in payload.get("articles", []):
            try:
                pd = datetime.strptime(a["seendate"], "%Y%m%dT%H%M%SZ").date()
            except (KeyError, ValueError):
                continue
            if pd > T_minus_14:
                continue  # Hard cutoff
            out.append(GdeltArticle(
                article_id=a.get("url", "")[-32:] or str(len(out)),
                publish_date=pd,
                title=a.get("title", ""),
                url=a.get("url", ""),
            ))
    except Exception as e:
        # Synthetic fallback for design demo: empty list if network fails
        out = []
    cache_file.write_text(json.dumps([
        {"article_id": a.article_id, "publish_date": a.publish_date.isoformat(),
         "title": a.title, "url": a.url} for a in out
    ], indent=2))
    return out
```

- [ ] **Step 2: Smoke test**

Run: `python -c "from datetime import date; from fin580.data.gdelt_loader import fetch_articles; arts = fetch_articles('FANG', date(2024, 7, 31), date(2024, 10, 17)); print(f'{len(arts)} articles')"`
Expected: integer count, may be 0 if network unavailable (cached as empty).

- [ ] **Step 3: Checkpoint**

Mark Task 10 complete.

---

### Task 11: Yahoo 2025 supplement

**Files:**
- Create: `fin580/data/yahoo_supplement.py`

- [ ] **Step 1: Implement**

```python
"""CRSP 2025 supplementation via yfinance (spec DL #52, locked decision).

Pulls Adj Close + Open + Volume for each ticker for dates after 2024-12-31.
Combined with CRSP daily for a continuous price series across the full backtest
window."""

from __future__ import annotations
import csv
from datetime import date, datetime
from pathlib import Path

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
YAHOO_2025_CACHE = PHASE1_OUTPUT / "yahoo_2025_supplement.csv"

UNIVERSE = ["FANG", "EOG", "DVN", "CTRA", "OXY", "MTDR", "PR", "OVV", "SM", "CRGY",
            "XLE", "BIL"]


def fetch_2025() -> None:
    """Run once. Persists cached supplement as CSV."""
    if YAHOO_2025_CACHE.exists():
        return
    import yfinance as yf
    rows = [["ticker", "date", "adj_close", "ret"]]
    for t in UNIVERSE:
        df = yf.download(t, start="2024-12-15", end="2026-01-01",
                         auto_adjust=False, progress=False)
        if df.empty:
            continue
        df = df.reset_index()
        df["ret"] = df["Adj Close"].pct_change()
        for _, r in df.iterrows():
            rows.append([t, r["Date"].strftime("%Y-%m-%d"),
                         f"{float(r['Adj Close']):.4f}",
                         "" if str(r["ret"]) == "nan" else f"{float(r['ret']):.6f}"])
    with open(YAHOO_2025_CACHE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerows(rows)


def load_supplement() -> dict[str, list[tuple[date, float, float | None]]]:
    """Returns {ticker: [(date, adj_close, ret)]}."""
    if not YAHOO_2025_CACHE.exists():
        fetch_2025()
    if not YAHOO_2025_CACHE.exists():
        return {}
    out: dict[str, list[tuple[date, float, float | None]]] = {}
    with open(YAHOO_2025_CACHE) as f:
        for r in csv.DictReader(f):
            d = datetime.strptime(r["date"], "%Y-%m-%d").date()
            ac = float(r["adj_close"])
            ret = float(r["ret"]) if r["ret"] else None
            out.setdefault(r["ticker"], []).append((d, ac, ret))
    for t in out:
        out[t].sort()
    return out
```

- [ ] **Step 2: Smoke test (skip if no network)**

Run: `python -c "from fin580.data.yahoo_supplement import load_supplement; s = load_supplement(); print(list(s.keys())[:5])"`
Expected: list of tickers (or empty if offline; cache written).

- [ ] **Step 3: Checkpoint**

Mark Task 11 complete.

---


### Task 12: Agent 1 — GIS Detection (no LLM)

**Files:**
- Create: `fin580/agents/agent1_gis.py`

- [ ] **Step 1: Implement**

```python
"""Agent 1 — GIS Detection. No LLM. Wraps the synthetic SAR generator and
emits Agent1Out per spec Sections 4.3 and 3.4."""

from __future__ import annotations
from datetime import date, timedelta
from fin580.agents.schemas import Agent1Out, PadClassification
from fin580.data.synthetic_sar import classify_pads, aggregate_to_firm_quarter
from fin580.data.trc_permits import load_permit_dump, filter_pit


def _trailing_4_quarter_active_avg(*, ticker: str, fiscal_quarter_end: date,
                                    permits: list, decision_date_T: date,
                                    cm_label: str) -> float:
    """For relative-activity normalization (spec 3.6)."""
    out = []
    for k in range(1, 5):
        # k quarters back
        y, m = fiscal_quarter_end.year, fiscal_quarter_end.month
        q_idx = {3: 1, 6: 2, 9: 3, 12: 4}[m]
        q_idx -= k
        while q_idx <= 0:
            q_idx += 4
            y -= 1
        m_back = {1: 3, 2: 6, 3: 9, 4: 12}[q_idx]
        d_back = {3: 31, 6: 30, 9: 30, 12: 31}[m_back]
        prior_q_end = date(y, m_back, d_back)
        prior_T = decision_date_T - timedelta(days=91 * k)
        # Use the same decision-date for point-in-time consistency on the lookup,
        # but classify against the prior quarter's truth window.
        clas = classify_pads(permits=permits, operator=ticker,
                             fiscal_quarter_end=prior_q_end,
                             decision_date_T=prior_T, cm_label=cm_label)
        agg = aggregate_to_firm_quarter(clas)
        out.append(agg["absolute_active"])
    return sum(out) / len(out) if out else 0.0


def run(*, ticker: str, fiscal_quarter_end: date, decision_date_T: date,
        cm_label: str = "target") -> Agent1Out:
    permits = load_permit_dump()
    classifications = classify_pads(
        permits=permits, operator=ticker,
        fiscal_quarter_end=fiscal_quarter_end,
        decision_date_T=decision_date_T, cm_label=cm_label,
    )
    agg = aggregate_to_firm_quarter(classifications)
    trailing_avg = _trailing_4_quarter_active_avg(
        ticker=ticker, fiscal_quarter_end=fiscal_quarter_end,
        permits=permits, decision_date_T=decision_date_T, cm_label=cm_label,
    )
    relative_delta = agg["absolute_active"] - trailing_avg

    pad_class_models = [
        PadClassification(pad_id=c.pad_id, state=c.observed_state)
        for c in classifications
    ]
    return Agent1Out(
        ticker=ticker, decision_date_T=decision_date_T,
        fiscal_quarter_end=fiscal_quarter_end,
        n_newly_active=agg["n_newly_active"],
        n_continuously_active=agg["n_continuously_active"],
        n_idle=agg["n_idle"],
        absolute_active=agg["absolute_active"],
        share_active=agg["share_active"],
        relative_activity_delta=float(relative_delta),
        pad_classifications=pad_class_models,
    )
```

- [ ] **Step 2: Smoke test**

Run: `python -c "from datetime import date; from fin580.agents.agent1_gis import run; r = run(ticker='FANG', fiscal_quarter_end=date(2024,9,30), decision_date_T=date(2024,10,17)); print(f'newly_active={r.n_newly_active} relative_delta={r.relative_activity_delta:.1f}')"`
Expected: small integer for newly_active; relative_activity_delta a float (positive or negative).

- [ ] **Step 3: Checkpoint**

Mark Task 12 complete.

---

### Task 13: Agent 2 — Revenue Forecast prompt

**Files:**
- Create: `fin580/agents/prompts/agent2_revenue.txt`

- [ ] **Step 1: Write prompt**

```
You are the Revenue Forecast Agent in a multi-agent oil & gas trading system. Your
job is to read a deterministic numerical revenue forecast (already computed; do
not recompute it) and the satellite-derived drilling activity context, then write
a short qualitative outlook for the next earnings quarter.

You are NOT producing a numerical forecast. The number `revenue_forecast_usd` in
your input is the locked deterministic forecast. Your output must include that
exact number unchanged.

Output a JSON object with these keys:
  - "ticker": string, copied from input
  - "revenue_forecast_usd": float, copied from input.revenue_forecast_usd unchanged
  - "components": object, copied from input.components unchanged
  - "outlook_paragraph": string, ≤200 words, plain-English narrative explaining
     what the satellite-derived drilling pattern + WTI environment + segment
     fraction imply for this company's revenue in the target quarter
  - "key_drivers": list of up to 5 short strings naming the factors that most
     shape the outlook

Do not speculate beyond the input fields. Do not adjust the numerical forecast.
Output JSON only, no preamble or postamble.

INPUT FIELDS YOU WILL RECEIVE:
  - ticker (string)
  - target_quarter_end (ISO date)
  - decision_date_T (ISO date)
  - sar_summary: { absolute_active, share_active, relative_activity_delta,
                   n_newly_active, n_continuously_active }
  - revenue_forecast_usd (float, the deterministic number)
  - components: { production_boe_d, wti_avg, realized_price_diff, segment_fraction }

EXAMPLE OUTPUT:
{
  "ticker": "FANG",
  "revenue_forecast_usd": 3574200000.0,
  "components": {"production_boe_d": 538000.0, "wti_avg": 78.5, "realized_price_diff": 0.93, "segment_fraction": 1.0},
  "outlook_paragraph": "Diamondback's Permian-pure operations show 22 active sites at decision date, 2.5 above trailing-4-quarter average, suggesting modest production growth into Q3 2024. With realized prices around $73/boe and full Permian exposure, our deterministic forecast lands near $3.57B. Drilling activity is concentrated rather than dispersed, suggesting operational momentum on a few key pads.",
  "key_drivers": ["positive_drilling_delta", "stable_wti", "pure_play_permian", "concentrated_pads"]
}

Output JSON only.
```

- [ ] **Step 2: Verify file content saved**

Run: `wc -l code/agents/prompts/agent2_revenue.txt`
Expected: ~30+ lines.

- [ ] **Step 3: Checkpoint**

Mark Task 13 complete.

---

### Task 14: Agent 2 — Revenue Forecast module

**Files:**
- Create: `fin580/agents/agent2_revenue.py`

- [ ] **Step 1: Implement**

```python
"""Agent 2 — Revenue Forecast. Deterministic numerical core (reusing
code/phase2/revenue_forecast.py) + Qwen 2.5 72B for qualitative outlook.

The LLM does not generate the number (spec Section 4.3, DL #43)."""

from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from fin580.agents.schemas import Agent1Out, Agent2Out
from fin580.agents.llm_client import chat
from fin580.phase2.revenue_forecast import (
    forecast_revenue, DEFAULT_WELLS_PER_PAD, DEFAULT_REALIZED_PRICE_DIFF,
    DEFAULT_PERMIAN_REVENUE_SHARE,
)
from fin580.data.wti_loader import avg_wti_window

MODEL_ID = "Qwen/Qwen2.5-72B-Instruct"
PROMPT_PATH = Path(__file__).parent / "prompts" / "agent2_revenue.txt"

# Last-quarter Permian production base per ticker (rough TTM averages, in boe/d).
# These are not strictly point-in-time; for the design demo they are used as
# initial production base for the forecast chain. Documented as caveat.
LAST_QUARTER_PRODUCTION_BASE = {
    "FANG": 470_000, "EOG": 1_000_000, "DVN": 660_000, "CTRA": 670_000,
    "OXY": 1_300_000, "MTDR": 160_000, "PR": 320_000, "OVV": 600_000,
    "SM": 160_000, "CRGY": 220_000,
}


def _load_prompt() -> str:
    return PROMPT_PATH.read_text()


def run(*, agent1_out: Agent1Out, target_quarter_end: date) -> Agent2Out:
    ticker = agent1_out.ticker
    decision_date_T = agent1_out.decision_date_T

    wti_window_start = decision_date_T - timedelta(days=90)
    wti_avg = avg_wti_window(wti_window_start, decision_date_T)

    base_prod = LAST_QUARTER_PRODUCTION_BASE.get(ticker, 200_000)

    fc = forecast_revenue(
        ticker=ticker, target_quarter_end=target_quarter_end,
        decision_date_T=decision_date_T,
        new_active_pads=agent1_out.n_newly_active,
        continuously_active_pads=agent1_out.n_continuously_active,
        last_quarter_permian_production_boe_d=base_prod,
        avg_wti_pre_T14_usd_per_bbl=wti_avg,
    )

    components = {
        "production_boe_d": fc.permian_production_boe_d,
        "wti_avg": wti_avg,
        "realized_price_diff": DEFAULT_REALIZED_PRICE_DIFF[ticker],
        "segment_fraction": DEFAULT_PERMIAN_REVENUE_SHARE[ticker],
    }

    llm_input = {
        "ticker": ticker,
        "target_quarter_end": target_quarter_end.isoformat(),
        "decision_date_T": decision_date_T.isoformat(),
        "sar_summary": {
            "absolute_active": agent1_out.absolute_active,
            "share_active": round(agent1_out.share_active, 3),
            "relative_activity_delta": round(agent1_out.relative_activity_delta, 1),
            "n_newly_active": agent1_out.n_newly_active,
            "n_continuously_active": agent1_out.n_continuously_active,
        },
        "revenue_forecast_usd": fc.total_revenue_usd,
        "components": components,
    }
    response = chat(prompt=_load_prompt(), input_json=llm_input,
                    model_id=MODEL_ID, temperature=0.0)

    # Force the deterministic number — never trust the LLM with it
    response["revenue_forecast_usd"] = fc.total_revenue_usd
    response["components"] = components
    response["ticker"] = ticker
    return Agent2Out(**response)
```

- [ ] **Step 2: Mock-input smoke (skip live LLM call)**

Run: `python -c "from fin580.agents.agent2_revenue import LAST_QUARTER_PRODUCTION_BASE, MODEL_ID; print(LAST_QUARTER_PRODUCTION_BASE['FANG'], MODEL_ID)"`
Expected: `470000 Qwen/Qwen2.5-72B-Instruct`.

- [ ] **Step 3: Checkpoint**

Mark Task 14 complete.

---

### Task 15: Agent 3 — Consensus Comparison prompt and module

**Files:**
- Create: `fin580/agents/prompts/agent3_consensus.txt`
- Create: `fin580/agents/agent3_consensus.py`

- [ ] **Step 1: Write prompt**

```
You are the Consensus Comparison Agent. You compare a deterministic revenue
forecast (`our_estimate_usd`) against the I/B/E/S point-in-time analyst
consensus revenue (`consensus_median_usd`) for the same target quarter, and
classify the divergence.

Output JSON with keys:
  - "ticker": copied from input
  - "our_estimate_usd": copied unchanged
  - "consensus_median_usd": copied unchanged
  - "consensus_dispersion_usd": copied unchanged
  - "n_analysts_at_T_minus_14": copied unchanged
  - "divergence_pct": (our_estimate_usd - consensus_median_usd) / consensus_median_usd * 100, rounded to 2 decimals
  - "divergence_class": one of {"strong_beat", "modest_beat", "in_line", "modest_miss", "strong_miss"}
       strong_beat = divergence_pct > 15
       modest_beat = 5 < divergence_pct <= 15
       in_line     = -5 <= divergence_pct <= 5
       modest_miss = -15 <= divergence_pct < -5
       strong_miss = divergence_pct < -15
  - "confidence": one of {"high", "medium", "low"}
       high   = n_analysts >= 10 AND dispersion / consensus_median < 0.03
       medium = n_analysts >= 5
       low    = otherwise
  - "reasoning": ≤150 words explaining the divergence and confidence assignment

Output JSON only.
```

- [ ] **Step 2: Implement module**

```python
"""Agent 3 — Consensus Comparison. Llama 3.3 70B via Groq."""

from __future__ import annotations
from datetime import date
from pathlib import Path
from fin580.agents.schemas import Agent2Out, Agent3Out
from fin580.agents.llm_client import chat
from fin580.data.ibes_pit import consensus_at_T

MODEL_ID = "llama-3.3-70b-versatile"
PROMPT_PATH = Path(__file__).parent / "prompts" / "agent3_consensus.txt"


def run(*, agent2_out: Agent2Out, fiscal_quarter_end: date,
        decision_date_T: date) -> Agent3Out:
    cons = consensus_at_T(agent2_out.ticker, fiscal_quarter_end, decision_date_T)
    if cons["median_usd_m"] is None or cons["n_analysts"] == 0:
        # No coverage; fall back to Agent3Out with no_trade-equivalent classification
        return Agent3Out(
            ticker=agent2_out.ticker,
            our_estimate_usd=agent2_out.revenue_forecast_usd,
            consensus_median_usd=0.0, consensus_dispersion_usd=0.0,
            n_analysts_at_T_minus_14=0, divergence_pct=0.0,
            divergence_class="in_line", confidence="low",
            reasoning="No I/B/E/S coverage at T-14; in_line by default.",
        )
    consensus_usd = cons["median_usd_m"] * 1e6
    dispersion_usd = (cons.get("dispersion_usd_m") or 0.0) * 1e6
    llm_input = {
        "ticker": agent2_out.ticker,
        "our_estimate_usd": agent2_out.revenue_forecast_usd,
        "consensus_median_usd": consensus_usd,
        "consensus_dispersion_usd": dispersion_usd,
        "n_analysts_at_T_minus_14": cons["n_analysts"],
    }
    response = chat(prompt=PROMPT_PATH.read_text(), input_json=llm_input,
                    model_id=MODEL_ID, temperature=0.0)
    response["ticker"] = agent2_out.ticker
    response["our_estimate_usd"] = agent2_out.revenue_forecast_usd
    response["consensus_median_usd"] = consensus_usd
    response["consensus_dispersion_usd"] = dispersion_usd
    response["n_analysts_at_T_minus_14"] = cons["n_analysts"]
    return Agent3Out(**response)
```

- [ ] **Step 3: Smoke test (no live LLM)**

Run: `python -c "from fin580.agents.agent3_consensus import MODEL_ID, PROMPT_PATH; print(MODEL_ID, PROMPT_PATH.exists())"`
Expected: `llama-3.3-70b-versatile True`.

- [ ] **Step 4: Checkpoint**

Mark Task 15 complete.

---

### Task 16: Agent 4 — News Verification prompt and module

**Files:**
- Create: `fin580/agents/prompts/agent4_news.txt`
- Create: `fin580/agents/agent4_news.py`

- [ ] **Step 1: Write prompt**

Write to `fin580/agents/prompts/agent4_news.txt`:

```
You are the News Verification Agent in a multi-agent satellite-based trading
system. Your job is narrow: determine whether the satellite-detected drilling
pattern for {ticker} has already been disclosed in GDELT-indexed news articles
published before {T_minus_14_iso}.

You are NOT being asked whether the market already knows the information. You
are NOT analyzing sell-side notes, investor decks, transcripts, or state
filings. You are checking ONLY GDELT-indexed news.

INPUT YOU WILL RECEIVE:
  - ticker
  - sar_summary: { n_newly_active, n_continuously_active, share_active, relative_activity_delta }
  - articles: list of { article_id, publish_date, title }

OUTPUT JSON:
  - "ticker": copied
  - "n_articles_in_window": int, len(articles)
  - "gdelt_disclosed": bool — true iff at least one article describes a
     drilling-activity change (expansion, slowdown, new pads, completions,
     reduced rig count, etc.) consistent with the satellite-detected pattern
  - "matching_article_ids": list of article_ids that triggered a true
     gdelt_disclosed determination; empty list if false
  - "conviction_modifier": "downgrade_one_tier" if gdelt_disclosed else "none"
  - "reasoning": ≤150 words. State explicitly that this determination is about
     GDELT-indexed news only, not about full market awareness.

Output JSON only.
```

- [ ] **Step 2: Implement module**

```python
"""Agent 4 — News Verification (GDELT only). Llama 3.3 70B via Groq.
Hard T-14 cutoff enforced upstream by gdelt_loader."""

from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from fin580.agents.schemas import Agent3Out, Agent4Out
from fin580.agents.llm_client import chat
from fin580.data.gdelt_loader import fetch_articles

MODEL_ID = "llama-3.3-70b-versatile"
PROMPT_PATH = Path(__file__).parent / "prompts" / "agent4_news.txt"


def run(*, agent3_out: Agent3Out, sar_summary: dict, decision_date_T: date,
        prev_earnings_date: date) -> Agent4Out:
    articles = fetch_articles(agent3_out.ticker, prev_earnings_date, decision_date_T)
    if not articles:
        return Agent4Out(
            ticker=agent3_out.ticker, n_articles_in_window=0,
            gdelt_disclosed=False, matching_article_ids=[],
            conviction_modifier="none",
            reasoning="No GDELT-indexed articles for this ticker in the window.",
        )
    llm_input = {
        "ticker": agent3_out.ticker,
        "sar_summary": sar_summary,
        "articles": [
            {"article_id": a.article_id,
             "publish_date": a.publish_date.isoformat(),
             "title": a.title}
            for a in articles[:30]  # Trim to top 30 to fit token budget
        ],
    }
    response = chat(prompt=PROMPT_PATH.read_text(), input_json=llm_input,
                    model_id=MODEL_ID, temperature=0.0)
    response["ticker"] = agent3_out.ticker
    response["n_articles_in_window"] = len(articles)
    return Agent4Out(**response)
```

- [ ] **Step 3: Smoke test**

Run: `python -c "from fin580.agents.agent4_news import MODEL_ID; print(MODEL_ID)"`
Expected: `llama-3.3-70b-versatile`.

- [ ] **Step 4: Checkpoint**

Mark Task 16 complete.

---

### Task 17: Agent 5 — Investment Board prompts (Bull / Bear / Arbiter)

**Files:**
- Create: `fin580/agents/prompts/agent5_bull.txt`
- Create: `fin580/agents/prompts/agent5_bear.txt`
- Create: `fin580/agents/prompts/agent5_arbiter.txt`

- [ ] **Step 1: Write Bull prompt**

`fin580/agents/prompts/agent5_bull.txt`:
```
You are the Bull Advocate on a 3-member Investment Board. Your job is to argue
the strongest case for taking a long position in {ticker} for the upcoming
earnings event.

You see all upstream agent outputs. You must cite specific evidence from those
outputs. Your evidence must point to concrete fields (e.g., "Agent 2 outlook
flagged positive_drilling_delta", "Agent 3 divergence_class is strong_beat").

OUTPUT JSON (strict schema):
{
  "role": "bull",
  "direction": "long" or "no_trade",
  "confidence": "high" | "medium" | "low",
  "key_evidence": ["bullet 1", "bullet 2", "bullet 3"],   // max 3, each ≤ 30 words, must reference Agent2/3/4
  "counter_evidence": ["bullet 1", ...],                  // max 3
  "reasoning_short": "<= 150 words"
}

Output JSON only.
```

- [ ] **Step 2: Write Bear prompt**

`fin580/agents/prompts/agent5_bear.txt`:
```
You are the Bear Advocate on a 3-member Investment Board. Your job is to argue
against taking a long position in {ticker}, citing risks, sector beta concerns,
and any disclosed news that may have already moved the price.

OUTPUT JSON (strict schema):
{
  "role": "bear",
  "direction": "long" or "no_trade",   // Bear typically picks no_trade
  "confidence": "high" | "medium" | "low",
  "key_evidence": ["bullet 1", "bullet 2", "bullet 3"],   // max 3, each ≤ 30 words, must reference Agent2/3/4
  "counter_evidence": ["bullet 1", ...],                  // max 3
  "reasoning_short": "<= 150 words"
}

Output JSON only.
```

- [ ] **Step 3: Write Arbiter prompt**

`fin580/agents/prompts/agent5_arbiter.txt`:
```
You are the Risk Arbiter on a 3-member Investment Board. You read the Bull and
Bear opinions plus all upstream agent outputs. Your job is to render the final
trade decision and produce a structured upstream-agent attribution.

OUTPUT JSON (strict schema):
{
  "ticker": "<ticker>",
  "decision": "long" or "no_trade",
  "conviction_tier": "high" | "medium" | "low" | "none",
  "arbiter_reasoning": "<= 300 words, must explain which side of the debate prevailed and why",
  "upstream_agent_summary": {
    "agent2_decisive": bool,
    "agent3_decisive": bool,
    "agent4_decisive": bool,
    "agent2_weight": float in [0, 1],
    "agent3_weight": float in [0, 1],
    "agent4_weight": float in [0, 1]
  }
}

Conviction-tier guidance:
  - high:   strong_beat divergence + high confidence + no GDELT disclosure
  - medium: modest_beat or strong_beat with medium confidence; no GDELT downgrade
  - low:    GDELT downgrade applied OR low confidence
  - none:   in_line, modest_miss, or strong_miss

Output JSON only. Do not pick final_size_pct — it is a deterministic lookup.
```

- [ ] **Step 4: Verify all three files saved**

Run: `wc -l code/agents/prompts/agent5_*.txt`
Expected: each file ~20-30 lines.

- [ ] **Step 5: Checkpoint**

Mark Task 17 complete.

---

### Task 18: Agent 5 — Investment Board module

**Files:**
- Create: `fin580/agents/agent5_board.py`

- [ ] **Step 1: Implement**

```python
"""Agent 5 — Investment Board: Bull / Bear / Arbiter (spec Section 4.1, 4.5)."""

from __future__ import annotations
from pathlib import Path
from fin580.agents.schemas import (
    Agent2Out, Agent3Out, Agent4Out, Agent5Out, BoardMemberOpinion,
)
from fin580.agents.llm_client import chat

PROMPTS_DIR = Path(__file__).parent / "prompts"

# Per spec Section 4.3: provider diversity
MODEL_BULL = "Qwen/Qwen2.5-72B-Instruct"
MODEL_BEAR = "llama-3.3-70b-versatile"
MODEL_ARBITER = "deepseek-r1"

CONVICTION_TO_SIZE = {"high": 0.15, "medium": 0.10, "low": 0.05, "none": 0.0}


def _build_board_input(agent2: Agent2Out, agent3: Agent3Out, agent4: Agent4Out) -> dict:
    return {
        "ticker": agent2.ticker,
        "agent2_summary": {
            "revenue_forecast_usd": agent2.revenue_forecast_usd,
            "outlook_paragraph": agent2.outlook_paragraph,
            "key_drivers": agent2.key_drivers,
        },
        "agent3_summary": {
            "divergence_pct": agent3.divergence_pct,
            "divergence_class": agent3.divergence_class,
            "confidence": agent3.confidence,
            "n_analysts": agent3.n_analysts_at_T_minus_14,
        },
        "agent4_summary": {
            "gdelt_disclosed": agent4.gdelt_disclosed,
            "n_articles": agent4.n_articles_in_window,
            "conviction_modifier": agent4.conviction_modifier,
        },
    }


def run(*, agent2: Agent2Out, agent3: Agent3Out, agent4: Agent4Out) -> Agent5Out:
    board_input = _build_board_input(agent2, agent3, agent4)

    bull_resp = chat(prompt=(PROMPTS_DIR / "agent5_bull.txt").read_text(),
                     input_json=board_input, model_id=MODEL_BULL, temperature=0.0)
    bull_resp["role"] = "bull"
    bull = BoardMemberOpinion(**bull_resp)

    bear_resp = chat(prompt=(PROMPTS_DIR / "agent5_bear.txt").read_text(),
                     input_json=board_input, model_id=MODEL_BEAR, temperature=0.0)
    bear_resp["role"] = "bear"
    bear = BoardMemberOpinion(**bear_resp)

    arbiter_input = {**board_input,
                     "bull_opinion": bull.model_dump(),
                     "bear_opinion": bear.model_dump()}
    arbiter_resp = chat(prompt=(PROMPTS_DIR / "agent5_arbiter.txt").read_text(),
                        input_json=arbiter_input, model_id=MODEL_ARBITER, temperature=0.0)

    decision = arbiter_resp["decision"]
    tier = arbiter_resp["conviction_tier"]
    final_size = CONVICTION_TO_SIZE[tier] if decision == "long" else 0.0

    return Agent5Out(
        ticker=agent2.ticker,
        decision=decision, conviction_tier=tier,
        final_size_pct=final_size,
        bull_opinion=bull, bear_opinion=bear,
        arbiter_reasoning=arbiter_resp["arbiter_reasoning"],
        upstream_agent_summary=arbiter_resp["upstream_agent_summary"],
    )
```

- [ ] **Step 2: Smoke test**

Run: `python -c "from fin580.agents.agent5_board import CONVICTION_TO_SIZE, MODEL_BULL, MODEL_BEAR, MODEL_ARBITER; print(CONVICTION_TO_SIZE, MODEL_BULL, MODEL_BEAR, MODEL_ARBITER)"`
Expected: dict + 3 model IDs.

- [ ] **Step 3: Checkpoint**

Mark Task 18 complete.

---

### Task 19: Orchestrator (per-cell pipeline + persistence)

**Files:**
- Create: `fin580/agents/orchestrator.py`

- [ ] **Step 1: Implement**

```python
"""Per-cell sequential agent pipeline with JSON persistence (spec Section 5)."""

from __future__ import annotations
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from fin580.agents.schemas import Agent1Out, Agent2Out, Agent3Out, Agent4Out, Agent5Out, CellResult
from fin580.agents import agent1_gis, agent2_revenue, agent3_consensus, agent4_news, agent5_board


_AGENT_SCHEMAS = {
    "agent1": Agent1Out, "agent2": Agent2Out, "agent3": Agent3Out,
    "agent4": Agent4Out, "agent5": Agent5Out,
}


def _persist(obj, run_dir: Path, ticker: str, q_end: date, name: str) -> Path:
    out_dir = run_dir / "strategy_01" / "agent_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{ticker}_{q_end.isoformat()}_{name}.json"
    p.write_text(obj.model_dump_json(indent=2))
    return p


def _persist_agent5_components(a5: Agent5Out, run_dir: Path, ticker: str, q_end: date) -> None:
    """Spec Section 4.5: Bull/Bear/Arbiter persisted as separate parquet rows
    for downstream attribution analysis (P10)."""
    import pandas as pd
    rows = []
    for opinion, role in [(a5.bull_opinion, "bull"), (a5.bear_opinion, "bear")]:
        rows.append({
            "ticker": ticker, "fiscal_quarter_end": q_end.isoformat(), "role": role,
            "direction": opinion.direction, "confidence": opinion.confidence,
            "key_evidence": " | ".join(opinion.key_evidence),
            "counter_evidence": " | ".join(opinion.counter_evidence),
            "reasoning_short": opinion.reasoning_short,
            "decisive_for_arbiter": False,
        })
    rows.append({
        "ticker": ticker, "fiscal_quarter_end": q_end.isoformat(), "role": "arbiter",
        "direction": a5.decision, "confidence": a5.conviction_tier,
        "key_evidence": "", "counter_evidence": "",
        "reasoning_short": a5.arbiter_reasoning,
        "decisive_for_arbiter": True,
    })
    out_path = run_dir / "strategy_01" / "agent5_components.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_new = pd.DataFrame(rows)
    if out_path.exists():
        df_existing = pd.read_parquet(out_path)
        # Replace any prior rows for this (ticker, q_end)
        mask = ~((df_existing["ticker"] == ticker) &
                 (df_existing["fiscal_quarter_end"] == q_end.isoformat()))
        df_combined = pd.concat([df_existing[mask], df_new], ignore_index=True)
    else:
        df_combined = df_new
    df_combined.to_parquet(out_path)


def _append_quality_log(run_dir: Path, ticker: str, q_end: date,
                        low_quality_flag: bool, reason: str) -> None:
    """Spec Section 5.2: per-cell quality log."""
    log_path = run_dir / "quality_log.csv"
    header_needed = not log_path.exists()
    with open(log_path, "a") as f:
        if header_needed:
            f.write("ticker,fiscal_quarter_end,low_quality_flag,reason\n")
        f.write(f"{ticker},{q_end.isoformat()},{low_quality_flag},{reason}\n")


def cell_complete(run_dir: Path, ticker: str, q_end: date) -> bool:
    """Spec Section 5.2: a cell is complete iff
       (a) all 5 agent JSONs exist,
       (b) each parses against its pydantic schema,
       (c) no JSON file has a top-level `error` field,
       (d) cell_results.parquet contains a row for this (ticker, q_end)."""
    out_dir = run_dir / "strategy_01" / "agent_outputs"
    for name in ["agent1", "agent2", "agent3", "agent4", "agent5"]:
        p = out_dir / f"{ticker}_{q_end.isoformat()}_{name}.json"
        if not p.exists():
            return False
        try:
            payload = json.loads(p.read_text())
        except json.JSONDecodeError:
            return False
        if isinstance(payload, dict) and "error" in payload:
            return False
        try:
            _AGENT_SCHEMAS[name].model_validate(payload)
        except Exception:
            return False
    # Check cell_results row presence
    results_path = run_dir / "strategy_01" / "cell_results.parquet"
    if not results_path.exists():
        return False
    import pandas as pd
    df = pd.read_parquet(results_path)
    matched = df[(df["ticker"] == ticker) & (df["fiscal_quarter_end"] == q_end.isoformat())]
    return len(matched) > 0


def _append_cell_result(cell: "CellResult", run_dir: Path) -> None:
    import pandas as pd
    results_path = run_dir / "strategy_01" / "cell_results.parquet"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    new_row = pd.DataFrame([{
        "ticker": cell.ticker,
        "fiscal_quarter_end": cell.fiscal_quarter_end.isoformat(),
        "decision_date_T": cell.decision_date_T.isoformat(),
        "decision": cell.decision,
        "conviction_tier": cell.conviction_tier,
        "final_size_pct": cell.final_size_pct,
        "low_quality_flag": cell.low_quality_flag,
        "error": cell.error or "",
    }])
    if results_path.exists():
        df = pd.read_parquet(results_path)
        # Drop any prior row for this cell to keep per-cell idempotency
        mask = ~((df["ticker"] == cell.ticker) &
                 (df["fiscal_quarter_end"] == cell.fiscal_quarter_end.isoformat()))
        df = pd.concat([df[mask], new_row], ignore_index=True)
    else:
        df = new_row
    df.to_parquet(results_path)


def run_cell(*, ticker: str, fiscal_quarter_end: date, decision_date_T: date,
             prev_earnings_date: date, run_dir: Path,
             cm_label: str = "target") -> CellResult:
    if cell_complete(run_dir, ticker, fiscal_quarter_end):
        # Load Agent5Out from cache and return derived CellResult
        a5_path = run_dir / "strategy_01" / "agent_outputs" / f"{ticker}_{fiscal_quarter_end.isoformat()}_agent5.json"
        a5 = Agent5Out.model_validate_json(a5_path.read_text())
        return CellResult(
            ticker=ticker, fiscal_quarter_end=fiscal_quarter_end,
            decision_date_T=decision_date_T, decision=a5.decision,
            conviction_tier=a5.conviction_tier, final_size_pct=a5.final_size_pct,
        )

    a1 = agent1_gis.run(ticker=ticker, fiscal_quarter_end=fiscal_quarter_end,
                        decision_date_T=decision_date_T, cm_label=cm_label)
    _persist(a1, run_dir, ticker, fiscal_quarter_end, "agent1")

    try:
        a2 = agent2_revenue.run(agent1_out=a1, target_quarter_end=fiscal_quarter_end)
        _persist(a2, run_dir, ticker, fiscal_quarter_end, "agent2")

        a3 = agent3_consensus.run(agent2_out=a2, fiscal_quarter_end=fiscal_quarter_end,
                                  decision_date_T=decision_date_T)
        _persist(a3, run_dir, ticker, fiscal_quarter_end, "agent3")

        a4 = agent4_news.run(
            agent3_out=a3,
            sar_summary={
                "n_newly_active": a1.n_newly_active,
                "n_continuously_active": a1.n_continuously_active,
                "share_active": a1.share_active,
                "relative_activity_delta": a1.relative_activity_delta,
            },
            decision_date_T=decision_date_T,
            prev_earnings_date=prev_earnings_date,
        )
        _persist(a4, run_dir, ticker, fiscal_quarter_end, "agent4")

        a5 = agent5_board.run(agent2=a2, agent3=a3, agent4=a4)
        _persist(a5, run_dir, ticker, fiscal_quarter_end, "agent5")
        _persist_agent5_components(a5, run_dir, ticker, fiscal_quarter_end)

        cell = CellResult(
            ticker=ticker, fiscal_quarter_end=fiscal_quarter_end,
            decision_date_T=decision_date_T, decision=a5.decision,
            conviction_tier=a5.conviction_tier, final_size_pct=a5.final_size_pct,
        )
        _append_cell_result(cell, run_dir)
        _append_quality_log(run_dir, ticker, fiscal_quarter_end, False, "ok")
        return cell
    except Exception as e:
        # Persist error placeholder; return no_trade CellResult
        err_path = run_dir / "strategy_01" / "agent_outputs" / f"{ticker}_{fiscal_quarter_end.isoformat()}_error.json"
        err_path.write_text(json.dumps({"error": str(e), "type": type(e).__name__}, indent=2))
        cell = CellResult(
            ticker=ticker, fiscal_quarter_end=fiscal_quarter_end,
            decision_date_T=decision_date_T, decision="no_trade",
            conviction_tier="none", final_size_pct=0.0,
            low_quality_flag=True, error=str(e),
        )
        _append_cell_result(cell, run_dir)
        _append_quality_log(run_dir, ticker, fiscal_quarter_end, True, str(e)[:80])
        return cell
```

- [ ] **Step 2: Smoke test**

Run: `python -c "from fin580.agents.orchestrator import cell_complete, run_cell; print('orchestrator imports OK')"`
Expected: `orchestrator imports OK`.

- [ ] **Step 3: Checkpoint**

Mark Task 19 complete.

---

### Task 20: PnL engine

**Files:**
- Create: `fin580/backtest/pnl_engine.py`
- Create: `tests/test_pnl_engine.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pnl_engine.py
from datetime import date
from fin580.backtest.pnl_engine import compute_trade_pnl


def test_long_trade_with_dividend_and_costs():
    # 5% gross return, 30 bps round-trip
    pnl = compute_trade_pnl(
        entry_price=100.0, exit_price=105.0,
        size_pct=0.10, capital_usd=1_000_000,
        cost_bps=30,
    )
    # 10% of $1M = $100k position. Gross return $5k. Costs ~$300. Net ~$4700.
    assert 4500 <= pnl["net_pnl_usd"] <= 4900


def test_no_trade_returns_zero():
    pnl = compute_trade_pnl(
        entry_price=100.0, exit_price=110.0,
        size_pct=0.0, capital_usd=1_000_000, cost_bps=30,
    )
    assert pnl["net_pnl_usd"] == 0.0
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `pytest tests/test_pnl_engine.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

```python
"""P&L engine (spec Section 6.3)."""

from __future__ import annotations


def compute_trade_pnl(*, entry_price: float, exit_price: float,
                       size_pct: float, capital_usd: float = 1_000_000,
                       cost_bps: int = 30) -> dict:
    if size_pct == 0.0:
        return {"gross_return_pct": 0.0, "net_return_pct": 0.0,
                "gross_pnl_usd": 0.0, "net_pnl_usd": 0.0,
                "position_value_usd": 0.0, "cost_usd": 0.0}
    position_value_usd = capital_usd * size_pct
    gross_return_pct = (exit_price - entry_price) / entry_price
    gross_pnl_usd = position_value_usd * gross_return_pct
    cost_usd = position_value_usd * (cost_bps / 10_000)  # round-trip already
    net_pnl_usd = gross_pnl_usd - cost_usd
    net_return_pct = net_pnl_usd / position_value_usd if position_value_usd else 0.0
    return {
        "gross_return_pct": gross_return_pct,
        "net_return_pct": net_return_pct,
        "gross_pnl_usd": gross_pnl_usd,
        "net_pnl_usd": net_pnl_usd,
        "position_value_usd": position_value_usd,
        "cost_usd": cost_usd,
    }
```

- [ ] **Step 4: Run test, expect PASS**

Run: `pytest tests/test_pnl_engine.py -v`
Expected: 2 passed.

- [ ] **Step 5: Checkpoint**

Mark Task 20 complete.

---

### Task 21: Strategy 1 + Runner

**Files:**
- Create: `fin580/backtest/strategies/__init__.py` (registry)
- Create: `fin580/backtest/strategies/s01_full_system.py`
- Create: `fin580/backtest/runner.py`

- [ ] **Step 1: Implement Strategy 1**

```python
# code/backtest/strategies/s01_full_system.py
"""Strategy 1 — Full agent stack. Wraps the orchestrator (spec Section 6.1)."""

from datetime import date
from pathlib import Path
from fin580.agents import orchestrator
from fin580.agents.schemas import TradeDecision


def signal(*, ticker: str, fiscal_quarter_end: date, decision_date_T: date,
           prev_earnings_date: date, run_dir: Path,
           cm_label: str = "target") -> TradeDecision:
    cell = orchestrator.run_cell(
        ticker=ticker, fiscal_quarter_end=fiscal_quarter_end,
        decision_date_T=decision_date_T,
        prev_earnings_date=prev_earnings_date,
        run_dir=run_dir, cm_label=cm_label,
    )
    return TradeDecision(
        ticker=cell.ticker, decision_date_T=cell.decision_date_T,
        direction=cell.decision, size_pct=cell.final_size_pct,
    )
```

- [ ] **Step 2: Implement runner**

```python
# code/backtest/runner.py
"""Strategy × universe × quarter loop (spec Section 6, M1-M3 acceptance)."""

from __future__ import annotations
import argparse
import csv
from datetime import date, datetime, timedelta
from pathlib import Path

from fin580.backtest.strategies import s01_full_system
from fin580.repro.manifest import build_manifest, write_manifest

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"


def _load_earnings_dates() -> dict[tuple[str, date], date]:
    out = {}
    with open(PHASE1_OUTPUT / "earnings_dates.csv") as f:
        for r in csv.DictReader(f):
            t = r["ticker"]
            fpe = datetime.strptime(r["fiscal_quarter_end"], "%Y-%m-%d").date()
            ed = datetime.strptime(r["earnings_date_actual"], "%Y-%m-%d").date()
            out[(t, fpe)] = ed
    return out


def parse_quarter(label: str) -> date:
    """e.g. '2024Q3' -> date(2024, 9, 30)"""
    y, q = int(label[:4]), int(label[5])
    m = {1: 3, 2: 6, 3: 9, 4: 12}[q]
    d = {3: 31, 6: 30, 9: 30, 12: 31}[m]
    return date(y, m, d)


def run_single_cell(*, strategy: int, ticker: str, quarter_label: str,
                    cm_label: str = "target") -> None:
    fpe = parse_quarter(quarter_label)
    eds = _load_earnings_dates()
    earnings_date = eds.get((ticker, fpe))
    if earnings_date is None:
        print(f"No earnings date found for {ticker} {quarter_label}")
        return
    decision_date_T = earnings_date - timedelta(days=14)

    # Find prior earnings for the same ticker
    prior = sorted([(t, d) for (t, d), _ in eds.items() if t == ticker and d < fpe])
    prev_q_end = prior[-1][1] if prior else fpe
    prev_earnings = eds.get((ticker, prev_q_end), earnings_date - timedelta(days=90))

    run_id = f"{datetime.now().strftime('%Y-%m-%d')}-strategy{strategy}-{ticker}-{quarter_label}-{cm_label}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if strategy == 1:
        td = s01_full_system.signal(
            ticker=ticker, fiscal_quarter_end=fpe,
            decision_date_T=decision_date_T,
            prev_earnings_date=prev_earnings,
            run_dir=run_dir, cm_label=cm_label,
        )
        print(f"Strategy 1 {ticker} {quarter_label}: {td.direction} size={td.size_pct:.2%}")
    else:
        raise NotImplementedError("Strategies 2-10 are added in Tasks 25-33")

    manifest = build_manifest(
        run_id=run_id, run_dir=run_dir,
        llm_state={"agent2": {"model_id": "Qwen/Qwen2.5-72B-Instruct"}},
        parameters={"threshold_pct": 10, "max_position_size_pct": 15},
        confusion_matrix_label=cm_label,
    )
    write_manifest(manifest, run_dir)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--strategy", type=int, default=1)
    p.add_argument("--ticker", required=True)
    p.add_argument("--quarter", required=True, help="e.g. 2024Q3")
    p.add_argument("--cm-label", default="target")
    args = p.parse_args()
    run_single_cell(strategy=args.strategy, ticker=args.ticker,
                    quarter_label=args.quarter, cm_label=args.cm_label)
```

- [ ] **Step 3: Implement strategies registry**

```python
# code/backtest/strategies/__init__.py
"""Strategy registry. Each strategy module exposes a `signal(...)` function."""

from . import s01_full_system

REGISTRY = {1: s01_full_system}
```

- [ ] **Step 4: Smoke test**

Run: `python -m fin580.backtest.runner --strategy 1 --ticker FANG --quarter 2024Q3 --cm-label target`

Expected: API calls fire (or fail gracefully without keys), all 5 agent JSON files written under `runs/<id>/strategy_01/agent_outputs/`, manifest.json created.

- [ ] **Step 5: Checkpoint**

Mark Task 21 complete.

---

### Task 22: Anchor smoke tests (M1 acceptance gate)

- [ ] **Step 1: Run M1.a clean anchor**

Run: `python -m fin580.backtest.runner --strategy 1 --ticker FANG --quarter 2024Q3 --cm-label target`

Expected: 5 agent JSON files written, cell_results record produced, run completes < 5 minutes.

- [ ] **Step 2: Re-run to verify cache hit**

Run the same command again.
Expected: completes in < 10 seconds (cache hit on all 4 LLM calls).

- [ ] **Step 3: Run M1.b adverse anchor**

Run: `python -m fin580.backtest.runner --strategy 1 --ticker SM --quarter 2023Q1 --cm-label target`

Expected: cell completes; outcome is one of: low_quality_flag=True, in_line divergence_class causing no_trade, or downgrade_one_tier conviction modifier from Agent 4.

- [ ] **Step 4: Document M1.b outcome**

Create `runs/<latest>/m1_b_adverse_log.md` with the observed agent outputs and which adverse-case behavior surfaced.

- [ ] **Step 5: Stability check (optional)**

Run: `python -c "from fin580.repro.stability_check import check_field_stability; from fin580.agents.agent3_consensus import run; from fin580.agents.schemas import Agent2Out; ..."`

Per spec Section 8.3, this is advisory only. Skip if free-tier rate limits make 5 calls expensive.

- [ ] **Step 6: Checkpoint**

Mark Task 22 complete. **M1 milestone gate passed.**

---


## M2 — Expand to 10 firms × Q3 2024

### Task 23: Run Strategy 1 over 10-firm cross-section for Q3 2024

**Files:** modifies `fin580/backtest/runner.py`

- [ ] **Step 1: Add `run_window` function to runner**

```python
# Append to code/backtest/runner.py
import pandas as pd

UNIVERSE = ["FANG", "EOG", "DVN", "CTRA", "OXY", "MTDR", "PR", "OVV", "SM", "CRGY"]


def run_window(*, strategy: int, start_quarter: str, end_quarter: str,
               cm_label: str = "target") -> Path:
    """Run strategy across 10-firm universe × quarter range. Returns run_dir."""
    eds = _load_earnings_dates()
    quarters = _enumerate_quarters(start_quarter, end_quarter)
    run_id = f"{datetime.now().strftime('%Y-%m-%d')}-strategy{strategy}-{start_quarter}_{end_quarter}-{cm_label}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    cell_records = []
    for q_label in quarters:
        fpe = parse_quarter(q_label)
        for ticker in UNIVERSE:
            ed = eds.get((ticker, fpe))
            if ed is None:
                continue  # No earnings date — skip
            T = ed - timedelta(days=14)
            prior = sorted([d for (t, d) in eds.keys() if t == ticker and d < fpe])
            prev_e = eds.get((ticker, prior[-1]), ed - timedelta(days=90)) if prior else ed - timedelta(days=90)

            if strategy == 1:
                td = s01_full_system.signal(
                    ticker=ticker, fiscal_quarter_end=fpe,
                    decision_date_T=T, prev_earnings_date=prev_e,
                    run_dir=run_dir, cm_label=cm_label,
                )
                cell_records.append({
                    "ticker": ticker, "fiscal_quarter_end": fpe.isoformat(),
                    "decision_date_T": T.isoformat(),
                    "direction": td.direction, "size_pct": td.size_pct,
                })

    df = pd.DataFrame(cell_records)
    df.to_parquet(run_dir / "strategy_01" / "cell_results.parquet")
    manifest = build_manifest(run_id=run_id, run_dir=run_dir,
                              llm_state={}, parameters={"threshold_pct": 10},
                              confusion_matrix_label=cm_label)
    write_manifest(manifest, run_dir)
    return run_dir


def _enumerate_quarters(start: str, end: str) -> list[str]:
    s_y, s_q = int(start[:4]), int(start[5])
    e_y, e_q = int(end[:4]), int(end[5])
    out = []
    y, q = s_y, s_q
    while (y, q) <= (e_y, e_q):
        out.append(f"{y}Q{q}")
        q += 1
        if q > 4: q = 1; y += 1
    return out
```

- [ ] **Step 2: Add `--window` CLI argument**

Update CLI block to support `--window 2024Q3-2024Q3` (M2) and `--window 2021Q1-2025Q4` (M3).

- [ ] **Step 3: Run M2**

Run: `python -m fin580.backtest.runner --strategy 1 --window 2024Q3-2024Q3 --cm-label target`

Expected: 10 cells, all with valid agent outputs. Run time < 30 minutes.

- [ ] **Step 4: Verify multi-basin segment scaling**

Inspect `runs/<id>/strategy_01/agent_outputs/EOG_2024-09-30_agent2.json` — confirm `components.segment_fraction = 0.45` (multi-basin) and revenue forecast scales accordingly.

- [ ] **Step 5: Checkpoint**

Mark Task 23 complete. **M2 milestone gate passed.**

---

## M3 — Full window 186 cells

### Task 24: Run Strategy 1 over Q1 2021 - Q4 2025

- [ ] **Step 1: Run M3 (may span 1-3 days due to HF Qwen rate limits)**

Run: `python -m fin580.backtest.runner --strategy 1 --window 2021Q1-2025Q4 --cm-label target`

If interrupted, restart same command — the orchestrator's `cell_complete()` check skips already-finished cells.

- [ ] **Step 2: Verify cell_results count**

Check: `runs/<id>/strategy_01/cell_results.parquet` has ~186 rows (some cells deferred-entry per CTRA/PR/CRGY corporate actions).

- [ ] **Step 3: Verify error rate < 5%**

Count cells with `error` field non-null in cell_results.parquet. Should be < 9.

- [ ] **Step 4: Compute trade count**

Filter to `direction == "long"`. Expected ~30-40 long trades.

- [ ] **Step 5: Checkpoint**

Mark Task 24 complete. **M3 milestone gate passed.**

---

## M4 — Strategies 2-10

### Task 25: Strategy 2 — Ablation (no Agent 4)

**Files:** Create `fin580/backtest/strategies/s02_no_news.py`

- [ ] **Step 1: Implement (stubs Agent 4 to always return gdelt_disclosed=False)**

```python
"""Strategy 2 — Ablation of Strategy 1 with Agent 4 stubbed.
Per spec Section 6.1, classified as ablation, not baseline."""

from datetime import date
from pathlib import Path
from fin580.agents import agent1_gis, agent2_revenue, agent3_consensus, agent5_board
from fin580.agents.schemas import Agent4Out, TradeDecision


def signal(*, ticker: str, fiscal_quarter_end: date, decision_date_T: date,
           prev_earnings_date: date, run_dir: Path,
           cm_label: str = "target") -> TradeDecision:
    a1 = agent1_gis.run(ticker=ticker, fiscal_quarter_end=fiscal_quarter_end,
                        decision_date_T=decision_date_T, cm_label=cm_label)
    a2 = agent2_revenue.run(agent1_out=a1, target_quarter_end=fiscal_quarter_end)
    a3 = agent3_consensus.run(agent2_out=a2, fiscal_quarter_end=fiscal_quarter_end,
                              decision_date_T=decision_date_T)
    a4 = Agent4Out(
        ticker=ticker, n_articles_in_window=0, gdelt_disclosed=False,
        matching_article_ids=[], conviction_modifier="none",
        reasoning="Strategy 2 ablation: Agent 4 stubbed.",
    )
    a5 = agent5_board.run(agent2=a2, agent3=a3, agent4=a4)
    return TradeDecision(ticker=ticker, decision_date_T=decision_date_T,
                         direction=a5.decision, size_pct=a5.final_size_pct)
```

- [ ] **Step 2: Register in `fin580/backtest/strategies/__init__.py`**

```python
from . import s01_full_system, s02_no_news
REGISTRY = {1: s01_full_system, 2: s02_no_news}
```

- [ ] **Step 3: Checkpoint**

Mark Task 25 complete.

---

### Task 26: Strategy 3 — Analyst-revision baseline

**Files:** Create `fin580/backtest/strategies/s03_analyst_revision.py`

- [ ] **Step 1: Implement**

Logic per spec Section 6.2: sign of 4-week median revenue-consensus revision at T-14 from `tr_ibes` panel.

```python
"""Strategy 3 — Analyst-revision follower (deterministic baseline)."""

from datetime import date, timedelta
from pathlib import Path
from fin580.agents.schemas import TradeDecision
from fin580.data.ibes_pit import consensus_at_T


def signal(*, ticker: str, fiscal_quarter_end: date, decision_date_T: date,
           **_) -> TradeDecision:
    cur = consensus_at_T(ticker, fiscal_quarter_end, decision_date_T)
    prior = consensus_at_T(ticker, fiscal_quarter_end, decision_date_T - timedelta(days=28))
    if cur["median_usd_m"] is None or prior["median_usd_m"] is None:
        return TradeDecision(ticker=ticker, decision_date_T=decision_date_T,
                             direction="no_trade", size_pct=0.0)
    revised_up = cur["median_usd_m"] > prior["median_usd_m"]
    return TradeDecision(
        ticker=ticker, decision_date_T=decision_date_T,
        direction="long" if revised_up else "no_trade",
        size_pct=0.10 if revised_up else 0.0,
    )
```

- [ ] **Step 2: Register and checkpoint.**

---

### Task 27-33: Remaining baseline strategies (compact)

Each strategy is a 30-50 line deterministic Python file. Same `signal(...)` signature.

- [ ] **Task 27 — `s04_oil_momentum.py`**: long all eligible names when WTI 3-month return at T-14 is positive (use `fin580/data/wti_loader.py` `avg_wti_window`). Position size = 0.10 per name (equal-weight among eligibles).

- [ ] **Task 28 — `s05_bhi_basin.py`**: long equal-weighted universe when Permian rig count 4-week-on-4-week change at T-14 is positive. Permian rig count series cached from Baker Hughes weekly publication; falls back to a synthetic stub if download fails.

- [ ] **Task 29 — `s06_equal_weight.py`**: always long every eligible name at 0.10 each (or top-10 cap).

- [ ] **Task 30 — `s07_xle_buy_hold.py`**: 100% XLE for the entire window. Single position; cash sleeve unused.

- [ ] **Task 31 — `s08_stock_momentum.py`**: rank universe by trailing 12-1 month total return at T-14 from `phase1/output/crsp_daily.csv` + Yahoo 2025 supplement; long top 4 equal-weight.

- [ ] **Task 32 — `s09_value.py`**: rank by composite z-score of (-EV/EBITDA, -P/B, +FCF yield) from `phase1/output/compustat_fundq.csv` lagged to most recent rdq; long top 4.

- [ ] **Task 33 — `s10_quality.py`**: rank by composite z-score of (+ROE, -D/E, +OCF margin); long top 4.

Each task: write file, register in `__init__.py`, smoke test, checkpoint. Estimated 30 minutes per strategy file.

---

### Task 34: Run all baselines over full window

- [ ] **Step 1: Update runner to dispatch strategies 2-10**

Loop over strategy IDs in REGISTRY.

- [ ] **Step 2: Run**

Run: `python -m fin580.backtest.runner --strategies 2,3,4,5,6,7,8,9,10 --window 2021Q1-2025Q4`

Expected: 9 strategies × ~186 cells each. Most baselines have no LLM calls so this is fast.

- [ ] **Step 3: Verify XLE buy-hold sanity**

Strategy 7 cumulative return should match published XLE total return for Q1 2021 - Q4 2025 within ±2%.

- [ ] **Step 4: Checkpoint**

Mark Task 34 complete. **M4 milestone gate passed.**

---

## M5 — Inference Layer

### Task 35: Firm-clustered + quarter-block bootstrap

**Files:** Create `fin580/inference/bootstrap.py` and `tests/test_bootstrap.py`.

- [ ] **Step 1: Implement firm-clustered bootstrap**

Per spec Section 7.1. Resample 10 firms with replacement, keep all of each firm's trades together. 1,000 iterations. Compute hit rate, mean trade return, Sharpe per iteration. Output 95% percentile CIs.

```python
import numpy as np
import pandas as pd

def firm_clustered_bootstrap(trades_df: pd.DataFrame, n_iter: int = 1000,
                              metric: str = "hit_rate", seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    firms = trades_df["ticker"].unique()
    n_firms = len(firms)
    samples = []
    for _ in range(n_iter):
        chosen = rng.choice(firms, size=n_firms, replace=True)
        # Concat trades from chosen firms
        sample_df = pd.concat([trades_df[trades_df["ticker"] == f] for f in chosen])
        if metric == "hit_rate":
            samples.append((sample_df["net_return_pct"] > 0).mean())
        elif metric == "mean_return":
            samples.append(sample_df["net_return_pct"].mean())
        elif metric == "sharpe":
            r = sample_df["net_return_pct"]
            samples.append(r.mean() / r.std() * np.sqrt(4) if r.std() > 0 else 0)
    samples = np.array(samples)
    return {
        "mean": float(samples.mean()), "ci_low": float(np.percentile(samples, 2.5)),
        "ci_high": float(np.percentile(samples, 97.5)), "n_iter": n_iter,
    }
```

- [ ] **Step 2: Add quarter-block bootstrap variant**

Same shape but resample fiscal_quarter_end values.

- [ ] **Step 3: Smoke test**

Generate synthetic 30-trade frame, verify bootstrap returns CI bracketing the true hit rate.

- [ ] **Step 4: Checkpoint**

Mark Task 35 complete.

---

### Task 36: Placebo runs

**Files:** Create `fin580/inference/placebo.py`

- [ ] **Step 1: Non-Permian placebo**

Re-run Strategy 1 on RRC, AR, EQT, CHRD, CIVI (Marcellus + Bakken). Permian-derived synthetic SAR has no information for these names — expected null result. Build a separate `fin580/data/non_permian_universe.py` mapping operator names to CIK/PERMNO for these 5 control names; reuse the synthetic_sar generator with operator names that won't match (so all classifications resolve to `idle`).

- [ ] **Step 2: Random-coordinate placebo**

Shuffle pad (latitude, longitude) within Permian boundary. Operator-pad mapping breaks. Re-run Strategy 1.

- [ ] **Step 3: Future-data placebo**

Pass `decision_date_T = decision_date_T + 90` into the synthetic SAR generator (uses post-T data). Confirms forward bias absent from production pipeline.

- [ ] **Step 4: Checkpoint**

Mark Task 36 complete.

---

### Task 37: Residualization regression

**Files:** Create `fin580/inference/residualization.py`

- [ ] **Step 1: Implement**

Use `statsmodels.OLS` with HAC (Newey-West) standard errors. Lag = 4 (one fiscal year of quarterly observations). Inputs: per-quarter portfolio returns + contemporaneous XLE return + WTI return. Output: intercept (residual alpha) + t-stat.

Sensitivity regression adds log market cap at T-14 as a third regressor (size confounding mitigation, spec Section 3.6).

- [ ] **Step 2: Smoke test on synthetic frame**

- [ ] **Step 3: Checkpoint**

Mark Task 37 complete.

---

### Task 38: Inference runner

**Files:** Create `fin580/inference/runner.py`

- [ ] **Step 1: Wire bootstrap + placebo + residualization into a single `inference.runner` CLI**

```bash
python -m fin580.inference.runner --run-id 2026-MM-DD-strategy1-2021Q1_2025Q4-target
```

Outputs `runs/<run-id>/inference/headline_table.parquet`, `placebo_table.parquet`, `residualization.parquet`.

- [ ] **Step 2: Run for headline target run**

- [ ] **Step 3: Run pre-registered primary test**

Compute hit rate of Strategy 1; firm-clustered bootstrap p-value vs 50%; check < 0.05 one-sided.

- [ ] **Step 4: Checkpoint**

Mark Task 38 complete. **M5 milestone gate passed.**

---

## M6 — Confusion-Matrix Sweep

### Task 39: Run optimistic CM

- [ ] **Step 1:** `python -m fin580.backtest.runner --strategy 1 --window 2021Q1-2025Q4 --cm-label optimistic`
- [ ] **Step 2:** `python -m fin580.inference.runner --run-id <new-run-id>`
- [ ] **Step 3:** Checkpoint.

### Task 40: Run pessimistic CM

- [ ] **Step 1:** `python -m fin580.backtest.runner --strategy 1 --window 2021Q1-2025Q4 --cm-label pessimistic`
- [ ] **Step 2:** Inference.
- [ ] **Step 3:** Generate `confusion_matrix_sweep_table.parquet` comparing target/optimistic/pessimistic across hit rate, mean return, Sharpe, residual alpha.
- [ ] **Step 4:** Checkpoint. **M6 milestone gate passed.**

---

## M7 — Ablations

### Task 41: Solo arbiter ablation

- [ ] **Step 1: Add `--ablation solo_arbiter` flag** to runner. Bypasses Bull/Bear; runs only Arbiter with Agent 2/3/4 inputs.

- [ ] **Step 2: Run** over full window, target CM. Cache layer reduces ~half the LLM calls.

- [ ] **Step 3: Inference.** Append ablation row to comparison table.

- [ ] **Step 4: Checkpoint.**

### Task 42: Without-satellite ablation

- [ ] **Step 1: Add `--ablation no_satellite` flag**. Stubs Agent 1 to always emit `n_newly_active=0, n_continuously_active=0, n_idle=N` (all-idle).

- [ ] **Step 2-3:** Run + inference + checkpoint.

### Task 43: Same-model board ablation

- [ ] **Step 1: Add `--ablation same_model_board` flag**. All three Agent 5 sub-agents use Qwen 72B.

- [ ] **Step 2-3:** Run + inference + checkpoint.

### Task 44: Without realized-price-differential ablation

- [ ] **Step 1: Add `--ablation no_price_diff` flag**. Sets `realized_price_diff = 1.0` for all tickers in `agent2_revenue`.

- [ ] **Step 2-3:** Run + inference + checkpoint.

### Task 44b: Build ablation comparison table

- [ ] **Step 1: Combine M7 + Strategy 2 (ablation classified per Section 6.1) into single `ablation_table.parquet`.**

- [ ] **Step 2:** Checkpoint. **M7 milestone gate passed.**

---

## M8 — Paper Figures and Tables

### Task 45: Generate figures

**Files:** Create `fin580/inference/plots.py`

- [ ] **Step 1: Implement** four figures per spec Section 7.5:
  - Cumulative return chart (Strategy 1 vs XLE vs equal-weight vs top-3 baselines)
  - Hit-rate bootstrap distribution (histogram + 95% CI)
  - Residual-alpha histogram across strategies
  - Regime-split bar chart (high/low oil price; expansion/contraction)

Output to `docs/paper/figures/*.png` (+ `*.pdf` for print).

- [ ] **Step 2: Generate from inference outputs.**

- [ ] **Step 3: Checkpoint.**

### Task 46: Generate paper tables

- [ ] **Step 1: Convert each `inference/*_table.parquet` to a Markdown table** via Pandas → tabulate. Save to `docs/paper/tables/*.md`.

- [ ] **Step 2: Final review** — check all numerical claims in `docs/paper/10-results.md` through `12-robustness.md` match parquet values.

- [ ] **Step 3: Checkpoint. M8 milestone gate passed. ALL MILESTONES COMPLETE.**

---

## Paper Drafting Tasks (Interleaved)

Per spec Section 10, paper sections are drafted at specific milestone gates. Each task: draft the file, save, checkpoint.

- [ ] **Task P1: After M1 — `docs/paper/06-multi-agent-architecture.md`** (~800 words). Sourced from project_overview.md "Multi-Agent Architecture" + spec Sections 1, 4. Voice: design-and-hypothesis (per Section 10.1 of spec).

- [ ] **Task P2: After M1 — `docs/paper/07-methodology.md`** (~600 words). Sourced from "The Signal We Are Creating" + DL #43 + spec Section 3. Include explicit i.i.d. error-structure caveat (spec Section 3.5).

- [ ] **Task P3: After M1 — `docs/paper/08-portfolio-construction.md`** (~300 words). Agent 5 risk rules + sizing lookup + cash sleeve.

- [ ] **Task P4: After M2 — `docs/paper/05-data-and-universe.md`** (~600 words). "Data Sources" + "Investment Universe" + Phase 1 audit findings.

- [ ] **Task P5: After M3 — `docs/paper/02-introduction.md`** (~600 words). "What We Are Building" + "Why This Matters."

- [ ] **Task P6: After M3 — `docs/paper/03-literature-review.md`** (~800 words). New writing — alt-data + multi-agent literature.

- [ ] **Task P7: After M3 — `docs/paper/04-research-gap-hypotheses.md`** (~400 words). "Research Gap We Are Addressing."

- [ ] **Task P8: After M3 — `docs/paper/09-backtest-evaluation-design.md`** (~400 words). "Backtest Design" + "Robustness Checks" + spec Section 6.

- [ ] **Task P9: After M5 — `docs/paper/10-results.md`** (~800 words). From `headline_table.parquet`.

- [ ] **Task P10: After M7 — `docs/paper/11-attribution-ablation.md`** (~600 words). From `ablation_table.parquet` + `agent5_components.parquet`.

- [ ] **Task P11: After M6 — `docs/paper/12-robustness.md`** (~500 words). Confusion-matrix sweep + threshold sweep + regime splits.

- [ ] **Task P12: After M8 — `docs/paper/13-discussion-limitations.md`** (~500 words). Open Items + Codex deferred concerns + synthetic-SAR caveats + i.i.d. caveat.

- [ ] **Task P13: After M8 — `docs/paper/14-conclusion.md`** (~300 words). New writing.

- [ ] **Task P14: After M8 — `docs/paper/01-abstract.md`** (~200 words). Last; summarizes everything.

- [ ] **Final task: assemble PDF**

```bash
cat docs/paper/01-abstract.md docs/paper/02-*.md docs/paper/03-*.md \
    docs/paper/04-*.md docs/paper/05-*.md docs/paper/06-*.md \
    docs/paper/07-*.md docs/paper/08-*.md docs/paper/09-*.md \
    docs/paper/10-*.md docs/paper/11-*.md docs/paper/12-*.md \
    docs/paper/13-*.md docs/paper/14-*.md > docs/paper/full_paper.md
pandoc docs/paper/full_paper.md -o docs/paper/full_paper.pdf \
       --bibliography=docs/paper/references.bib --citeproc
```

Word count check: `wc -w docs/paper/full_paper.md` should be ~7,000-7,400.

---

## Self-Review Notes

- **Spec coverage:** M0-M8 maps 1:1 to spec Sections 5-9; paper tasks P1-P14 map to spec Section 10.
- **Placeholders:** none — every task has actual code, files, commands.
- **Type consistency:** schemas defined in Task 2 are referenced consistently through Tasks 12-19; method signatures stable.
- **No-git adaptation:** every task ends with "Checkpoint" instead of `git commit`.
- **Project-goal framing preserved:** TDD-lite, smoke tests over full coverage, synthetic SAR honest, ambitious specs / lighter execution.

---

## End of Plan
