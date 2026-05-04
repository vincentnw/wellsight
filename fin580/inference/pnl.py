"""Per-strategy P&L aggregation.

For each long trade, look up entry price (T-14) and exit price (T+2 trading
days after announcement) from CRSP+Yahoo combined series. Compute gross and
net (after 30 bps round-trip cost) returns. Strategy 7 (XLE buy-hold) is
treated separately as a single buy-hold position.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import pandas as pd

from fin580.backtest.pnl_engine import compute_trade_pnl
from fin580.data.crsp_loader import load_combined, price_at

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"


def _earnings_dates() -> dict[tuple[str, date], date]:
    out = {}
    import csv
    with open(PHASE1_OUTPUT / "earnings_dates.csv") as f:
        for r in csv.DictReader(f):
            t = r["ticker"]
            fpe = datetime.strptime(r["fiscal_quarter_end"], "%Y-%m-%d").date()
            ed = datetime.strptime(r["earnings_date_actual"], "%Y-%m-%d").date()
            out[(t, fpe)] = ed
    return out


def _next_trading_day_price(series, target: date, max_search_days: int = 7) -> float | None:
    """Most recent close on or before target. If target falls on weekend, walks back."""
    return price_at(series, target)


def _exit_price(series, earnings_date: date, days_after: int = 2) -> float | None:
    """Closing price on the Nth trading day strictly after earnings_date.

    Codex Issue 3 fix: prior implementation walked forward from
    earnings_date + N calendar days, which collapsed to 1 trading day for
    Thursday/Friday announcements. This implementation counts trading days
    (i.e., dates present in the price series) strictly after earnings_date.
    """
    forward_dates = sorted(d for d, _, _ in series if d > earnings_date)
    if len(forward_dates) < days_after:
        return None
    target_date = forward_dates[days_after - 1]
    return price_at(series, target_date)


def compute_pnl_for_strategy(strategy_id: int, window: str | None = None) -> pd.DataFrame:
    """Compute per-trade P&L for a strategy. Returns dataframe with one row
    per long trade. Strategies 1, 2 use cell_results.parquet; 3-10 use
    cell_results_summary.parquet.

    Picks the most recent run dir matching `*-strategy{id}-{window}-target`.
    `window` defaults to '2024Q1_2024Q4' (the headline real-data scope); pass
    explicit window string (e.g. '2021Q1_2025Q4') to use a different run.
    """
    if window is None:
        window = "2024Q1_2024Q4"
    # Match both base ("...-target") and suffixed ("...-target-realsar") run dirs.
    # Prefer suffixed dirs (where the real-SAR run was tagged) by sorting them
    # after the base dirs in reverse alphabetical (suffixed = newer/preferred).
    candidates = sorted(
        list(RUNS_DIR.glob(f"*-strategy{strategy_id}-{window}-target")) +
        list(RUNS_DIR.glob(f"*-strategy{strategy_id}-{window}-target-*")),
        reverse=True,
    )
    # Prefer cell_results.parquet (Strategies 1,2) then cell_results_summary.parquet
    path = None
    col = "direction"
    for run_dir in candidates:
        strat_dir = run_dir / f"strategy_{strategy_id:02d}"
        p1 = strat_dir / "cell_results.parquet"
        p2 = strat_dir / "cell_results_summary.parquet"
        if strategy_id in (1, 2) and p1.exists():
            path = p1
            col = "decision"
            break
        if p2.exists():
            path = p2
            col = "direction"
            break
    if path is None:
        return pd.DataFrame()

    df = pd.read_parquet(path)
    longs = df[df[col] == "long"].copy()
    if len(longs) == 0:
        return pd.DataFrame()

    crsp = load_combined()
    eds = _earnings_dates()

    rows = []
    for _, r in longs.iterrows():
        ticker = r["ticker"]
        fpe = datetime.strptime(r["fiscal_quarter_end"], "%Y-%m-%d").date()
        T = datetime.strptime(r["decision_date_T"], "%Y-%m-%d").date()
        size = float(r.get("size_pct", r.get("final_size_pct", 0.10)))
        ed = eds.get((ticker, fpe))
        if ed is None:
            continue
        series = crsp.get(ticker, [])
        if not series:
            continue
        entry_p = price_at(series, T)
        exit_p = _exit_price(series, ed, days_after=2)
        if entry_p is None or exit_p is None:
            continue
        pnl = compute_trade_pnl(
            entry_price=entry_p, exit_price=exit_p, size_pct=size,
            capital_usd=1_000_000, cost_bps=30,
        )
        rows.append({
            "strategy": strategy_id,
            "ticker": ticker,
            "fiscal_quarter_end": fpe.isoformat(),
            "entry_date_T": T.isoformat(),
            "exit_date": (ed + timedelta(days=2)).isoformat(),
            "entry_price": entry_p,
            "exit_price": exit_p,
            "size_pct": size,
            "gross_return_pct": pnl["gross_return_pct"],
            "net_return_pct": pnl["net_return_pct"],
            "gross_pnl_usd": pnl["gross_pnl_usd"],
            "net_pnl_usd": pnl["net_pnl_usd"],
        })
    return pd.DataFrame(rows)


STRATEGY1_YEARLY_RUNS = [
    "2026-05-03-strategy1-2019Q1_2019Q4-target-realsar",
    "2026-05-03-strategy1-2020Q1_2020Q4-target-realsar",
    "2026-05-03-strategy1-2021Q1_2021Q4-target-realsar",
    "2026-05-03-strategy1-2022Q1_2023Q4-target-realsar",
    "2026-04-30-strategy1-2024Q1_2024Q4-target-realsar",
]


def compute_pnl_strategy1_combined() -> pd.DataFrame:
    """Strategy 1 P&L unioned across the 5 yearly run dirs covering 2019-2024.

    This is the headline H1 trade ledger reported in the paper. Per-trade rows
    are deduped on (ticker, fiscal_quarter_end) keeping the latest attempt.
    Strategies 2-10 stay on the 2024 sub-window via compute_pnl_for_strategy.
    """
    crsp = load_combined()
    eds = _earnings_dates()
    cell_parts = []
    for run_name in STRATEGY1_YEARLY_RUNS:
        p = RUNS_DIR / run_name / "strategy_01" / "cell_results.parquet"
        if not p.exists():
            continue
        cell_parts.append(pd.read_parquet(p))
    if not cell_parts:
        return pd.DataFrame()
    cells = pd.concat(cell_parts, ignore_index=True).drop_duplicates(
        subset=["ticker", "fiscal_quarter_end"], keep="last"
    )
    longs = cells[cells["decision"] == "long"]
    rows = []
    for _, r in longs.iterrows():
        ticker = r["ticker"]
        fpe = datetime.strptime(r["fiscal_quarter_end"], "%Y-%m-%d").date()
        T = datetime.strptime(r["decision_date_T"], "%Y-%m-%d").date()
        size = float(r.get("size_pct", r.get("final_size_pct", 0.10)))
        ed = eds.get((ticker, fpe))
        if ed is None:
            continue
        series = crsp.get(ticker, [])
        if not series:
            continue
        entry_p = price_at(series, T)
        exit_p = _exit_price(series, ed, days_after=2)
        if entry_p is None or exit_p is None:
            continue
        pnl = compute_trade_pnl(
            entry_price=entry_p, exit_price=exit_p, size_pct=size,
            capital_usd=1_000_000, cost_bps=30,
        )
        rows.append({
            "strategy": 1,
            "ticker": ticker,
            "fiscal_quarter_end": fpe.isoformat(),
            "entry_date_T": T.isoformat(),
            "exit_date": (ed + timedelta(days=2)).isoformat(),
            "entry_price": entry_p,
            "exit_price": exit_p,
            "size_pct": size,
            "gross_return_pct": pnl["gross_return_pct"],
            "net_return_pct": pnl["net_return_pct"],
            "gross_pnl_usd": pnl["gross_pnl_usd"],
            "net_pnl_usd": pnl["net_pnl_usd"],
        })
    return pd.DataFrame(rows).sort_values("entry_date_T").reset_index(drop=True)


def strategy_metrics(trades: pd.DataFrame) -> dict:
    """Hit rate, mean / median return, Sharpe, max drawdown over trades."""
    if len(trades) == 0:
        return {
            "n_trades": 0,
            "hit_rate": None,
            "mean_net_return_pct": None,
            "median_net_return_pct": None,
            "sharpe_quarterly": None,
            "max_drawdown_pct": None,
        }
    rets = trades["net_return_pct"].astype(float)
    hit_rate = (rets > 0).mean()
    mean_ret = rets.mean()
    median_ret = rets.median()
    std_ret = rets.std()
    sharpe = (mean_ret / std_ret) if std_ret > 0 else None
    # Max drawdown across the chronological sequence
    sorted_trades = trades.sort_values("entry_date_T")
    equity = (1.0 + sorted_trades["net_return_pct"].astype(float)).cumprod()
    running_max = equity.cummax()
    dd = (equity - running_max) / running_max
    max_dd = float(dd.min()) if len(dd) else 0.0
    return {
        "n_trades": len(trades),
        "hit_rate": float(hit_rate),
        "mean_net_return_pct": float(mean_ret),
        "median_net_return_pct": float(median_ret),
        "sharpe_quarterly": float(sharpe) if sharpe is not None else None,
        "max_drawdown_pct": max_dd,
    }


def build_headline_table() -> pd.DataFrame:
    """Compute per-strategy metrics across all 10 strategies.

    Strategy 1 row uses the full 2019-2024 ledger (n=10 trades). Strategies
    2-10 use the 2024 sub-window (only window for which baseline runs exist).
    """
    rows = []
    for s in [1, 2, 3, 4, 5, 6, 8, 9, 10]:  # skip 7 (handled separately)
        trades = (
            compute_pnl_strategy1_combined() if s == 1
            else compute_pnl_for_strategy(s)
        )
        m = strategy_metrics(trades)
        m["strategy"] = s
        rows.append(m)

    # Strategy 7 — XLE buy-hold from 2021Q1 first earnings to 2025Q4 last
    crsp = load_combined()
    xle = crsp.get("XLE", [])
    if xle:
        start_d = date(2021, 1, 4)
        end_d = date(2025, 12, 31)
        p_start = price_at(xle, start_d) or xle[0][1]
        p_end = price_at(xle, end_d) or xle[-1][1]
        gross = (p_end - p_start) / p_start if p_start else 0
        rows.append({
            "strategy": 7,
            "n_trades": 1,
            "hit_rate": 1.0 if gross > 0 else 0.0,
            "mean_net_return_pct": gross - 0.0030,  # 30 bps round-trip
            "median_net_return_pct": gross - 0.0030,
            "sharpe_quarterly": None,
            "max_drawdown_pct": None,
        })
    return pd.DataFrame(rows).sort_values("strategy").reset_index(drop=True)
