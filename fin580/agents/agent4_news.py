"""Agent 4 — News Verification (GDELT only). Llama 3.3 70B via Groq.
Hard T-14 cutoff enforced upstream by gdelt_loader (spec DL #7)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fin580.agents.llm_client import chat
from fin580.agents.schemas import Agent3Out, Agent4Out
from fin580.data.gdelt_loader import fetch_articles

MODEL_ID = "gpt-4o-mini"  # v2.5: OpenAI mini tier (was Cerebras llama3.1-8b)
PROMPT_PATH = Path(__file__).parent / "prompts" / "agent4_news.txt"


def run(
    *,
    agent3_out: Agent3Out,
    sar_summary: dict,
    decision_date_T: date,
    prev_earnings_date: date,
) -> Agent4Out:
    articles = fetch_articles(
        agent3_out.ticker, prev_earnings_date, decision_date_T
    )
    if not articles:
        return Agent4Out(
            ticker=agent3_out.ticker,
            n_articles_in_window=0,
            gdelt_disclosed=False,
            matching_article_ids=[],
            conviction_modifier="none",
            reasoning="No GDELT-indexed articles for this ticker in the window.",
        )
    llm_input = {
        "ticker": agent3_out.ticker,
        "sar_summary": sar_summary,
        "articles": [
            {
                "article_id": a.article_id,
                "publish_date": a.publish_date.isoformat(),
                "title": a.title,
            }
            for a in articles[:30]  # Trim to top 30 to fit token budget
        ],
    }
    import json as _json
    try:
        response = chat(
            prompt=PROMPT_PATH.read_text(),
            input_json=llm_input,
            model_id=MODEL_ID,
            temperature=0.0,
        )
    except (_json.JSONDecodeError, ValueError, RuntimeError) as e:
        # Defensive fallback: Agent 4 LLM call failed (malformed JSON or
        # provider error). Return the most permissive no-disclosure default
        # so the rest of the cell pipeline can proceed.
        return Agent4Out(
            ticker=agent3_out.ticker,
            n_articles_in_window=len(articles),
            gdelt_disclosed=False,
            matching_article_ids=[],
            conviction_modifier="none",
            reasoning=f"Agent 4 LLM fallback ({type(e).__name__}): no disclosure assumed.",
        )
    response["ticker"] = agent3_out.ticker
    response["n_articles_in_window"] = len(articles)
    return Agent4Out(**response)
