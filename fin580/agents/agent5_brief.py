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


_NEUTRAL_EVIDENCE_TEXT = (
    "Insufficient point-in-time observations to characterize this dimension; "
    "do not infer."
)


def _coerce_brief(brief: dict, packet: dict) -> dict:
    """Enforce the brief contract on the LLM output.

    Five guardrails (binding per pre-reg):
      (1) For any section whose evidence packet says
          `data_sufficient: False`, force every interpretive (non-
          `evidence`) field in the corresponding brief section to
          `"data_insufficient"`.
      (2) For those same sections, REPLACE the `evidence` free-text
          with a neutral disclaimer so the board cannot read an
          unsupported LLM claim about a dimension that has no data.
      (3) Drop overall_risk_flags whose underlying section is marked
          insufficient (e.g. "weak-revenue-reaction-history" when
          reaction_history.data_sufficient is False).
      (4) If `tradable_setup` was set to a real value but every
          informative section is insufficient, downgrade
          `tradable_setup` to `"data_insufficient"`.
      (5) PREPEND a binding coercion notice to the overall `rationale`
          listing which sections were coerced. The board's prompt is
          instructed to treat this notice as overriding any claim in
          the rationale that depends on a coerced section.
    """
    if not isinstance(brief, dict):
        return brief

    insufficient_sections: set[str] = set()
    insufficient_brief_keys: list[str] = []
    for brief_key, packet_key in _BRIEF_TO_PACKET_SECTION.items():
        section = packet.get(packet_key, {})
        if not isinstance(section, dict):
            continue
        if section.get("data_sufficient") is False:
            insufficient_sections.add(packet_key)
            insufficient_brief_keys.append(brief_key)
            if isinstance(brief.get(brief_key), dict):
                # (1) interpretive enums -> data_insufficient
                for k in list(brief[brief_key].keys()):
                    if k == "evidence":
                        continue
                    brief[brief_key][k] = "data_insufficient"
                # (2) free-text evidence -> neutral disclaimer
                brief[brief_key]["evidence"] = _NEUTRAL_EVIDENCE_TEXT

    # (3) drop dependent risk flags
    flags = brief.get("overall_risk_flags")
    if isinstance(flags, list):
        kept = []
        for flag in flags:
            section = _RISK_FLAG_TO_PACKET_SECTION.get(str(flag))
            if section is None or section not in insufficient_sections:
                kept.append(flag)
        brief["overall_risk_flags"] = kept

    # (4) downgrade tradable_setup if EVERY informative section is insufficient
    informative_sections = set(_BRIEF_TO_PACKET_SECTION.values())
    if informative_sections.issubset(insufficient_sections):
        if brief.get("tradable_setup") not in (None, "data_insufficient"):
            brief["tradable_setup"] = "data_insufficient"

    # (5) prepend coercion notice to rationale
    if insufficient_brief_keys:
        brief["coercion_notes"] = sorted(insufficient_brief_keys)
        rationale = str(brief.get("rationale") or "").strip()
        notice = (
            f"[COERCION OVERRIDE — BINDING]: The following sections were "
            f"flagged data_insufficient by the deterministic evidence packet "
            f"and have been coerced: {', '.join(sorted(insufficient_brief_keys))}. "
            f"Ignore any claim in the rationale below that depends on these "
            f"sections; treat them as data_insufficient regardless of phrasing."
        )
        brief["rationale"] = (
            f"{notice} {rationale}" if rationale else notice
        )

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
