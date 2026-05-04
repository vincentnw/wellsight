"""Roll up every M3/M5/M6/M7 result into a single evidence pack.

Outputs to runs/inference/:
- evidence_pack.json — top-level summary (numbers used in paper)
- ablation_table.{parquet,csv} — variant comparison
- headline_table.{parquet,csv} — per-strategy P&L
- bootstrap_table.{parquet,csv} — primary + sensitivity tests
- strategy01_trades.csv — per-trade ledger
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from fin580.inference.ablations import build_ablation_table
from fin580.inference.bootstrap import (
    firm_clustered_bootstrap,
    primary_test,
    quarter_block_bootstrap,
)
from fin580.inference.h2_test import quarter_block_diff
from fin580.inference.pnl import (
    build_headline_table,
    compute_pnl_for_strategy,
    compute_pnl_strategy1_combined,
    strategy_metrics,
)
from fin580.inference.revenue_diagnostics import (
    build_revenue_diagnostics,
    revenue_diagnostic_summary,
)

OUT_DIR = Path(__file__).resolve().parents[2] / "runs" / "inference"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Strategy 1 trades — H1 headline uses combined 2019-2024 ledger;
    # H2 vs Strategy 3 uses 2024 sub-window only because Strategies 3-10 only
    # have 2024 runs.
    s1_trades = compute_pnl_strategy1_combined()
    s1_trades.to_csv(OUT_DIR / "strategy01_trades.csv", index=False)
    s1_metrics = strategy_metrics(s1_trades)
    # 2024 sub-window slice from the same combined ledger (avoids picking up
    # experimental run dirs like *-alpha020 / *-redesign via reverse-glob).
    s1_trades_2024 = (
        s1_trades[s1_trades["fiscal_quarter_end"].str.startswith("2024-")]
        .reset_index(drop=True) if len(s1_trades) else pd.DataFrame()
    )
    s1_trades_2024.to_csv(OUT_DIR / "strategy01_trades_2024.csv", index=False)

    # 2. Bootstrap primary test (full window) + sensitivity + H2 (2024 only)
    primary = primary_test(s1_trades, n_iter=1000, seed=0) if len(s1_trades) else {}
    s3_trades = compute_pnl_for_strategy(3)
    h2 = (
        quarter_block_diff(s1_trades_2024, s3_trades)
        if len(s1_trades_2024) and len(s3_trades) else {}
    )
    fc_hit = firm_clustered_bootstrap(s1_trades, n_iter=1000, metric="hit_rate", seed=0)
    fc_mean = firm_clustered_bootstrap(s1_trades, n_iter=1000, metric="mean_return", seed=0)
    qb_hit = quarter_block_bootstrap(s1_trades, n_iter=1000, metric="hit_rate", seed=0)

    bootstrap_rows = [
        {"test": "primary_firm_clustered_hit_rate_vs_50",
         **primary},
        {"test": "firm_clustered_hit_rate_ci",
         "mean": fc_hit["mean"], "ci_low": fc_hit["ci_low"],
         "ci_high": fc_hit["ci_high"], "n_iter": fc_hit["n_iter"]},
        {"test": "firm_clustered_mean_return_ci",
         "mean": fc_mean["mean"], "ci_low": fc_mean["ci_low"],
         "ci_high": fc_mean["ci_high"], "n_iter": fc_mean["n_iter"]},
        {"test": "quarter_block_hit_rate_ci",
         "mean": qb_hit["mean"], "ci_low": qb_hit["ci_low"],
         "ci_high": qb_hit["ci_high"], "n_iter": qb_hit["n_iter"]},
    ]
    bootstrap_df = pd.DataFrame(bootstrap_rows)
    bootstrap_df.to_parquet(OUT_DIR / "bootstrap_table.parquet")
    bootstrap_df.to_csv(OUT_DIR / "bootstrap_table.csv", index=False)

    # 3. Headline strategy table — full window for Strategy 1, 2024 for the rest.
    # Also write a 2024-only slice (used by the dashboard's Section 6 baseline
    # comparison where every strategy is restricted to the 2024 sub-window).
    try:
        headline = build_headline_table()
        headline.to_parquet(OUT_DIR / "headline_table.parquet")
        headline.to_csv(OUT_DIR / "headline_table.csv", index=False)
        s1_2024_metrics = strategy_metrics(s1_trades_2024)
        headline_2024 = headline.copy()
        headline_2024.loc[headline_2024["strategy"] == 1, list(s1_2024_metrics)] = list(
            s1_2024_metrics.values()
        )
        headline_2024.to_csv(OUT_DIR / "headline_table_2024.csv", index=False)
    except Exception as e:
        headline = pd.DataFrame()
        print(f"Warning: headline_table build failed: {e}")

    # 4. Ablation comparison
    try:
        ablation = build_ablation_table()
        ablation.to_parquet(OUT_DIR / "ablation_table.parquet")
        ablation.to_csv(OUT_DIR / "ablation_table.csv", index=False)
    except Exception as e:
        ablation = pd.DataFrame()
        print(f"Warning: ablation_table build failed: {e}")

    # 5. Revenue-mechanism diagnostics. Diagnostic only: does not affect H1,
    # trade eligibility, or sizing.
    try:
        revenue_diag = build_revenue_diagnostics()
        revenue_diag.to_parquet(OUT_DIR / "revenue_diagnostics.parquet")
        revenue_diag.to_csv(OUT_DIR / "revenue_diagnostics.csv", index=False)
        revenue_diag_summary = revenue_diagnostic_summary(revenue_diag)
    except Exception as e:
        revenue_diag = pd.DataFrame()
        revenue_diag_summary = {"error": str(e)[:200]}
        print(f"Warning: revenue_diagnostics build failed: {e}")

    # 6. Top-level summary
    pack = {
        "generated_at": datetime.now().isoformat(),
        "strategy1_baseline": {
            "n_trades": s1_metrics.get("n_trades"),
            "hit_rate": s1_metrics.get("hit_rate"),
            "mean_net_return_pct": s1_metrics.get("mean_net_return_pct"),
            "median_net_return_pct": s1_metrics.get("median_net_return_pct"),
            "sharpe_quarterly": s1_metrics.get("sharpe_quarterly"),
            "max_drawdown_pct": s1_metrics.get("max_drawdown_pct"),
        },
        "primary_test_H1": {
            "p_value_one_sided": primary.get("p_value_one_sided"),
            "reject_50": primary.get("reject_50"),
            "ci_95": primary.get("ci_95"),
            "n_iter": primary.get("n_iter"),
        },
        "secondary_test_H2": h2,
        "ablation_summary": (
            ablation.to_dict(orient="records") if len(ablation) else []
        ),
        "revenue_diagnostic_summary": revenue_diag_summary,
        "headline_summary": (
            headline.to_dict(orient="records") if len(headline) else []
        ),
    }
    with open(OUT_DIR / "evidence_pack.json", "w") as f:
        json.dump(pack, f, indent=2, default=str)
    print(f"Wrote evidence pack to {OUT_DIR}")
    print(f"  Strategy 1 baseline: hit_rate={s1_metrics.get('hit_rate'):.3f}, "
          f"p={primary.get('p_value_one_sided')}, n={s1_metrics.get('n_trades')}")
    if len(ablation):
        for _, r in ablation.iterrows():
            print(f"  {r['variant']:>20s}: cells={r['n_cells_total']:>3d} "
                  f"long={r['n_long']:>2d} hit_rate={r['hit_rate']}")


if __name__ == "__main__":
    main()
