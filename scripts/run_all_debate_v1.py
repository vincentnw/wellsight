"""Run full pipeline (debate-v1) for all tickers across all years.
Writes progress to runs/debate_v1_run.log and rebuilds trade ledger on completion.
Usage: python scripts/run_all_debate_v1.py
"""
from __future__ import annotations

import sys
import time
import logging
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import os
os.environ["FIN580_SAR_MODE"] = "real_sentinel1"

LOG_FILE = ROOT / "runs" / "debate_v1_run.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

from fin580.backtest.runner import run_window, RUNS_DIR, UNIVERSE

CM_LABEL = "v3"

# Year windows: run each year as a separate run dir to match dashboard structure.
# 2025 partial quarters are included in the 2024 window run (Q1-2025Q3).
WINDOWS = [
    ("2019Q1", "2019Q4"),
    ("2020Q1", "2020Q4"),
    ("2021Q1", "2021Q4"),
    ("2022Q1", "2022Q4"),
    ("2023Q1", "2023Q4"),
    ("2024Q1", "2025Q3"),  # includes 2025 partials — maps to "2024" window in dashboard
]

new_run_dirs: dict[str, Path] = {}

total_start = time.time()
for start_q, end_q in WINDOWS:
    year = start_q[:4]
    log.info(f"=== Starting window {start_q}–{end_q} ({len(UNIVERSE)} tickers) ===")
    t0 = time.time()
    try:
        run_dir = run_window(
            strategy=1,
            start_quarter=start_q,
            end_quarter=end_q,
            cm_label=CM_LABEL,
        )
        new_run_dirs[year] = run_dir
        elapsed = time.time() - t0
        log.info(f"  Window {start_q}–{end_q} done in {elapsed/60:.1f} min → {run_dir.name}")
    except Exception as e:
        log.error(f"  Window {start_q}–{end_q} FAILED: {e}")

log.info(f"\nAll windows done in {(time.time()-total_start)/60:.1f} min total")
log.info("Run dirs:")
for yr, d in new_run_dirs.items():
    log.info(f"  {yr}: {d.name}")

# --- Rebuild trade ledger from new run dirs ---
log.info("\nRebuilding trade ledger from new run dirs...")

import pandas as pd
from fin580.backtest.pnl_engine import compute_trade_pnl
from fin580.data.crsp_loader import load_combined, price_at
from fin580.inference.pnl import _earnings_dates, _exit_price

def _window_for_fpe(fpe: str) -> str:
    y = int(fpe[:4])
    if y <= 2019: return "2019"
    if y == 2020: return "2020"
    if y == 2021: return "2021"
    if y == 2022: return "2022"
    if y == 2023: return "2023"
    return "2024"

try:
    crsp = load_combined()
except FileNotFoundError:
    log.error("CRSP data not found — cannot build P&L. Run dirs are ready; rebuild ledger manually.")
    sys.exit(0)

eds = _earnings_dates()

rows = []
for year, run_dir in new_run_dirs.items():
    p = run_dir / "strategy_01" / "cell_results.parquet"
    if not p.exists():
        log.warning(f"No cell_results.parquet in {run_dir.name}")
        continue
    cells = pd.read_parquet(p)
    directional = cells[cells["decision"].isin(["long", "short"])]
    log.info(f"  {year}: {len(directional)} trades from {len(cells)} cells")
    for _, r in directional.iterrows():
        ticker = r["ticker"]
        fpe_str = r["fiscal_quarter_end"]
        direction = r["decision"]
        size = float(r.get("final_size_pct", 0.10))
        from datetime import datetime
        fpe = datetime.strptime(fpe_str, "%Y-%m-%d").date()
        T = datetime.strptime(r["decision_date_T"], "%Y-%m-%d").date()
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
            direction=direction, capital_usd=1_000_000, cost_bps=30,
        )
        conv = r.get("conviction_tier", "medium")
        rows.append({
            "strategy": 1,
            "ticker": ticker,
            "fiscal_quarter_end": fpe_str,
            "direction": direction,
            "entry_date_T": T.isoformat(),
            "exit_date": (ed + timedelta(days=2)).isoformat(),
            "entry_price": entry_p,
            "exit_price": exit_p,
            "size_pct": size,
            "gross_return_pct": pnl["gross_return_pct"],
            "net_return_pct": pnl["net_return_pct"],
            "gross_pnl_usd": pnl["gross_pnl_usd"],
            "net_pnl_usd": pnl["net_pnl_usd"],
            "conviction_tier": conv,
        })

if rows:
    out = pd.DataFrame(rows).sort_values(["fiscal_quarter_end", "ticker"]).reset_index(drop=True)
    ledger_path = ROOT / "runs" / "inference" / "strategy01_trades.csv"
    out.to_csv(ledger_path, index=False)
    total_pnl = out["net_pnl_usd"].sum()
    wins = (out["net_return_pct"] > 0).sum()
    log.info(f"\nLedger saved: {len(out)} trades")
    log.info(f"  Portfolio return: {total_pnl/1_000_000*100:+.2f}%  (${total_pnl:+,.0f})")
    log.info(f"  Hit rate: {wins/len(out):.0%}  ({wins}W / {len(out)-wins}L)")
    log.info(f"  Ledger: {ledger_path}")
else:
    log.warning("No directional trades found — ledger not updated.")

log.info("\nDone. Restart the dashboard to see updated results.")
