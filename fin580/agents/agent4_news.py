"""Agent 4 — News Verification (GDELT only). Llama 3.3 70B via Groq.
Hard T-14 cutoff enforced upstream by gdelt_loader (spec DL #7)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fin580.agents.llm_client import chat
from fin580.agents.schemas import Agent3Out, Agent4Out
from fin580.data.gdelt_loader import fetch_articles

MODEL_ID = "meta-llama/Llama-3.3-70B-Instruct"  # HuggingFace Inference API
PROMPT_PATH = Path(__file__).parent / "prompts" / "agent4_news.txt"

# >30 articles in the pre-earnings window signals elevated market awareness even
# without explicit GDELT disclosure. Caught 3 of 7 historical losing trades.
HIGH_ARTICLE_THRESHOLD = 30


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
            conviction_modifier="upgrade_one_tier",
            reasoning=(
                "Zero GDELT-indexed articles in window — satellite signal has no "
                "corresponding public news disclosure. Novel, uncontaminated signal: "
                "upgrade conviction one tier."
            ),
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
    out = Agent4Out(**response)

    # Hard override: even without explicit disclosure, >30 articles in the
    # pre-earnings window signals elevated market awareness. The information
    # edge is degraded. Downgrade conviction one tier deterministically.
    # This caught 3 of 7 historical losing trades (OVV 21Q2, EOG 21Q2, OXY 21Q4).
    if len(articles) > HIGH_ARTICLE_THRESHOLD and out.conviction_modifier != "downgrade_one_tier":
        out = Agent4Out(
            ticker=out.ticker,
            n_articles_in_window=out.n_articles_in_window,
            gdelt_disclosed=out.gdelt_disclosed,
            matching_article_ids=out.matching_article_ids,
            conviction_modifier="downgrade_one_tier",
            reasoning=(
                f"{out.reasoning} | OVERRIDE: {len(articles)} articles in window "
                f"exceeds high-awareness threshold ({HIGH_ARTICLE_THRESHOLD}). "
                "Elevated market coverage degrades information edge — downgrade one tier."
            ),
        )
    return out
