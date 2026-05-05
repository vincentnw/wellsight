"""Canonical rollups for v2.5_fix headline.

Computes the full evidence pack against the v2.5_fix ledger:
  - bootstrap p-value (firm-clustered, null-centered)
  - 95% bootstrap CI on hit rate (firm-clustered + quarter-block)
  - per-trade Sharpe (quarterly)
  - max drawdown over the chronological sequence
  - per-year and per-quarter tables with EXPLICIT signed currency formatting
  - aggregate metrics

All currency rendered with sign-explicit format: "+$1,234" or "($1,234)"
to avoid unicode minus-sign rendering issues across terminals.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from fin580.inference.bootstrap import (
    firm_clustered_bootstrap,
    quarter_block_bootstrap,
    primary_test,
)


def fmt_usd(x: float) -> str:
    """Sign-explicit currency. Negatives wrapped in parentheses + minus prefix."""
    if pd.isna(x) or x is None:
        return "n/a"
    if x < 0:
        return f"-${abs(x):,.0f}"
    return f"+${x:,.0f}"


def fmt_pct(x: float, places: int = 2) -> str:
    if pd.isna(x) or x is None:
        return "n/a"
    if x < 0:
        return f"-{abs(x)*100:.{places}f}%"
    return f"+{x*100:.{places}f}%"


def main():
    ledger_path = Path("runs/inference/strategy01_trades_v2_5_fix.csv")
    df = pd.read_csv(ledger_path)
    df["fiscal_quarter_end"] = pd.to_datetime(df["fiscal_quarter_end"]).dt.date
    df = df.sort_values("entry_date_T").reset_index(drop=True)

    n = len(df)
    rets = df["net_return_pct"].astype(float)
    pnls = df["net_pnl_usd"].astype(float)

    print("=" * 78)
    print("v2.5_fix CANONICAL ROLLUPS  (2019-2024 corrected ledger)")
    print("=" * 78)
    print()

    # ---------- aggregate
    wins = int((rets > 0).sum())
    losses = int((rets <= 0).sum())
    hit_rate = wins / n
    mean_ret = rets.mean()
    median_ret = rets.median()
    total_pnl = pnls.sum()
    std_ret = rets.std()
    sharpe = mean_ret / std_ret if std_ret > 0 else float("nan")

    # max drawdown over compounded equity curve
    equity = (1.0 + rets).cumprod()
    running_max = equity.cummax()
    dd = (equity - running_max) / running_max
    max_dd = float(dd.min()) if len(dd) else 0.0

    print("--- Aggregate ---")
    print(f"  n trades:                {n}")
    print(f"  wins / losses:           {wins} / {losses}")
    print(f"  hit rate:                {hit_rate*100:.1f}%")
    print(f"  mean net return / trade: {fmt_pct(mean_ret, 2)}")
    print(f"  median net return:       {fmt_pct(median_ret, 2)}")
    print(f"  total P&L on $1M:        {fmt_usd(total_pnl)}  ({fmt_pct(total_pnl/1_000_000, 2)} of capital)")
    print(f"  per-trade Sharpe (qtrly): {sharpe:.3f}")
    print(f"  max drawdown:            {fmt_pct(max_dd, 2)}")
    print()

    # ---------- bootstrap
    print("--- Primary test: firm-clustered bootstrap, null-centered, one-sided vs H0=50% ---")
    pt = primary_test(df, n_iter=1000, seed=0)
    print(f"  observed hit rate:       {pt['hit_rate_obs']*100:.1f}%")
    print(f"  bootstrap p-value:       {pt['p_value_one_sided']:.3f}")
    print(f"  exact-binomial p (cross-check): {pt['p_value_exact_binomial']:.3f}")
    print(f"  reject H0=50% at 5%:     {pt['reject_50']}")
    ci_lo, ci_hi = pt['ci_95']
    print(f"  95% bootstrap CI on hit rate: [{ci_lo*100:.1f}%, {ci_hi*100:.1f}%]")
    print(f"  n iterations:            {pt['n_iter']}")
    print()

    print("--- Sensitivity: quarter-block bootstrap ---")
    qb = quarter_block_bootstrap(df, n_iter=1000, metric="hit_rate", seed=0)
    print(f"  hit rate bootstrap mean: {qb['mean']*100:.1f}%")
    print(f"  95% quarter-block CI:    [{qb['ci_low']*100:.1f}%, {qb['ci_high']*100:.1f}%]")
    fc_mean = firm_clustered_bootstrap(df, n_iter=1000, metric="mean_return", seed=0)
    print(f"  firm-clustered mean-return bootstrap: mean={fmt_pct(fc_mean['mean'])}, "
          f"95% CI=[{fmt_pct(fc_mean['ci_low'])}, {fmt_pct(fc_mean['ci_high'])}]")
    print()

    # ---------- per-year (group by fiscal_quarter_end year, the paper convention)
    print("--- Per-year (by fiscal year of cell) ---")
    df["year"] = pd.to_datetime(df["fiscal_quarter_end"]).dt.year
    rows = []
    for y, g in df.groupby("year"):
        rets_y = g["net_return_pct"]
        rows.append({
            "year": int(y),
            "n": len(g),
            "W": int((rets_y > 0).sum()),
            "L": int((rets_y <= 0).sum()),
            "hit_rate": fmt_pct((rets_y > 0).mean(), 1),
            "mean_ret": fmt_pct(rets_y.mean(), 2),
            "P&L": fmt_usd(g["net_pnl_usd"].sum()),
        })
    yt = pd.DataFrame(rows)
    print(yt.to_string(index=False))
    print(f"  Total: n={n}, {wins}W/{losses}L, {hit_rate*100:.1f}% hit, "
          f"mean={fmt_pct(mean_ret, 2)}, P&L={fmt_usd(total_pnl)}")
    print()

    # ---------- per-quarter
    print("--- Per-quarter ---")
    df["qtr"] = pd.to_datetime(df["fiscal_quarter_end"]).dt.month.map(
        {3: 1, 6: 2, 9: 3, 12: 4}
    )
    rows = []
    for (y, q), g in df.groupby(["year", "qtr"]):
        rets_q = g["net_return_pct"]
        rows.append({
            "year": int(y),
            "qtr": f"Q{int(q)}",
            "n": len(g),
            "W/L": f"{int((rets_q > 0).sum())}W/{int((rets_q <= 0).sum())}L",
            "hit_rate": fmt_pct((rets_q > 0).mean(), 1),
            "P&L": fmt_usd(g["net_pnl_usd"].sum()),
        })
    print(pd.DataFrame(rows).to_string(index=False))
    print()

    # ---------- 2020-Q1 caveat (now hollow without SM)
    q1_2020 = df[(df.year == 2020) & (df.qtr == 1)]
    print("--- 2020-Q1 cohort under v2.5_fix ---")
    print(f"  trades:        {len(q1_2020)}")
    if len(q1_2020):
        for _, t in q1_2020.iterrows():
            print(f"    {t['ticker']} {t['fiscal_quarter_end']}: {fmt_pct(t['net_return_pct'])} = {fmt_usd(t['net_pnl_usd'])}")
        print(f"  cohort sum:    {fmt_usd(q1_2020.net_pnl_usd.sum())}")
    print()

    # ---------- write evidence pack
    out = Path("runs/inference")
    out.mkdir(parents=True, exist_ok=True)
    evidence = {
        "version": "v2.5_fix",
        "computed_at": datetime.now().isoformat(timespec="seconds"),
        "n_trades": n,
        "wins": wins,
        "losses": losses,
        "hit_rate": float(hit_rate),
        "mean_net_return_pct": float(mean_ret),
        "median_net_return_pct": float(median_ret),
        "total_pnl_usd": float(total_pnl),
        "sharpe_quarterly": float(sharpe),
        "max_drawdown_pct": float(max_dd),
        "primary_test": {
            "hit_rate_obs": float(pt["hit_rate_obs"]),
            "p_value_one_sided": float(pt["p_value_one_sided"]),
            "p_value_exact_binomial": float(pt["p_value_exact_binomial"]),
            "reject_50_at_5pct": bool(pt["reject_50"]),
            "ci_95_low": float(pt["ci_95"][0]),
            "ci_95_high": float(pt["ci_95"][1]),
            "n_iter": int(pt["n_iter"]),
        },
        "quarter_block_bootstrap_hit_rate": {
            "mean": float(qb["mean"]),
            "ci_low": float(qb["ci_low"]),
            "ci_high": float(qb["ci_high"]),
        },
        "firm_clustered_mean_return": {
            "mean": float(fc_mean["mean"]),
            "ci_low": float(fc_mean["ci_low"]),
            "ci_high": float(fc_mean["ci_high"]),
        },
    }
    pack_path = out / "evidence_pack_v2_5_fix.json"
    pack_path.write_text(json.dumps(evidence, indent=2))
    print(f"Wrote {pack_path}")

    bootstrap_table = pd.DataFrame([
        {
            "test": "firm_clustered_hit_rate",
            "obs": pt["hit_rate_obs"],
            "p_one_sided": pt["p_value_one_sided"],
            "ci_low": pt["ci_95"][0],
            "ci_high": pt["ci_95"][1],
            "n_iter": pt["n_iter"],
        },
        {
            "test": "quarter_block_hit_rate",
            "obs": float((rets > 0).mean()),
            "p_one_sided": None,
            "ci_low": qb["ci_low"],
            "ci_high": qb["ci_high"],
            "n_iter": qb["n_iter"],
        },
        {
            "test": "firm_clustered_mean_return",
            "obs": float(rets.mean()),
            "p_one_sided": None,
            "ci_low": fc_mean["ci_low"],
            "ci_high": fc_mean["ci_high"],
            "n_iter": fc_mean["n_iter"],
        },
    ])
    boot_path = out / "bootstrap_table_v2_5_fix.csv"
    bootstrap_table.to_csv(boot_path, index=False)
    print(f"Wrote {boot_path}")

    # Per-year and per-quarter tables to CSV for the paper
    yt.to_csv(out / "per_year_v2_5_fix.csv", index=False)
    pd.DataFrame(rows).to_csv(out / "per_quarter_v2_5_fix.csv", index=False)
    print(f"Wrote per-year and per-quarter tables")


if __name__ == "__main__":
    main()
