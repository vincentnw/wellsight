"""v2.5_fix vs v2.5 diagnostic.

Computes corrected ledger P&L for the 2019-2024 v2.5_fix runs, compares
against the old v2.5 ledger committed in the paper, and emits the
2021 over-firing diagnostic plus a concurrency-cap sensitivity.

Headline P&L counts every long the system actually generated. Concurrency-
cap analysis is reported separately as a sensitivity, not a competing
headline.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from fin580.inference.pnl import _exit_price, _earnings_dates, RUNS_DIR
from fin580.data.crsp_loader import load_combined, price_at
from fin580.backtest.pnl_engine import compute_trade_pnl

OLD_RUNS = [f"2026-05-04-strategy1-{y}Q1_{y}Q4-target-realsar-v2_5" for y in range(2019, 2025)]
NEW_RUNS = [f"2026-05-05-strategy1-{y}Q1_{y}Q4-target-realsar-v2_5_fix" for y in range(2019, 2025)]


def build_ledger(run_dirs: list[str]) -> pd.DataFrame:
    crsp = load_combined()
    eds = _earnings_dates()
    parts = []
    for name in run_dirs:
        p = RUNS_DIR / name / "strategy_01" / "cell_results.parquet"
        if p.exists():
            parts.append(pd.read_parquet(p))
    if not parts:
        return pd.DataFrame()
    cells = pd.concat(parts, ignore_index=True).drop_duplicates(
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
            "ticker": ticker,
            "fiscal_quarter_end": fpe.isoformat(),
            "year": fpe.year,
            "qtr": (fpe.month - 1) // 3 + 1,
            "entry_date_T": T.isoformat(),
            "earnings_date": ed.isoformat(),
            "entry_price": entry_p,
            "exit_price": exit_p,
            "size_pct": size,
            "conviction_tier": r.get("conviction_tier", "?"),
            "net_return_pct": pnl["net_return_pct"],
            "net_pnl_usd": pnl["net_pnl_usd"],
        })
    return pd.DataFrame(rows).sort_values("entry_date_T").reset_index(drop=True)


def per_year(ledger: pd.DataFrame) -> pd.DataFrame:
    if len(ledger) == 0:
        return pd.DataFrame()
    g = ledger.groupby("year").agg(
        n=("net_return_pct", "count"),
        wins=("net_return_pct", lambda s: int((s > 0).sum())),
        hit_rate=("net_return_pct", lambda s: float((s > 0).mean())),
        mean_ret=("net_return_pct", "mean"),
        total_pnl=("net_pnl_usd", "sum"),
    ).reset_index()
    return g


def per_quarter(ledger: pd.DataFrame) -> pd.DataFrame:
    if len(ledger) == 0:
        return pd.DataFrame()
    return ledger.groupby(["year", "qtr"]).size().rename("n_longs").reset_index()


def diagnostic_2021(new_run_dir: str) -> pd.DataFrame:
    """For each 2021 long, pull Agent-1/Agent-2 numerics from JSONs."""
    out_dir = RUNS_DIR / new_run_dir / "strategy_01" / "agent_outputs"
    cells = pd.read_parquet(RUNS_DIR / new_run_dir / "strategy_01" / "cell_results.parquet")
    longs_2021 = cells[cells.decision == "long"]
    rows = []
    for _, r in longs_2021.iterrows():
        ticker = r["ticker"]
        fpe = r["fiscal_quarter_end"]
        a1 = json.loads((out_dir / f"{ticker}_{fpe}_agent1.json").read_text())
        a2 = json.loads((out_dir / f"{ticker}_{fpe}_agent2.json").read_text())
        a3 = json.loads((out_dir / f"{ticker}_{fpe}_agent3.json").read_text())
        active = a1["absolute_active"]
        rel_delta = a1["relative_activity_delta"]
        recovered_trailing = active - rel_delta
        components = a2.get("components", {})
        sig_raw = components.get("drilling_signal_raw")
        sig_clipped = components.get("drilling_signal_clipped")
        clipped = (
            sig_raw is not None
            and sig_clipped is not None
            and abs(sig_raw) > abs(sig_clipped) + 1e-9
        )
        rows.append({
            "ticker": ticker,
            "fpe": fpe,
            "active": active,
            "rel_delta": rel_delta,
            "trailing_avg": round(recovered_trailing, 2),
            "signal_raw": round(sig_raw, 3) if sig_raw is not None else None,
            "signal_clipped": round(sig_clipped, 3) if sig_clipped is not None else None,
            "clipped_at_+1": clipped,
            "divergence_pct": round(a3.get("divergence_pct", 0.0), 2),
            "div_class": a3.get("divergence_class", "?"),
        })
    return pd.DataFrame(rows).sort_values("fpe")


def cap_analysis(ledger: pd.DataFrame, cap: int = 8) -> pd.DataFrame:
    """Hypothetical: which longs would be excluded if max_names=cap were enforced."""
    by_qtr = ledger.groupby("fiscal_quarter_end")
    rows = []
    for fpe, grp in by_qtr:
        if len(grp) <= cap:
            continue
        # Priority: higher conviction tier first, then larger size_pct (proxy for divergence magnitude)
        tier_rank = {"high": 3, "medium": 2, "low": 1, "none": 0}
        scored = grp.copy()
        scored["tier_rank"] = scored["conviction_tier"].map(tier_rank).fillna(0)
        ranked = scored.sort_values(["tier_rank", "size_pct"], ascending=[False, False])
        kept = ranked.head(cap)
        excluded = ranked.iloc[cap:]
        for _, ex in excluded.iterrows():
            rows.append({
                "fpe": fpe,
                "n_longs": len(grp),
                "excluded_ticker": ex["ticker"],
                "excluded_tier": ex["conviction_tier"],
                "excluded_pnl_usd": ex["net_pnl_usd"],
            })
    return pd.DataFrame(rows)


# ===== Build ledgers =====
print("=" * 78)
print("Building OLD v2.5 ledger...")
old = build_ledger(OLD_RUNS)
print(f"  {len(old)} trades")

print("Building NEW v2.5_fix ledger...")
new = build_ledger(NEW_RUNS)
print(f"  {len(new)} trades")
print()

# ===== 1. Per-year side-by-side =====
print("=" * 78)
print("1. PER-YEAR LEDGER  (old v2.5  vs  v2.5_fix)")
print("=" * 78)
old_y = per_year(old).rename(columns={c: f"old_{c}" for c in ["n", "wins", "hit_rate", "mean_ret", "total_pnl"]})
new_y = per_year(new).rename(columns={c: f"new_{c}" for c in ["n", "wins", "hit_rate", "mean_ret", "total_pnl"]})
combined = pd.merge(old_y, new_y, on="year", how="outer").fillna(0)
for col in ["old_n", "old_wins", "new_n", "new_wins"]:
    combined[col] = combined[col].astype(int)
print(combined.to_string(index=False))
print()
print(f"OLD totals:  n={old_y['old_n'].sum()}, wins={old_y['old_wins'].sum()}, "
      f"hit_rate={(old['net_return_pct'] > 0).mean():.3f}, "
      f"mean_ret={old['net_return_pct'].mean():+.4f}, "
      f"total_pnl=${old['net_pnl_usd'].sum():+,.0f}")
print(f"NEW totals:  n={new_y['new_n'].sum()}, wins={new_y['new_wins'].sum()}, "
      f"hit_rate={(new['net_return_pct'] > 0).mean():.3f}, "
      f"mean_ret={new['net_return_pct'].mean():+.4f}, "
      f"total_pnl=${new['net_pnl_usd'].sum():+,.0f}")
print()

# ===== 2. Per-quarter trade counts =====
print("=" * 78)
print("2. PER-QUARTER TRADE COUNTS  (flag any quarter > 8)")
print("=" * 78)
oldq = per_quarter(old).rename(columns={"n_longs": "old_n"})
newq = per_quarter(new).rename(columns={"n_longs": "new_n"})
qmerge = pd.merge(oldq, newq, on=["year", "qtr"], how="outer").fillna(0)
qmerge[["old_n", "new_n"]] = qmerge[["old_n", "new_n"]].astype(int)
qmerge["over_cap"] = qmerge["new_n"] > 8
qmerge_show = qmerge[(qmerge.old_n > 0) | (qmerge.new_n > 0)].sort_values(["year", "qtr"])
print(qmerge_show.to_string(index=False))
print()

# ===== 3. Trade diff =====
print("=" * 78)
print("3. TRADE DIFF  (added/dropped vs old v2.5)")
print("=" * 78)
old_keys = set(zip(old.ticker, old.fiscal_quarter_end))
new_keys = set(zip(new.ticker, new.fiscal_quarter_end))
dropped = old_keys - new_keys
added = new_keys - old_keys
common = old_keys & new_keys

print(f"\nDROPPED (in old, not in fixed) — {len(dropped)} trades:")
if dropped:
    drop_df = old[old.apply(lambda r: (r["ticker"], r["fiscal_quarter_end"]) in dropped, axis=1)]
    print(drop_df[["ticker", "fiscal_quarter_end", "size_pct", "net_return_pct", "net_pnl_usd"]].to_string(index=False))
    print(f"  sum of dropped P&L:  ${drop_df.net_pnl_usd.sum():+,.0f}")

print(f"\nADDED (in fixed, not in old) — {len(added)} trades:")
if added:
    add_df = new[new.apply(lambda r: (r["ticker"], r["fiscal_quarter_end"]) in added, axis=1)]
    print(add_df[["ticker", "fiscal_quarter_end", "size_pct", "conviction_tier", "net_return_pct", "net_pnl_usd"]].to_string(index=False))
    print(f"  sum of added P&L:    ${add_df.net_pnl_usd.sum():+,.0f}")

print(f"\nCOMMON ({len(common)} trades) — sizing/PnL may differ between old and fixed:")
if common:
    c_old = old[old.apply(lambda r: (r["ticker"], r["fiscal_quarter_end"]) in common, axis=1)].set_index(["ticker", "fiscal_quarter_end"])
    c_new = new[new.apply(lambda r: (r["ticker"], r["fiscal_quarter_end"]) in common, axis=1)].set_index(["ticker", "fiscal_quarter_end"])
    rows = []
    for k in common:
        o = c_old.loc[k]
        n = c_new.loc[k]
        rows.append({
            "ticker": k[0], "fpe": k[1],
            "old_size": o["size_pct"], "new_size": n["size_pct"],
            "old_tier": o["conviction_tier"], "new_tier": n["conviction_tier"],
            "ret_pct": o["net_return_pct"],
            "old_pnl": o["net_pnl_usd"], "new_pnl": n["net_pnl_usd"],
            "pnl_delta": n["net_pnl_usd"] - o["net_pnl_usd"],
        })
    cdf = pd.DataFrame(rows).sort_values("fpe")
    print(cdf.to_string(index=False))
    print(f"  sum of pnl_delta on common trades:   ${cdf.pnl_delta.sum():+,.0f}")
print()

# ===== 4. 2021 over-firing diagnostic =====
print("=" * 78)
print("4. 2021 RECOVERY-REGIME DIAGNOSTIC  (long cells only)")
print("=" * 78)
diag = diagnostic_2021("2026-05-05-strategy1-2021Q1_2021Q4-target-realsar-v2_5_fix")
print(diag.to_string(index=False))
print()
clipped_count = int(diag["clipped_at_+1"].sum())
zero_baseline = int((diag["trailing_avg"] <= 1.0).sum())
print(f"Of 2021 longs ({len(diag)}):")
print(f"  clipped at signal=+1.0:           {clipped_count}")
print(f"  trailing_avg <= 1 (near-zero):    {zero_baseline}")
print(f"  divergence_pct = +10.0% exactly:  {int((diag.divergence_pct >= 9.99).sum())}")
print()

# ===== 5. Concurrency-cap sensitivity =====
print("=" * 78)
print("5. CONCURRENCY-CAP SENSITIVITY  (HYPOTHETICAL — cap not in inference code)")
print("=" * 78)
print(f"NOTE: max_names=8 is recorded in manifest at runner.py:146 only.")
print(f"      Inference pipeline (fin580/inference/pnl.py) does NOT enforce it.")
print(f"      Headline P&L above counts every long.\n")
cap_df = cap_analysis(new, cap=8)
if len(cap_df) == 0:
    print("No quarter has more than 8 longs — cap would not have bound anywhere.")
else:
    print("Quarters where cap would bind:")
    print(cap_df.to_string(index=False))
    print(f"\nIF cap had been enforced, these {len(cap_df)} longs would have been excluded.")
    print(f"  sum of excluded P&L:  ${cap_df.excluded_pnl_usd.sum():+,.0f}")
    new_capped_pnl = new.net_pnl_usd.sum() - cap_df.excluded_pnl_usd.sum()
    print(f"\n  Headline (no cap):    ${new.net_pnl_usd.sum():+,.0f}")
    print(f"  Hypothetical (capped): ${new_capped_pnl:+,.0f}")
print()

# Save ledgers
out = Path("runs/inference")
out.mkdir(parents=True, exist_ok=True)
new.to_csv(out / "strategy01_trades_v2_5_fix.csv", index=False)
old.to_csv(out / "strategy01_trades_v2_5_OLD.csv", index=False)
print(f"Saved: {out / 'strategy01_trades_v2_5_fix.csv'}, {out / 'strategy01_trades_v2_5_OLD.csv'}")
