"""Agent 5 — Investment Board: Bull / Bear / Arbiter (spec Sections 4.1, 4.5).

Position sizing is a deterministic lookup; the LLM does not pick size.
Bull/Bear/Arbiter responses are persisted separately by the orchestrator
to support attribution analysis (spec Section 4.5)."""

from __future__ import annotations

from pathlib import Path

from fin580.agents.llm_client import chat
from fin580.agents.schemas import (
    Agent2Out,
    Agent3Out,
    Agent4Out,
    Agent5Out,
    BoardMemberOpinion,
    UpstreamAgentSummary,
)

PROMPTS_DIR = Path(__file__).parent / "prompts"

_BULL_PROMPT       = PROMPTS_DIR / "agent5_bull.txt"
_BEAR_PROMPT       = PROMPTS_DIR / "agent5_bear.txt"
_BULL_REBUTTAL     = PROMPTS_DIR / "agent5_bull_rebuttal.txt"
_BEAR_CHALLENGE    = PROMPTS_DIR / "agent5_bear_challenge.txt"
_ARBITER_PROMPT    = PROMPTS_DIR / "agent5_arbiter.txt"

# Provider + model-family diversity per spec Section 4.3.
# Per DL #53: Cerebras free tier doesn't host DeepSeek R1; HuggingFace does host
# the R1 distill variant. Arbiter routed via HF instead, preserving the
# DeepSeek R1 design choice.
MODEL_BULL    = "Qwen/Qwen2.5-72B-Instruct"                    # HuggingFace
MODEL_BEAR    = "meta-llama/Llama-3.3-70B-Instruct"            # HuggingFace
MODEL_ARBITER = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"   # HuggingFace — reasoning

import os as _os

# Conviction-to-size lookup. Override via env vars to customize position sizing:
#   FIN580_SIZE_HIGH   (default 0.15 = 15% of capital per trade)
#   FIN580_SIZE_MEDIUM (default 0.10 = 10%)
#   FIN580_SIZE_LOW    (default 0.05 = 5%)
CONVICTION_TO_SIZE = {
    "high":   float(_os.environ.get("FIN580_SIZE_HIGH",   "0.25")),
    "medium": float(_os.environ.get("FIN580_SIZE_MEDIUM", "0.10")),
    "low":    float(_os.environ.get("FIN580_SIZE_LOW",    "0.05")),
    "none":   0.0,
}


def _build_board_input(
    agent2: Agent2Out, agent3: Agent3Out, agent4: Agent4Out
) -> dict:
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


def run(
    *,
    agent2: Agent2Out,
    agent3: Agent3Out,
    agent4: Agent4Out,
) -> Agent5Out:
    board_input = _build_board_input(agent2, agent3, agent4)

    def _coerce_member(resp: dict, role: str) -> BoardMemberOpinion:
        # Truncate lists to schema-allowed max of 3 (LLMs sometimes return more)
        for k in ("key_evidence", "counter_evidence"):
            v = resp.get(k, [])
            if isinstance(v, list) and len(v) > 3:
                resp[k] = v[:3]
            elif not isinstance(v, list):
                resp[k] = []
        # Truncate reasoning_short to schema max
        rs = str(resp.get("reasoning_short", ""))[:1500]
        resp["reasoning_short"] = rs
        # Coerce direction / confidence to allowed Literals defensively
        d = str(resp.get("direction", "")).strip().lower()
        if d in ("long", "buy"):
            resp["direction"] = "long"
        elif d in ("short", "sell"):
            resp["direction"] = "short"
        else:
            resp["direction"] = "no_trade"
        c = str(resp.get("confidence", "")).strip().lower()
        resp["confidence"] = c if c in ("high", "medium", "low") else "low"
        resp["role"] = role
        return BoardMemberOpinion(**resp)

    bull_resp = chat(
        prompt=_BULL_PROMPT.read_text(),
        input_json=board_input,
        model_id=MODEL_BULL,
        temperature=0.0,
    )
    bull = _coerce_member(bull_resp, "bull")

    bear_resp = chat(
        prompt=_BEAR_PROMPT.read_text(),
        input_json=board_input,
        model_id=MODEL_BEAR,
        temperature=0.0,
    )
    bear = _coerce_member(bear_resp, "bear")

    arbiter_input = {
        **board_input,
        "bull_opinion": bull.model_dump(),
        "bear_opinion": bear.model_dump(),
    }
    arbiter_resp = chat(
        prompt=_ARBITER_PROMPT.read_text(),
        input_json=arbiter_input,
        model_id=MODEL_ARBITER,
        temperature=0.0,
    )

    # Defensive arbiter parsing — providers occasionally return slightly
    # different field names or values. Fall back to no_trade rather than
    # crash the whole cell.
    raw_decision = str(arbiter_resp.get("decision", "")).strip().lower()
    if raw_decision in ("long", "buy"):
        decision = "long"
    elif raw_decision in ("short", "sell"):
        decision = "short"
    else:
        decision = "no_trade"

    raw_tier = str(arbiter_resp.get("conviction_tier", "")).strip().lower()
    if raw_tier in ("high", "medium", "low", "none"):
        tier = raw_tier
    else:
        # Provider may return phrasings like "strong" / "moderate" / null.
        tier_map = {
            "strong": "high", "high_confidence": "high",
            "moderate": "medium", "modest": "medium", "med": "medium",
            "weak": "low", "low_confidence": "low",
        }
        tier = tier_map.get(raw_tier, "none")

    # Hard rule (deterministic Python, not LLM judgment): divergence_class gates
    # direction.  Long is only valid on beat; short is only valid on miss;
    # in_line always → no_trade.  The LLM opinion is corrected when it conflicts.
    if agent3.divergence_class == "in_line":
        decision = "no_trade"
        tier = "none"
    elif agent3.divergence_class in ("modest_beat", "strong_beat"):
        # Long-only zone: short not permitted here.
        if decision == "short":
            decision = "long"
    elif agent3.divergence_class in ("modest_miss", "strong_miss"):
        # Short-only zone: long not permitted here.
        if decision == "long":
            decision = "short"

    # Apply Agent 4 conviction modifier deterministically after arbiter tier is set.
    TIER_ORDER = ["none", "low", "medium", "high"]
    if decision != "no_trade" and tier in TIER_ORDER:
        if agent4.conviction_modifier == "upgrade_one_tier":
            idx = TIER_ORDER.index(tier)
            tier = TIER_ORDER[min(idx + 1, len(TIER_ORDER) - 1)]
        elif agent4.conviction_modifier == "downgrade_one_tier":
            idx = TIER_ORDER.index(tier)
            tier = TIER_ORDER[max(idx - 1, 0)]

    if decision == "no_trade":
        tier = "none"
        final_size = 0.0
    else:
        final_size = CONVICTION_TO_SIZE.get(tier, 0.0)
        if final_size == 0.0:
            # Directional trade with tier "none" is inconsistent — degrade to no_trade.
            decision = "no_trade"

    raw_summary = arbiter_resp.get("upstream_agent_summary", {})
    safe_summary = {
        "agent2_decisive": bool(raw_summary.get("agent2_decisive", False)),
        "agent3_decisive": bool(raw_summary.get("agent3_decisive", False)),
        "agent4_decisive": bool(raw_summary.get("agent4_decisive", False)),
        "agent2_weight": float(raw_summary.get("agent2_weight", 0.0) or 0.0),
        "agent3_weight": float(raw_summary.get("agent3_weight", 0.0) or 0.0),
        "agent4_weight": float(raw_summary.get("agent4_weight", 0.0) or 0.0),
    }
    # Clamp weights to [0, 1] to satisfy schema
    for k in ("agent2_weight", "agent3_weight", "agent4_weight"):
        safe_summary[k] = max(0.0, min(1.0, safe_summary[k]))

    arbiter_reasoning_text = str(arbiter_resp.get("arbiter_reasoning", "(no reasoning returned)"))[:3000]

    return Agent5Out(
        ticker=agent2.ticker,
        decision=decision,
        conviction_tier=tier,
        final_size_pct=final_size,
        bull_opinion=bull,
        bear_opinion=bear,
        arbiter_reasoning=arbiter_reasoning_text,
        upstream_agent_summary=UpstreamAgentSummary(**safe_summary),
    )
