"""Strategy 2 — Ablation of Strategy 1 with Agent 4 stubbed.
Per spec Section 6.1, classified as ablation, not baseline."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fin580.agents import (
    agent1_gis,
    agent2_revenue,
    agent3_consensus,
    agent5_board,
)
from fin580.agents.schemas import Agent4Out, TradeDecision


def signal(
    *,
    ticker: str,
    fiscal_quarter_end: date,
    decision_date_T: date,
    prev_earnings_date: date,
    run_dir: Path,
    cm_label: str = "target",
) -> TradeDecision:
    a1 = agent1_gis.run(
        ticker=ticker,
        fiscal_quarter_end=fiscal_quarter_end,
        decision_date_T=decision_date_T,
        cm_label=cm_label,
    )
    a2 = agent2_revenue.run(agent1_out=a1, target_quarter_end=fiscal_quarter_end)
    a3 = agent3_consensus.run(
        agent2_out=a2,
        fiscal_quarter_end=fiscal_quarter_end,
        decision_date_T=decision_date_T,
    )
    # Apply same gated execution as Strategy 1 (DL #61)
    if a3.divergence_class not in ("modest_beat", "strong_beat"):
        return TradeDecision(
            ticker=ticker, decision_date_T=decision_date_T,
            direction="no_trade", size_pct=0.0,
        )
    # Agent 4 stubbed (the ablation): always returns no GDELT disclosure
    a4 = Agent4Out(
        ticker=ticker, n_articles_in_window=0, gdelt_disclosed=False,
        matching_article_ids=[], conviction_modifier="none",
        reasoning="Strategy 2 ablation: Agent 4 stubbed (no GDELT input).",
    )
    a5 = agent5_board.run(agent2=a2, agent3=a3, agent4=a4)
    return TradeDecision(
        ticker=ticker, decision_date_T=decision_date_T,
        direction=a5.decision, size_pct=a5.final_size_pct,
    )
