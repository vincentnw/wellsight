"""Per-cell sequential agent pipeline with JSON persistence (spec Section 5).

Includes Codex Round-5 hardening:
  - cell_complete() validates pydantic schemas + rejects top-level errors +
    requires cell_results.parquet row presence
  - per-component Agent 5 logging (Bull / Bear / Arbiter as separate parquet
    rows) for attribution analysis (spec Section 4.5)
  - quality_log.csv per cell"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from fin580.agents import (
    agent1_gis,
    agent2_revenue,
    agent3_consensus,
    agent4_news,
    agent5_board,
)
from fin580.agents.schemas import (
    Agent1Out,
    Agent2Out,
    Agent3Out,
    Agent4Out,
    Agent5Out,
    BoardMemberOpinion,
    CellResult,
    UpstreamAgentSummary,
)

_AGENT_SCHEMAS = {
    "agent1": Agent1Out,
    "agent2": Agent2Out,
    "agent3": Agent3Out,
    "agent4": Agent4Out,
    "agent5": Agent5Out,
}


def _persist(obj, run_dir: Path, ticker: str, q_end: date, name: str) -> Path:
    out_dir = run_dir / "strategy_01" / "agent_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{ticker}_{q_end.isoformat()}_{name}.json"
    p.write_text(obj.model_dump_json(indent=2))
    return p


def _persist_agent5_components(
    a5: Agent5Out, run_dir: Path, ticker: str, q_end: date
) -> None:
    """Spec Section 4.5: Bull/Bear/Arbiter persisted as separate parquet rows
    for downstream attribution analysis (P10)."""
    rows = []
    for opinion, role in [
        (a5.bull_opinion, "bull"),
        (a5.bear_opinion, "bear"),
    ]:
        rows.append({
            "ticker": ticker,
            "fiscal_quarter_end": q_end.isoformat(),
            "role": role,
            "direction": opinion.direction,
            "confidence": opinion.confidence,
            "key_evidence": " | ".join(opinion.key_evidence),
            "counter_evidence": " | ".join(opinion.counter_evidence),
            "reasoning_short": opinion.reasoning_short,
            "decisive_for_arbiter": False,
        })
    rows.append({
        "ticker": ticker,
        "fiscal_quarter_end": q_end.isoformat(),
        "role": "arbiter",
        "direction": a5.decision,
        "confidence": a5.conviction_tier,
        "key_evidence": "",
        "counter_evidence": "",
        "reasoning_short": a5.arbiter_reasoning,
        "decisive_for_arbiter": True,
    })
    out_path = run_dir / "strategy_01" / "agent5_components.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_new = pd.DataFrame(rows)
    if out_path.exists():
        df_existing = pd.read_parquet(out_path)
        mask = ~(
            (df_existing["ticker"] == ticker)
            & (df_existing["fiscal_quarter_end"] == q_end.isoformat())
        )
        df_combined = pd.concat([df_existing[mask], df_new], ignore_index=True)
    else:
        df_combined = df_new
    df_combined.to_parquet(out_path)


def _append_quality_log(
    run_dir: Path,
    ticker: str,
    q_end: date,
    low_quality_flag: bool,
    reason: str,
) -> None:
    log_path = run_dir / "quality_log.csv"
    header_needed = not log_path.exists()
    with open(log_path, "a") as f:
        if header_needed:
            f.write("ticker,fiscal_quarter_end,low_quality_flag,reason\n")
        clean_reason = reason.replace(",", ";").replace("\n", " ")
        f.write(
            f"{ticker},{q_end.isoformat()},{low_quality_flag},{clean_reason}\n"
        )


def _append_cell_result(cell: CellResult, run_dir: Path) -> None:
    results_path = run_dir / "strategy_01" / "cell_results.parquet"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    new_row = pd.DataFrame([{
        "ticker": cell.ticker,
        "fiscal_quarter_end": cell.fiscal_quarter_end.isoformat(),
        "decision_date_T": cell.decision_date_T.isoformat(),
        "decision": cell.decision,
        "conviction_tier": cell.conviction_tier,
        "final_size_pct": cell.final_size_pct,
        "low_quality_flag": cell.low_quality_flag,
        "error": cell.error or "",
    }])
    if results_path.exists():
        df = pd.read_parquet(results_path)
        mask = ~(
            (df["ticker"] == cell.ticker)
            & (df["fiscal_quarter_end"] == cell.fiscal_quarter_end.isoformat())
        )
        df = pd.concat([df[mask], new_row], ignore_index=True)
    else:
        df = new_row
    df.to_parquet(results_path)


def cell_complete(run_dir: Path, ticker: str, q_end: date) -> bool:
    """Spec Section 5.2: cell complete iff (a) all 5 JSONs exist, (b) each
    parses against its pydantic schema, (c) no JSON has top-level `error`,
    (d) cell_results.parquet has a row for this cell."""
    out_dir = run_dir / "strategy_01" / "agent_outputs"
    for name in ["agent1", "agent2", "agent3", "agent4", "agent5"]:
        p = out_dir / f"{ticker}_{q_end.isoformat()}_{name}.json"
        if not p.exists():
            return False
        try:
            payload = json.loads(p.read_text())
        except json.JSONDecodeError:
            return False
        if isinstance(payload, dict) and "error" in payload:
            return False
        try:
            _AGENT_SCHEMAS[name].model_validate(payload)
        except Exception:
            return False
    results_path = run_dir / "strategy_01" / "cell_results.parquet"
    if not results_path.exists():
        return False
    df = pd.read_parquet(results_path)
    matched = df[
        (df["ticker"] == ticker)
        & (df["fiscal_quarter_end"] == q_end.isoformat())
    ]
    return len(matched) > 0


def run_cell(
    *,
    ticker: str,
    fiscal_quarter_end: date,
    decision_date_T: date,
    prev_earnings_date: date,
    run_dir: Path,
    cm_label: str = "target",
) -> CellResult:
    if cell_complete(run_dir, ticker, fiscal_quarter_end):
        a5_path = (
            run_dir
            / "strategy_01"
            / "agent_outputs"
            / f"{ticker}_{fiscal_quarter_end.isoformat()}_agent5.json"
        )
        a5 = Agent5Out.model_validate_json(a5_path.read_text())
        return CellResult(
            ticker=ticker,
            fiscal_quarter_end=fiscal_quarter_end,
            decision_date_T=decision_date_T,
            decision=a5.decision,
            conviction_tier=a5.conviction_tier,
            final_size_pct=a5.final_size_pct,
        )

    a1 = agent1_gis.run(
        ticker=ticker,
        fiscal_quarter_end=fiscal_quarter_end,
        decision_date_T=decision_date_T,
        cm_label=cm_label,
    )
    _persist(a1, run_dir, ticker, fiscal_quarter_end, "agent1")

    try:
        a2 = agent2_revenue.run(
            agent1_out=a1, target_quarter_end=fiscal_quarter_end
        )
        _persist(a2, run_dir, ticker, fiscal_quarter_end, "agent2")

        a3 = agent3_consensus.run(
            agent2_out=a2,
            fiscal_quarter_end=fiscal_quarter_end,
            decision_date_T=decision_date_T,
        )
        _persist(a3, run_dir, ticker, fiscal_quarter_end, "agent3")

        # DL #61 short-circuit REMOVED in the Agent 4+5 redesign branch.
        # Per docs/AGENT4_5_REDESIGN.md, Agent 3's divergence_class is now
        # informational only — Agent 4 (catalyst brief) and Agent 5 (Bull/Bear/
        # Arbiter with conviction_score) run on EVERY cell. The mechanical
        # trade-selection layer in fin580/backtest/runner.py applies the
        # top-K-per-cycle budget to actually fire trades.

        a4 = agent4_news.run(
            agent3_out=a3,
            sar_summary={
                "n_newly_active": a1.n_newly_active,
                "n_continuously_active": a1.n_continuously_active,
                "share_active": a1.share_active,
                "relative_activity_delta": a1.relative_activity_delta,
            },
            decision_date_T=decision_date_T,
            prev_earnings_date=prev_earnings_date,
            agent2_out=a2,  # Redesigned Agent 4: forecast context informs catalyst extraction
        )
        _persist(a4, run_dir, ticker, fiscal_quarter_end, "agent4")

        a5 = agent5_board.run(agent2=a2, agent3=a3, agent4=a4)
        _persist(a5, run_dir, ticker, fiscal_quarter_end, "agent5")
        _persist_agent5_components(a5, run_dir, ticker, fiscal_quarter_end)

        cell = CellResult(
            ticker=ticker,
            fiscal_quarter_end=fiscal_quarter_end,
            decision_date_T=decision_date_T,
            decision=a5.decision,
            conviction_tier=a5.conviction_tier,
            final_size_pct=a5.final_size_pct,
            conviction_score=a5.conviction_score,
        )
        _append_cell_result(cell, run_dir)
        _append_quality_log(run_dir, ticker, fiscal_quarter_end, False, "ok")
        return cell

    except Exception as e:
        err_path = (
            run_dir
            / "strategy_01"
            / "agent_outputs"
            / f"{ticker}_{fiscal_quarter_end.isoformat()}_error.json"
        )
        err_path.parent.mkdir(parents=True, exist_ok=True)
        err_path.write_text(
            json.dumps({"error": str(e), "type": type(e).__name__}, indent=2)
        )
        cell = CellResult(
            ticker=ticker,
            fiscal_quarter_end=fiscal_quarter_end,
            decision_date_T=decision_date_T,
            decision="no_trade",
            conviction_tier="none",
            final_size_pct=0.0,
            low_quality_flag=True,
            error=str(e),
        )
        _append_cell_result(cell, run_dir)
        _append_quality_log(
            run_dir, ticker, fiscal_quarter_end, True, str(e)[:80]
        )
        return cell
