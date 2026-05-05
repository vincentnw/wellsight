"""Build equity-curve CSVs per strategy. Depends on per-trade ledgers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from fin580.inference.pnl import compute_pnl_for_strategy

OUT_DIR = Path(__file__).resolve().parents[2] / "runs" / "inference"


def build_equity_for_strategy(strategy_id: int) -> pd.DataFrame:
    trades = compute_pnl_for_strategy(strategy_id)
    if len(trades) == 0:
        return pd.DataFrame()
    s = trades.sort_values("entry_date_T").reset_index(drop=True)
    s["cum_growth_factor"] = (1.0 + s["net_return_pct"].astype(float)).cumprod()
    s["running_max"] = s["cum_growth_factor"].cummax()
    s["drawdown_pct"] = (s["cum_growth_factor"] - s["running_max"]) / s["running_max"]
    return s


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for s_id in [1, 2, 3, 4, 5, 6, 8, 9, 10]:
        eq = build_equity_for_strategy(s_id)
        if len(eq) == 0:
            continue
        eq.to_csv(OUT_DIR / f"strategy{s_id:02d}_equity.csv", index=False)
        print(f"Strategy {s_id}: wrote {len(eq)} rows; final cum_growth={eq.iloc[-1]['cum_growth_factor']:.3f}")


if __name__ == "__main__":
    main()
