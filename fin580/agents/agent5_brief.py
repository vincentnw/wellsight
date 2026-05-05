"""Agent 5_brief — Investment Committee Brief.

Runs between Agent 4 (News Verification) and the existing Bull / Bear /
Arbiter sub-agents (`agent5_board.py`). Produces a structured JSON
summary of the four PIT brief sections (reaction history, fundamentals,
regime, positioning) for the board to consume.

Design freeze: docs/v2/v2_6_pre_registration.md.

Deterministic evidence comes from `agent5_brief_features.py`. The LLM
(gpt-4o-mini via OpenAI) writes only the interpretive tags + 1-2
sentence evidence references. It does NOT compute any of the underlying
numerical fields.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fin580.agents.agent5_brief_features import build_brief_features
from fin580.agents.llm_client import chat
from fin580.agents.schemas import Agent3Out

MODEL_ID = "gpt-4o-mini"
PROMPT_PATH = Path(__file__).parent / "prompts" / "agent5_brief.txt"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text()


def run(
    *,
    ticker: str,
    fiscal_quarter_end: date,
    decision_date_T: date,
    agent3_out: Agent3Out | None = None,
) -> dict:
    """Build the deterministic feature packet and call the LLM for the
    interpretive layer. Returns the brief JSON the board will consume."""
    features = build_brief_features(ticker, fiscal_quarter_end, decision_date_T)

    # Include divergence_class context so the brief knows whether the
    # upstream signal cleared the gate (informational only — the brief
    # cannot create a long).
    context = {
        "evidence_packet": features,
        "agent3_divergence_class": (
            agent3_out.divergence_class if agent3_out is not None else None
        ),
        "agent3_divergence_pct": (
            agent3_out.divergence_pct if agent3_out is not None else None
        ),
    }

    try:
        brief = chat(
            prompt=_load_prompt(),
            input_json=context,
            model_id=MODEL_ID,
            temperature=0.0,
        )
    except Exception as e:
        brief = {
            "ticker": ticker,
            "fiscal_quarter_end": fiscal_quarter_end.isoformat(),
            "decision_date_T": decision_date_T.isoformat(),
            "error": f"{type(e).__name__}: {str(e)[:200]}",
        }

    # Always attach the deterministic packet so the board can audit
    # which fields the brief was meant to summarize.
    brief["_evidence_packet"] = features
    return brief
