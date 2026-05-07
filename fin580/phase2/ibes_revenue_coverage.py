"""Regenerate ibes_revenue_coverage.csv from the master IBES Detail file.

Same derivation applied uniformly across all fiscal years:
  - Filter to FPI=6 (current quarter SAL forecast) + MEASURE='SAL'
  - Restrict FPEDATS to true quarter-ends (Mar 31, Jun 30, Sep 30, Dec 31)
  - Aggregate per (OFTIC, FPEDATS):
      n_estimates           = count of estimate-revisions
      n_unique_analysts     = nunique(ANALYS)
      consensus_median_usd_m= median(VALUE)
      consensus_mean_usd_m  = mean(VALUE)
      dispersion_usd_m      = std(VALUE)
      newest_anndats        = max(ANNDATS)
      oldest_anndats        = min(ANNDATS)
  - Restrict to project's 10-firm Permian universe
  - eligible = n_unique_analysts >= 3

Run: python -m fin580.phase2.ibes_revenue_coverage
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
UNIVERSE = ["FANG", "EOG", "DVN", "CTRA", "OXY", "MTDR", "PR", "OVV", "SM", "CRGY"]


def regenerate(
    ibes_csv: Path = PHASE1_OUTPUT / "ibes_tr_ibes_sal_query11220958.csv",
    out_csv: Path = PHASE1_OUTPUT / "ibes_revenue_coverage.csv",
) -> int:
    df = pd.read_csv(ibes_csv, parse_dates=["ANNDATS", "FPEDATS", "ANNDATS_ACT"])
    df = df.dropna(subset=["FPEDATS", "OFTIC", "VALUE"])
    df = df[(df.FPI == 6) & (df.MEASURE == "SAL")].copy()
    df = df[(df.FPEDATS.dt.month.isin([3, 6, 9, 12])) & df.FPEDATS.dt.is_quarter_end]

    agg = df.groupby(["OFTIC", "FPEDATS"]).agg(
        n_estimates=("VALUE", "size"),
        n_unique_analysts=("ANALYS", "nunique"),
        consensus_median_usd_m=("VALUE", "median"),
        consensus_mean_usd_m=("VALUE", "mean"),
        dispersion_usd_m=("VALUE", "std"),
        newest_anndats=("ANNDATS", "max"),
        oldest_anndats=("ANNDATS", "min"),
    ).reset_index()
    agg.columns = [
        "ticker", "fiscal_quarter_end", "n_estimates", "n_unique_analysts",
        "consensus_median_usd_m", "consensus_mean_usd_m", "dispersion_usd_m",
        "newest_anndats", "oldest_anndats",
    ]
    agg["eligible"] = agg["n_unique_analysts"] >= 3
    agg = agg[agg.ticker.isin(UNIVERSE)].sort_values(["ticker", "fiscal_quarter_end"]).reset_index(drop=True)

    for c in ("fiscal_quarter_end", "newest_anndats", "oldest_anndats"):
        agg[c] = pd.to_datetime(agg[c]).dt.strftime("%Y-%m-%d")

    agg.to_csv(out_csv, index=False)
    return len(agg)


if __name__ == "__main__":
    n = regenerate()
    print(f"Wrote ibes_revenue_coverage.csv: {n} rows")
