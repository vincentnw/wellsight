"""Agent 5 — Investment Board: Bull / Bear / Arbiter.

REDESIGNED per docs/AGENT4_5_REDESIGN.md:
  - Bull on Cerebras qwen-3-235b (advocacy, strong reasoner)
  - Bear on Cerebras llama3.1-8b (skepticism, fast)
  - Arbiter on Gemini 2.5 Flash (cross-provider judgment, restores model-family
    diversity that DL #59 collapsed)
  - Arbiter outputs `conviction_score` 0-100 (NEW — used by trade-selection
    layer for top-K-per-cycle ranking)
  - DL #56 hard guardrail REMOVED — Arbiter sees all cells, decides on all.
    The mechanical trade-selection layer in fin580/backtest/runner.py
    enforces the budget cap, not Agent 5.

Position sizing is still a deterministic lookup; the LLM does not pick size.
"""

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

# Model stack — see docs/AGENT4_5_REDESIGN.md Section 2 for rationale.
MODEL_BULL = "qwen-3-235b-a22b-instruct-2507"   # Cerebras, advocacy
MODEL_BEAR = "llama3.1-8b"                       # Cerebras, skepticism
MODEL_ARBITER = "gemini-2.5-flash"               # Google AI Studio (free tier 250 RPD / 10 RPM)

CONVICTION_TO_SIZE = {"high": 0.15, "medium": 0.10, "low": 0.05, "none": 0.0}

# Pre-registered conviction_score → tier thresholds (LOCKED before 2024 eval).
# See docs/AGENT4_5_REDESIGN.md Section 3 "Score calibration."
SCORE_TIER_THRESHOLDS = {
    "high":   75.0,
    "medium": 60.0,
    "low":    45.0,
}


def _summarize_catalysts(items: list | None, max_items: int = 3) -> list[dict]:
    if not items:
        return []
    out = []
    for c in items[:max_items]:
        if hasattr(c, "model_dump"):
            d = c.model_dump()
        else:
            d = dict(c)
        out.append({
            "summary": d.get("summary", ""),
            "article_date": d.get("article_date", ""),
        })
    return out


def _build_board_input(
    agent2: Agent2Out, agent3: Agent3Out, agent4: Agent4Out
) -> dict:
    """Build the input package the Bull/Bear/Arbiter LLMs see.

    The redesigned Agent 4 produces structured catalysts; this function
    surfaces them to the board. Falls back gracefully on legacy Agent 4
    outputs (no catalysts) without crashing."""
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
            "n_articles_in_window": agent4.n_articles_in_window,
            "fallback_used": bool(agent4.fallback_used),
            "overall_sentiment": agent4.overall_sentiment or "neutral",
            "sar_complement": agent4.sar_complement or "",
            "novelty_assessment": agent4.novelty_assessment or "partial",
            "positive_catalysts": _summarize_catalysts(agent4.positive_catalysts),
            "negative_catalysts": _summarize_catalysts(agent4.negative_catalysts),
        },
    }


def _coerce_member(resp: dict, role: str) -> BoardMemberOpinion:
    # Truncate lists to schema-allowed max of 3 (LLMs sometimes return more)
    for k in ("key_evidence", "counter_evidence"):
        v = resp.get(k, [])
        if isinstance(v, list) and len(v) > 3:
            resp[k] = v[:3]
        elif not isinstance(v, list):
            resp[k] = []
    rs = str(resp.get("reasoning_short", ""))[:1500]
    resp["reasoning_short"] = rs
    d = str(resp.get("direction", "")).strip().lower()
    resp["direction"] = "long" if d in ("long", "buy") else "no_trade"
    c = str(resp.get("confidence", "")).strip().lower()
    resp["confidence"] = c if c in ("high", "medium", "low") else "low"
    resp["role"] = role
    return BoardMemberOpinion(**resp)


def _score_to_tier(score: float) -> str:
    """Apply pre-registered thresholds to map conviction_score → tier."""
    if score >= SCORE_TIER_THRESHOLDS["high"]:
        return "high"
    if score >= SCORE_TIER_THRESHOLDS["medium"]:
        return "medium"
    if score >= SCORE_TIER_THRESHOLDS["low"]:
        return "low"
    return "none"


def run(
    *,
    agent2: Agent2Out,
    agent3: Agent3Out,
    agent4: Agent4Out,
) -> Agent5Out:
    board_input = _build_board_input(agent2, agent3, agent4)

    bull_resp = chat(
        prompt=(PROMPTS_DIR / "agent5_bull.txt").read_text(encoding="utf-8"),
        input_json=board_input,
        model_id=MODEL_BULL,
        temperature=0.0,
    )
    bull = _coerce_member(bull_resp, "bull")

    bear_resp = chat(
        prompt=(PROMPTS_DIR / "agent5_bear.txt").read_text(encoding="utf-8"),
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
        prompt=(PROMPTS_DIR / "agent5_arbiter.txt").read_text(encoding="utf-8"),
        input_json=arbiter_input,
        model_id=MODEL_ARBITER,
        temperature=0.0,
    )

    # Defensive arbiter parsing — Gemini sometimes returns slightly different
    # field shapes. Fall back gracefully.
    raw_decision = str(arbiter_resp.get("decision", "")).strip().lower()
    decision = "long" if raw_decision in ("long", "buy") else "no_trade"

    # Conviction score (0-100) — NEW required field from Arbiter.
    raw_score = arbiter_resp.get("conviction_score")
    try:
        score = float(raw_score) if raw_score is not None else 0.0
    except (TypeError, ValueError):
        score = 0.0
    score = max(0.0, min(100.0, score))  # Clamp to [0, 100]

    # Derive tier from score (frozen thresholds — see docs/AGENT4_5_REDESIGN.md).
    # Arbiter is also asked to output its own tier; we trust the score and use
    # the LLM's tier only as a sanity check / log.
    derived_tier = _score_to_tier(score)
    raw_tier = str(arbiter_resp.get("conviction_tier", "")).strip().lower()
    if raw_tier in ("high", "medium", "low", "none"):
        # Use LLM's tier if it agrees with the score-derived one; otherwise
        # the score is authoritative (deterministic, audit-friendly).
        tier = derived_tier
    else:
        tier = derived_tier

    # NOTE: DL #56 hard guardrail REMOVED here. The Arbiter is now the sole
    # decision-maker on long vs no_trade. The mechanical trade-selection
    # layer in fin580/backtest/runner.py applies the top-K-per-cycle budget
    # to actually fire trades.

    if decision == "no_trade":
        tier = "none"
        final_size = 0.0
    else:
        # If Arbiter says long but score is below "low" threshold, downgrade
        # to no_trade (decision and score must be consistent — score wins).
        if tier == "none":
            decision = "no_trade"
            final_size = 0.0
        else:
            final_size = CONVICTION_TO_SIZE[tier]

    raw_summary = arbiter_resp.get("upstream_agent_summary", {})
    safe_summary = {
        "agent2_decisive": bool(raw_summary.get("agent2_decisive", False)),
        "agent3_decisive": bool(raw_summary.get("agent3_decisive", False)),
        "agent4_decisive": bool(raw_summary.get("agent4_decisive", False)),
        "agent2_weight": float(raw_summary.get("agent2_weight", 0.0) or 0.0),
        "agent3_weight": float(raw_summary.get("agent3_weight", 0.0) or 0.0),
        "agent4_weight": float(raw_summary.get("agent4_weight", 0.0) or 0.0),
    }
    for k in ("agent2_weight", "agent3_weight", "agent4_weight"):
        safe_summary[k] = max(0.0, min(1.0, safe_summary[k]))

    arbiter_reasoning_text = str(
        arbiter_resp.get("arbiter_reasoning", "(no reasoning returned)")
    )[:3000]

    return Agent5Out(
        ticker=agent2.ticker,
        decision=decision,
        conviction_tier=tier,
        final_size_pct=final_size,
        bull_opinion=bull,
        bear_opinion=bear,
        arbiter_reasoning=arbiter_reasoning_text,
        upstream_agent_summary=UpstreamAgentSummary(**safe_summary),
        conviction_score=score,
    )
