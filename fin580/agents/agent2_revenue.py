"""Agent 2 — Revenue Forecast. Deterministic numerical core (reusing
fin580/phase2/revenue_forecast.py) + Qwen 2.5 72B for qualitative outlook.

The LLM does NOT generate the number (spec Section 4.3, DL #43). The numerical
forecast is computed deterministically; the LLM produces only the qualitative
outlook + key_drivers, and we overwrite the LLM-returned number with the
deterministic one before constructing Agent2Out."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from fin580.agents.llm_client import chat
from fin580.agents.schemas import Agent1Out, Agent2Out
from fin580.data.ibes_pit import consensus_at_T
from fin580.data.wti_loader import avg_wti_window
from fin580.phase2.revenue_forecast import (
    ALPHA_PRIMARY,
    DEFAULT_PERMIAN_REVENUE_SHARE,
    DEFAULT_REALIZED_PRICE_DIFF,
    DEFAULT_WELLS_PER_PAD,
    forecast_revenue,
)

MODEL_ID = "gpt-4o-mini"  # v2.5 update: all-OpenAI stack (was Cerebras qwen-3-235b)
PROMPT_PATH = Path(__file__).parent / "prompts" / "agent2_revenue.txt"

# Last-quarter Permian production base per ticker (rough TTM averages, in boe/d).
# Documented in spec Section 12 as not strictly point-in-time; acceptable
# placeholder under project-goal framing.
LAST_QUARTER_PRODUCTION_BASE = {
    "FANG": 470_000, "EOG": 1_000_000, "DVN": 660_000, "CTRA": 670_000,
    "OXY": 1_300_000, "MTDR": 160_000, "PR": 320_000, "OVV": 600_000,
    "SM": 160_000, "CRGY": 220_000,
}


def _load_prompt() -> str:
    return PROMPT_PATH.read_text()


def run(*, agent1_out: Agent1Out, target_quarter_end: date,
        alpha: float | None = None) -> Agent2Out:
    if alpha is None:
        # Allow override via env var so runner can pass alpha to ablations
        # without code edits (DL #55 alpha=0 ablation, M7).
        import os
        env_alpha = os.environ.get("FIN580_ALPHA")
        alpha = float(env_alpha) if env_alpha else ALPHA_PRIMARY
    ticker = agent1_out.ticker
    decision_date_T = agent1_out.decision_date_T

    wti_window_start = decision_date_T - timedelta(days=90)
    wti_avg = avg_wti_window(wti_window_start, decision_date_T)

    base_prod = LAST_QUARTER_PRODUCTION_BASE.get(ticker, 200_000)

    # DL #54 — consensus-anchored mode. Fetch IBES consensus revenue at T-14;
    # compute drilling signal as relative_activity_delta normalized by trailing
    # 4Q average; pass to forecast_revenue for the anchored formula.
    cons = consensus_at_T(ticker, target_quarter_end, decision_date_T)
    consensus_anchor_usd: float | None = None
    drilling_signal: float | None = None
    if cons.get("median_usd_m") is not None and cons.get("n_analysts", 0) >= 1:
        consensus_anchor_usd = float(cons["median_usd_m"]) * 1e6
        # Recover trailing-4Q average from Agent 1: relative_delta = active − trailing_avg
        trailing_avg = float(agent1_out.absolute_active) - agent1_out.relative_activity_delta
        if trailing_avg > 1.0:
            drilling_signal = agent1_out.relative_activity_delta / trailing_avg
        else:
            drilling_signal = 0.0

    fc = forecast_revenue(
        ticker=ticker,
        target_quarter_end=target_quarter_end,
        decision_date_T=decision_date_T,
        new_active_pads=agent1_out.n_newly_active,
        continuously_active_pads=agent1_out.n_continuously_active,
        last_quarter_permian_production_boe_d=base_prod,
        avg_wti_pre_T14_usd_per_bbl=wti_avg,
        consensus_anchor_usd=consensus_anchor_usd,
        drilling_signal=drilling_signal,
        alpha=alpha,
    )

    components = {
        "mode": fc.inputs.get("mode", "unknown"),
        "alpha": alpha,
        "consensus_anchor_usd": consensus_anchor_usd,
        "drilling_signal_raw": drilling_signal,
        "drilling_signal_clipped": fc.inputs.get("drilling_signal_clipped"),
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
    response = chat(
        prompt=_load_prompt(),
        input_json=llm_input,
        model_id=MODEL_ID,
        temperature=0.0,
    )

    # Force the deterministic number — never trust the LLM with it.
    response["revenue_forecast_usd"] = fc.total_revenue_usd
    response["components"] = components
    response["ticker"] = ticker
    return Agent2Out(**response)
