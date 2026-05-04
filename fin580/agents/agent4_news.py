"""Agent 4 — News Intelligence (REDESIGNED per docs/AGENT4_5_REDESIGN.md).

Replaces the prior narrow novelty-check (`gdelt_disclosed: bool`) with a
structured catalyst brief that Agent 5's Bull/Bear/Arbiter debate consumes
as evidence.

News source: GDELT 2.0 (locked decision — see docs/AGENT4_5_REDESIGN.md
Appendix C for the rationale: NewsAPI free tier returns articles only up
to a month old, which is unusable for backfilling 2019-2023 cells).

Hard T-14 leakage cutoff is enforced upstream by gdelt_loader.fetch_articles.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fin580.agents.llm_client import chat
from fin580.agents.schemas import Agent2Out, Agent3Out, Agent4Out
from fin580.data.gdelt_loader import fetch_articles

MODEL_ID = "llama3.1-8b"  # Cerebras (DL #57)
PROMPT_PATH = Path(__file__).parent / "prompts" / "agent4_news.txt"
MAX_ARTICLES_TO_LLM = 30  # token-budget cap; orchestrator pre-filters by recency


def run(
    *,
    agent3_out: Agent3Out,
    sar_summary: dict,
    decision_date_T: date,
    prev_earnings_date: date,
    agent2_out: Agent2Out | None = None,  # New input — used for context, optional for backward compat
) -> Agent4Out:
    """Produce a structured news catalyst brief for the Bull/Bear/Arbiter board.

    The redesigned Agent 4 surfaces both positive and negative material
    catalysts — not just whether the SAR signal is "already disclosed."

    Defensive: returns a fallback Agent4Out (empty catalyst lists,
    `fallback_used=True`) if GDELT has no articles or the LLM call fails.
    Pipeline continues; downstream agents see "no salient news" rather
    than crashing the cell.
    """
    articles = fetch_articles(
        agent3_out.ticker, prev_earnings_date, decision_date_T
    )
    if not articles:
        return Agent4Out(
            ticker=agent3_out.ticker,
            n_articles_in_window=0,
            fallback_used=True,
            positive_catalysts=[],
            negative_catalysts=[],
            overall_sentiment="neutral",
            sar_complement="No GDELT-indexed articles in window — agent runs blind on news.",
            novelty_assessment="partial",  # Don't claim novelty without evidence
        )

    # Build LLM input — include Agent 2 forecast context if available so the
    # catalyst extraction can flag SAR/news contradictions.
    revenue_forecast_summary = None
    if agent2_out is not None:
        revenue_forecast_summary = {
            "our_estimate_usd": float(agent2_out.revenue_forecast_usd),
            "consensus_anchor_usd": float(agent2_out.components.get("consensus_anchor_usd", 0.0)),
            "divergence_pct": float(agent3_out.divergence_pct),
            "divergence_class": agent3_out.divergence_class,
        }

    llm_input = {
        "ticker": agent3_out.ticker,
        "sar_summary": sar_summary,
        "revenue_forecast_summary": revenue_forecast_summary,
        "articles": [
            {
                "article_id": a.article_id,
                "publish_date": a.publish_date.isoformat(),
                "title": a.title,
            }
            for a in articles[:MAX_ARTICLES_TO_LLM]
        ],
    }

    import json as _json
    try:
        response = chat(
            prompt=PROMPT_PATH.read_text(encoding="utf-8"),
            input_json=llm_input,
            model_id=MODEL_ID,
            temperature=0.0,
        )
    except (_json.JSONDecodeError, ValueError, RuntimeError) as e:
        # Defensive fallback: pipeline continues with neutral signal.
        return Agent4Out(
            ticker=agent3_out.ticker,
            n_articles_in_window=len(articles),
            fallback_used=True,
            positive_catalysts=[],
            negative_catalysts=[],
            overall_sentiment="neutral",
            sar_complement=f"Agent 4 LLM fallback ({type(e).__name__}): treating news as neutral.",
            novelty_assessment="partial",
        )

    # Stamp ticker + article count from authoritative inputs (don't trust LLM
    # to copy them correctly).
    response["ticker"] = agent3_out.ticker
    response["n_articles_in_window"] = len(articles)
    response.setdefault("fallback_used", False)

    # The new schema fields are optional, so missing ones default to None.
    # Defensive: if the LLM omits required-for-decision fields, fill safely.
    response.setdefault("positive_catalysts", [])
    response.setdefault("negative_catalysts", [])
    response.setdefault("overall_sentiment", "neutral")
    response.setdefault("sar_complement", "")
    response.setdefault("novelty_assessment", "partial")

    # Validate against the (extended) schema. If validation fails, the LLM
    # produced something the schema can't accept (e.g., bad sentiment value).
    try:
        return Agent4Out(**response)
    except Exception as e:
        # Last-resort fallback: schema validation failed.
        return Agent4Out(
            ticker=agent3_out.ticker,
            n_articles_in_window=len(articles),
            fallback_used=True,
            positive_catalysts=[],
            negative_catalysts=[],
            overall_sentiment="neutral",
            sar_complement=f"Agent 4 schema-validation fallback ({type(e).__name__}).",
            novelty_assessment="partial",
        )
