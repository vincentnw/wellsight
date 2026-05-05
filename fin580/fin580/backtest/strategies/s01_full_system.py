"""Strategy 1 — Full agent stack. Wraps the orchestrator (spec Section 6.1)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fin580.agents import orchestrator
from fin580.agents.schemas import TradeDecision


def signal(
    *,
    ticker: str,
    fiscal_quarter_end: date,
    decision_date_T: date,
    prev_earnings_date: date,
    run_dir: Path,
    cm_label: str = "target",
) -> TradeDecision:
    cell = orchestrator.run_cell(
        ticker=ticker,
        fiscal_quarter_end=fiscal_quarter_end,
        decision_date_T=decision_date_T,
        prev_earnings_date=prev_earnings_date,
        run_dir=run_dir,
        cm_label=cm_label,
    )
    return TradeDecision(
        ticker=cell.ticker,
        decision_date_T=cell.decision_date_T,
        direction=cell.decision,
        size_pct=cell.final_size_pct,
    )
