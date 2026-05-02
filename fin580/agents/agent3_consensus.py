"""Agent 3 — Consensus Comparison. Llama 3.3 70B via Groq (spec Section 4.3)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fin580.agents.llm_client import chat
from fin580.agents.schemas import Agent2Out, Agent3Out
from fin580.data.ibes_pit import consensus_at_T

MODEL_ID = "llama3.1-8b"  # Cerebras (DL #57: Groq 100k TPD/free hit at M3)
PROMPT_PATH = Path(__file__).parent / "prompts" / "agent3_consensus.txt"


def run(
    *,
    agent2_out: Agent2Out,
    fiscal_quarter_end: date,
    decision_date_T: date,
) -> Agent3Out:
    cons = consensus_at_T(agent2_out.ticker, fiscal_quarter_end, decision_date_T)
    if cons["median_usd_m"] is None or cons["n_analysts"] == 0:
        return Agent3Out(
            ticker=agent2_out.ticker,
            our_estimate_usd=agent2_out.revenue_forecast_usd,
            consensus_median_usd=0.0,
            consensus_dispersion_usd=0.0,
            n_analysts_at_T_minus_14=0,
            divergence_pct=0.0,
            divergence_class="in_line",
            confidence="low",
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
    response = chat(
        prompt=PROMPT_PATH.read_text(),
        input_json=llm_input,
        model_id=MODEL_ID,
        temperature=0.0,
    )

    # Codex Issue 1 fix: divergence_pct, divergence_class, and confidence are
    # the inputs to the trade gate. They MUST be deterministic Python — never
    # LLM output — to preserve the paper's deterministic-numerical-core claim
    # (analogous to Agent 2's deterministic revenue override per DL #43).
    div_pct = (agent2_out.revenue_forecast_usd - consensus_usd) / consensus_usd * 100.0
    if div_pct > 15.0:
        div_class = "strong_beat"
    elif div_pct > 5.0:
        div_class = "modest_beat"
    elif div_pct >= -5.0:
        div_class = "in_line"
    elif div_pct >= -15.0:
        div_class = "modest_miss"
    else:
        div_class = "strong_miss"
    n_analysts = cons["n_analysts"]
    dispersion_ratio = dispersion_usd / consensus_usd if consensus_usd > 0 else 1.0
    if n_analysts >= 10 and dispersion_ratio < 0.03:
        conf = "high"
    elif n_analysts >= 5:
        conf = "medium"
    else:
        conf = "low"

    response["ticker"] = agent2_out.ticker
    response["our_estimate_usd"] = agent2_out.revenue_forecast_usd
    response["consensus_median_usd"] = consensus_usd
    response["consensus_dispersion_usd"] = dispersion_usd
    response["n_analysts_at_T_minus_14"] = n_analysts
    response["divergence_pct"] = round(div_pct, 2)
    response["divergence_class"] = div_class
    response["confidence"] = conf
    return Agent3Out(**response)
