"""v2.5 vs v1 diagnostic decomposition table.

Combines the 6 yearly v2.5 run dirs into one cell-level frame, attaches
every diagnostic we have access to (SAR fields, divergence stats,
dispersion-adjusted surprise, WTI 4w return, actual revenue beat, Agent 5
voting), then labels each row by v1/v2.5 set membership:
  - inherited:   long in BOTH v1 and v2.5
  - v2.5_only:   long in v2.5 but no_trade in v1 (the marginal new trades)
  - dropped:     long in v1 but no_trade in v2.5

Outputs:
  runs/inference/v2_5_diagnostic_table.csv  (all 23 v2.5 longs + 4 v1-only drops)
  Console summary by set + W/L + signal_confidence tier.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fin580.backtest.pnl_engine import compute_trade_pnl
from fin580.data.crsp_loader import load_combined, price_at
from fin580.inference.pnl import _earnings_dates, _exit_price
from fin580.inference.signal_confidence import attach_signal_confidence
from fin580.inference.wti_veto import wti_4w_return_at_T

V2_5_RUNS = [
    ("2019", ROOT / "runs" / "2026-05-04-strategy1-2019Q1_2019Q4-target-realsar-v2_5"),
    ("2020", ROOT / "runs" / "2026-05-04-strategy1-2020Q1_2020Q4-target-realsar-v2_5"),
    ("2021", ROOT / "runs" / "2026-05-04-strategy1-2021Q1_2021Q4-target-realsar-v2_5"),
    ("2022", ROOT / "runs" / "2026-05-04-strategy1-2022Q1_2022Q4-target-realsar-v2_5"),
    ("2023", ROOT / "runs" / "2026-05-04-strategy1-2023Q1_2023Q4-target-realsar-v2_5"),
    ("2024", ROOT / "runs" / "2026-05-04-strategy1-2024Q1_2024Q4-target-realsar-v2_5"),
]

V1_LONGS = {
    ("SM", "2019-12-31"), ("OXY", "2019-12-31"),
    ("OVV", "2021-03-31"), ("CTRA", "2021-09-30"), ("OXY", "2021-09-30"), ("OVV", "2021-09-30"),
    ("CTRA", "2022-09-30"),
    ("OVV", "2023-06-30"),
    ("FANG", "2024-06-30"), ("PR", "2024-09-30"),
}


def _read_json(p: Path) -> dict | None:
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _load_compustat_actuals() -> pd.DataFrame:
    p = ROOT / "phase1" / "output" / "compustat_fundq.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    return (
        df[["tic", "datadate", "saleq"]]
        .rename(columns={
            "tic": "ticker",
            "datadate": "fiscal_quarter_end",
            "saleq": "actual_revenue_usd_m",
        })
        .assign(actual_revenue_usd=lambda d: d["actual_revenue_usd_m"] * 1_000_000.0)
    )[["ticker", "fiscal_quarter_end", "actual_revenue_usd"]]


def _agent_outputs(run_dir: Path, ticker: str, fpe_str: str) -> dict:
    out_dir = run_dir / "strategy_01" / "agent_outputs"
    base = f"{ticker}_{fpe_str}"
    a1 = _read_json(out_dir / f"{base}_agent1.json") or {}
    a2 = _read_json(out_dir / f"{base}_agent2.json") or {}
    a3 = _read_json(out_dir / f"{base}_agent3.json") or {}
    a4 = _read_json(out_dir / f"{base}_agent4.json") or {}
    a5 = _read_json(out_dir / f"{base}_agent5.json") or {}
    a2_components = a2.get("components", {}) if isinstance(a2.get("components"), dict) else {}

    bull = a5.get("bull_opinion", "")
    bear = a5.get("bear_opinion", "")

    def _opinion_dir(s: str) -> str:
        if not isinstance(s, str):
            return "?"
        s_low = s.lower()
        if "'direction': 'long'" in s_low or '"direction": "long"' in s_low:
            return "long"
        if "'direction': 'no_trade'" in s_low or '"direction": "no_trade"' in s_low:
            return "no_trade"
        return "?"

    bull_dir = _opinion_dir(bull)
    bear_dir = _opinion_dir(bear)
    arbiter_decision = a5.get("decision", "?")
    arbiter_reasoning = a5.get("arbiter_reasoning", "")
    arbiter_overruled_bear = (bear_dir == "no_trade" and arbiter_decision == "long")

    return {
        "absolute_active": a1.get("absolute_active"),
        "n_newly_active": a1.get("n_newly_active"),
        "n_continuously_active": a1.get("n_continuously_active"),
        "n_idle": a1.get("n_idle"),
        "share_active": a1.get("share_active"),
        "relative_activity_delta": a1.get("relative_activity_delta"),
        "revenue_forecast_usd": a2.get("revenue_forecast_usd"),
        "alpha": a2_components.get("alpha"),
        "drilling_signal_clipped": a2_components.get("drilling_signal_clipped"),
        "consensus_median_usd": a3.get("consensus_median_usd"),
        "consensus_dispersion_usd": a3.get("consensus_dispersion_usd"),
        "n_analysts_at_T_minus_14": a3.get("n_analysts_at_T_minus_14"),
        "divergence_pct": a3.get("divergence_pct"),
        "divergence_class": a3.get("divergence_class"),
        "agent3_confidence": a3.get("confidence"),
        "gdelt_disclosed": a4.get("gdelt_disclosed"),
        "gdelt_n_articles": a4.get("n_articles_in_window"),
        "agent4_modifier": a4.get("conviction_modifier"),
        "bull_direction": bull_dir,
        "bear_direction": bear_dir,
        "arbiter_decision": arbiter_decision,
        "arbiter_reasoning": (arbiter_reasoning[:240] if isinstance(arbiter_reasoning, str) else ""),
        "arbiter_overruled_bear": bool(arbiter_overruled_bear),
    }


def main() -> None:
    crsp = load_combined()
    eds = _earnings_dates()
    actuals = _load_compustat_actuals()

    rows = []
    for window_label, run_dir in V2_5_RUNS:
        cell_parquet = run_dir / "strategy_01" / "cell_results.parquet"
        if not cell_parquet.exists():
            print(f"  skipping {window_label}: no cell_results.parquet")
            continue
        cells = pd.read_parquet(cell_parquet)
        for _, r in cells.iterrows():
            ticker = r["ticker"]
            fpe_str = r["fiscal_quarter_end"]
            v25_decision = r["decision"]
            in_v1 = (ticker, fpe_str) in V1_LONGS
            # We only care about v2.5 longs + v1 drops (where v2.5 said no_trade)
            if v25_decision != "long" and not in_v1:
                continue
            fpe = datetime.strptime(fpe_str, "%Y-%m-%d").date()
            T = datetime.strptime(r["decision_date_T"], "%Y-%m-%d").date()

            # PnL (only meaningful for actual longs)
            net_pct = None
            net_pnl = None
            entry_p = exit_p = None
            if v25_decision == "long":
                size = float(r.get("final_size_pct", 0.10))
                ed = eds.get((ticker, fpe))
                series = crsp.get(ticker, [])
                entry_p = price_at(series, T) if series else None
                exit_p = _exit_price(series, ed, days_after=2) if (series and ed) else None
                if entry_p and exit_p:
                    pnl = compute_trade_pnl(
                        entry_price=entry_p, exit_price=exit_p, size_pct=size,
                        capital_usd=1_000_000, cost_bps=30,
                    )
                    net_pct = pnl["net_return_pct"]
                    net_pnl = pnl["net_pnl_usd"]

            agents = _agent_outputs(run_dir, ticker, fpe_str)

            # Dispersion-adjusted surprise: divergence_pct / (dispersion / consensus * 100)
            div_pct = agents.get("divergence_pct")
            cons_med = agents.get("consensus_median_usd")
            cons_disp = agents.get("consensus_dispersion_usd")
            disp_adj = None
            if (div_pct is not None and cons_med and cons_disp
                    and abs(cons_med) > 0 and abs(cons_disp) > 0):
                cov_pct = abs(cons_disp) / abs(cons_med) * 100.0
                if cov_pct > 0:
                    disp_adj = float(div_pct) / cov_pct

            # WTI 4w return at T
            wti = wti_4w_return_at_T(r["decision_date_T"])
            wti_4w = wti.get("wti_4w_return_pct")

            # Actual revenue beat
            actual_row = actuals[
                (actuals["ticker"] == ticker)
                & (actuals["fiscal_quarter_end"] == fpe_str)
            ]
            actual_rev = (
                float(actual_row["actual_revenue_usd"].iloc[0])
                if len(actual_row) else None
            )
            actual_beat = None
            if actual_rev is not None and cons_med:
                actual_beat = bool(actual_rev > cons_med)

            # Set membership label
            if v25_decision == "long" and in_v1:
                label = "inherited"
            elif v25_decision == "long" and not in_v1:
                label = "v2.5_only"
            elif v25_decision != "long" and in_v1:
                label = "dropped"
            else:
                continue  # not in any of our 3 buckets

            rows.append({
                "label": label,
                "window": window_label,
                "ticker": ticker,
                "fiscal_quarter_end": fpe_str,
                "v25_decision": v25_decision,
                "v25_size_pct": float(r.get("final_size_pct", 0.0)),
                "entry_price": entry_p,
                "exit_price": exit_p,
                "net_return_pct": net_pct,
                "net_pnl_usd": net_pnl,
                "win": (net_pct > 0) if net_pct is not None else None,
                "divergence_pct": div_pct,
                "divergence_class": agents.get("divergence_class"),
                "agent3_confidence": agents.get("agent3_confidence"),
                "consensus_median_usd": cons_med,
                "consensus_dispersion_usd": cons_disp,
                "n_analysts_at_T_minus_14": agents.get("n_analysts_at_T_minus_14"),
                "dispersion_adjusted_surprise": disp_adj,
                "absolute_active": agents.get("absolute_active"),
                "n_newly_active": agents.get("n_newly_active"),
                "n_continuously_active": agents.get("n_continuously_active"),
                "share_active": agents.get("share_active"),
                "relative_activity_delta": agents.get("relative_activity_delta"),
                "wti_4w_return_pct": wti_4w,
                "actual_revenue_usd": actual_rev,
                "actual_revenue_beat": actual_beat,
                "gdelt_disclosed": agents.get("gdelt_disclosed"),
                "gdelt_n_articles": agents.get("gdelt_n_articles"),
                "agent4_modifier": agents.get("agent4_modifier"),
                "bull_direction": agents.get("bull_direction"),
                "bear_direction": agents.get("bear_direction"),
                "arbiter_decision": agents.get("arbiter_decision"),
                "arbiter_overruled_bear": agents.get("arbiter_overruled_bear"),
                "arbiter_reasoning_240": agents.get("arbiter_reasoning"),
            })

    diag = pd.DataFrame(rows)
    diag = attach_signal_confidence(diag)

    out_path = ROOT / "runs" / "inference" / "v2_5_diagnostic_table.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    diag.to_csv(out_path, index=False)
    print(f"Wrote {out_path} ({len(diag)} rows)")
    print()

    print("Summary by label:")
    g = diag.groupby("label").agg(
        n=("ticker", "count"),
        wins=("win", lambda s: int((s.dropna() == True).sum())),
        losses=("win", lambda s: int((s.dropna() == False).sum())),
        total_pnl=("net_pnl_usd", lambda s: float(s.dropna().sum())),
        mean_ret=("net_return_pct", lambda s: float(s.dropna().mean()) if s.dropna().any() else None),
        mean_div_pct=("divergence_pct", lambda s: float(s.dropna().mean()) if s.dropna().any() else None),
        mean_sc_score=("signal_confidence_score", lambda s: float(s.dropna().mean()) if s.dropna().any() else None),
        mean_disp_adj=("dispersion_adjusted_surprise", lambda s: float(s.dropna().mean()) if s.dropna().any() else None),
        mean_wti_4w=("wti_4w_return_pct", lambda s: float(s.dropna().mean()) if s.dropna().any() else None),
    )
    print(g.to_string())
    print()

    print("v2.5_only trades (the 17 marginal additions):")
    cols = [
        "ticker", "fiscal_quarter_end", "win", "net_return_pct",
        "divergence_pct", "signal_confidence_score", "dispersion_adjusted_surprise",
        "wti_4w_return_pct", "actual_revenue_beat",
        "bull_direction", "bear_direction", "arbiter_overruled_bear",
    ]
    sub = diag[diag["label"] == "v2.5_only"][cols].sort_values(
        ["fiscal_quarter_end", "ticker"]
    )
    print(sub.to_string(index=False))


if __name__ == "__main__":
    main()
