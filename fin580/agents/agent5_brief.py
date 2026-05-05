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

# Map brief-output section keys -> evidence-packet section keys.
# Sections in this map carry an explicit `data_sufficient` flag; if that
# flag is False, the brief's interpretive fields for that section MUST be
# coerced to "data_insufficient" regardless of what the LLM produced.
_BRIEF_TO_PACKET_SECTION = {
    "reaction_history_summary": "reaction_history",
    "fundamentals_summary": "fundamentals",
    "positioning_summary": "positioning",
}

# Risk flags whose validity depends on a section that may be marked
# data_insufficient. If the underlying section is insufficient, drop the
# flag from the brief's overall_risk_flags list.
_RISK_FLAG_TO_PACKET_SECTION = {
    "weak-revenue-reaction-history": "reaction_history",
    "margin-deterioration": "fundamentals",
    "capex-pressure": "fundamentals",
    "extended-positioning": "positioning",
    "overbought": "positioning",
}


def _load_prompt() -> str:
    return PROMPT_PATH.read_text()


def _coerce_brief(brief: dict, packet: dict) -> dict:
    """Enforce the brief contract on the LLM output.

    Three guardrails (binding per pre-reg):
      (1) For any section whose evidence packet says
          `data_sufficient: False`, force every interpretive (non-
          `evidence`) field in the corresponding brief section to
          `"data_insufficient"`.
      (2) Drop overall_risk_flags whose underlying section is marked
          insufficient (e.g. "weak-revenue-reaction-history" when
          reaction_history.data_sufficient is False).
      (3) If `tradable_setup` was set to a real value but every
          informative section is insufficient, downgrade
          `tradable_setup` to `"data_insufficient"` so it does not
          create a false signal for the board.
    """
    if not isinstance(brief, dict):
        return brief

    insufficient_sections: set[str] = set()
    for brief_key, packet_key in _BRIEF_TO_PACKET_SECTION.items():
        section = packet.get(packet_key, {})
        if not isinstance(section, dict):
            continue
        if section.get("data_sufficient") is False:
            insufficient_sections.add(packet_key)
            if isinstance(brief.get(brief_key), dict):
                for k in list(brief[brief_key].keys()):
                    if k == "evidence":
                        continue
                    brief[brief_key][k] = "data_insufficient"

    flags = brief.get("overall_risk_flags")
    if isinstance(flags, list):
        kept = []
        for flag in flags:
            section = _RISK_FLAG_TO_PACKET_SECTION.get(str(flag))
            if section is None or section not in insufficient_sections:
                kept.append(flag)
        brief["overall_risk_flags"] = kept

    # If reaction_history + fundamentals + positioning are ALL insufficient,
    # tradable_setup cannot be meaningfully judged from PIT context. Force
    # it to data_insufficient so the board doesn't read a stale verdict.
    informative_sections = set(_BRIEF_TO_PACKET_SECTION.values())
    if informative_sections.issubset(insufficient_sections):
        if brief.get("tradable_setup") not in (None, "data_insufficient"):
            brief["tradable_setup"] = "data_insufficient"

    return brief


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

    # Coerce the brief against the deterministic packet's data_sufficient
    # flags. The LLM cannot violate the frozen schema-contract: if a
    # section's underlying data is insufficient, the brief MUST report
    # data_insufficient for that section (and dependent risk flags are
    # dropped). This is a guardrail, not result-tuning.
    brief = _coerce_brief(brief, features)

    # Always attach the deterministic packet so the board can audit
    # which fields the brief was meant to summarize.
    brief["_evidence_packet"] = features
    return brief
