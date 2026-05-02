"""FIN 580 Final Project — Demo Dashboard (single-page, story-driven).

Walk-through-style dashboard for a classroom demo. Scroll top to bottom — each
section answers one question. Sidebar has shortcut links.

Run:    streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Make the fin580 package importable when streamlit runs from inside dashboard/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

RUNS_DIR = ROOT / "runs"
PHASE1_OUTPUT = ROOT / "phase1" / "output"
HEADLINE_RUN = RUNS_DIR / "2026-04-30-strategy1-2024Q1_2024Q4-target-realsar"

st.set_page_config(
    page_title="FIN 580 — Multi-Agent Permian Trading Demo",
    page_icon="🛰️",
    layout="wide",
)

# -----------------------------------------------------------------------------
# Sidebar (just navigation hints)
# -----------------------------------------------------------------------------
st.sidebar.title("FIN 580 Final Demo")
st.sidebar.markdown(
    "Scroll the page top → bottom to follow the story. "
    "Or jump to a section:"
)
st.sidebar.markdown(
    """
    - [1. The Question](#section-1)
    - [2. Real Data the System Reads](#section-2)
    - [3. The 5 Agents](#section-3)
    - [4. Worked Example: FANG 2024-Q2](#section-4)
    - [5. The Two Trades](#section-5)
    - [6. Comparison vs Baselines](#section-6)
    - [7. Honest Limitations](#section-7)
    """
)

# -----------------------------------------------------------------------------
# Cached loaders
# -----------------------------------------------------------------------------
@st.cache_data
def load_cell_results():
    p = HEADLINE_RUN / "strategy_01" / "cell_results.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data
def load_strategy1_trades():
    p = RUNS_DIR / "inference" / "strategy01_trades_2024.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


@st.cache_data
def load_headline_table():
    p = RUNS_DIR / "inference" / "headline_table_2024.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


@st.cache_data
def load_evidence_pack():
    p = RUNS_DIR / "inference" / "evidence_pack.json"
    return json.loads(p.read_text()) if p.exists() else {}


def load_agent_json(ticker: str, fpe: str, agent: str) -> dict | None:
    p = HEADLINE_RUN / "strategy_01" / "agent_outputs" / f"{ticker}_{fpe}_{agent}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def load_sar_aggregate(ticker: str, fpe: str, T: str):
    p = (
        PHASE1_OUTPUT
        / "sentinel1_cache"
        / "firm_quarter_aggregates"
        / f"{ticker}_{fpe}_{T}_n5.json"
    )
    return json.loads(p.read_text()) if p.exists() else None


# =============================================================================
# Title block
# =============================================================================
st.title("🛰️ Multi-Agent Permian Trading System")
st.caption("FIN 580 Final Project — End-to-End Demo with Real Sentinel-1 SAR")

# Top-level scoreboard
trades = load_strategy1_trades()
cells = load_cell_results()
ev_pack = load_evidence_pack()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Window", "2024 Q1–Q4")
c2.metric("Cells evaluated", f"{len(cells)}")
c3.metric("Long trades fired", f"{len(trades)}")
if len(trades):
    wins = (trades.net_return_pct > 0).sum()
    c4.metric("Hit rate", f"{wins/len(trades):.0%}")
    c5.metric("Mean net return", f"{trades.net_return_pct.mean()*100:+.2f}%")

st.divider()

# =============================================================================
# Section 1: The Question
# =============================================================================
st.header("1. What are we trying to answer?", anchor="section-1")

st.markdown(
    """
    > **Can a multi-agent LLM system fed by real satellite radar of drilling
    activity produce directionally-correct long trades for Permian E&P stocks
    in the two weeks before earnings?**

    The system runs on **real public data** for 2024. It evaluates every
    (firm × fiscal-quarter) **cell** — 10 firms × 4 quarters = 40 cells — and
    decides long / no_trade 14 days before each earnings release.

    *Quick glossary:*  **cell** = one (firm × quarter) trade decision.
    **pad** = a real drilling pad in the Permian basin (coordinates from
    FracFocus). A cell fires a long when **≥3 of 5 sampled pads** show
    active drilling on Sentinel-1 SAR.
    """
)

st.divider()

# =============================================================================
# Section 2: Real Data
# =============================================================================
st.header("2. What real data does the system actually read?", anchor="section-2")

st.markdown(
    "Every input below is **real public data**. No synthetic substitutes — "
    "if a source were synthetic, we say so explicitly."
)

provenance_df = pd.DataFrame([
    {"Input": "🛰️ Sentinel-1 SAR backscatter (radar pixels, VV+VH)",
     "Where it comes from": "Microsoft Planetary Computer (free, no auth)",
     "Status": "✅ REAL"},
    {"Input": "📍 Pad coordinates + completion dates",
     "Where it comes from": "FracFocus bulk download — 12,376 Permian permits",
     "Status": "✅ REAL"},
    {"Input": "🛢️ WTI weekly spot price",
     "Where it comes from": "EIA RWTCw.xls (1986-2026)",
     "Status": "✅ REAL"},
    {"Input": "🪨 Permian rig count",
     "Where it comes from": "EIA Drilling Productivity Report",
     "Status": "✅ REAL"},
    {"Input": "📊 Analyst revenue consensus",
     "Where it comes from": "IBES Detail-History (WRDS), REVDATS-corrected",
     "Status": "✅ REAL"},
    {"Input": "📰 News articles for verification",
     "Where it comes from": "GDELT 2.0 DOC API (T-14 enforced)",
     "Status": "✅ REAL"},
    {"Input": "💵 Equity prices for P&L",
     "Where it comes from": "CRSP daily (WRDS) + yfinance Adj Close 2025",
     "Status": "✅ REAL"},
    {"Input": "📅 Earnings dates",
     "Where it comes from": "IBES ANNDATS_ACT (proxy)",
     "Status": "🟡 Real, but proxy"},
    {"Input": "🔧 SAR change-detection thresholds (1.5 dB / 0.5 dB)",
     "Where it comes from": "Ben-David 2021, Glaeser et al. 2020 literature",
     "Status": "🟡 Calibration parameter (not data)"},
])
st.dataframe(provenance_df, hide_index=True, width="stretch")

st.divider()

# =============================================================================
# Section 3: The 5 Agents
# =============================================================================
st.header("3. The five-agent pipeline", anchor="section-3")

st.markdown(
    """
    For every cell, the system runs five specialist agents in sequence. Numbers
    that drive trades come from **deterministic Python code**; LLMs only write
    qualitative reasoning.
    """
)

agents_df = pd.DataFrame([
    {"Step": "1. GIS Detection", "Agent": "🛰️ Agent 1",
     "Job": "Read real Sentinel-1 radar pixels at 5 representative pads. "
            "Apply +1.5 dB change-detection rule.",
     "LLM?": "No (pure code)"},
    {"Step": "2. Revenue Forecast", "Agent": "💰 Agent 2",
     "Job": "Compute deterministic forecast = consensus × (1 + 0.10 × drilling_signal). "
            "LLM only writes qualitative outlook.",
     "LLM?": "Yes (annotation only)"},
    {"Step": "3. Consensus Comparison", "Agent": "⚖️ Agent 3",
     "Job": "Compare forecast vs IBES consensus. Classify: strong_beat / modest_beat / "
            "in_line / modest_miss / strong_miss. Cells outside modest_beat range "
            "**short-circuit to no_trade**.",
     "LLM?": "No (pure code)"},
    {"Step": "4. News Verification", "Agent": "📰 Agent 4",
     "Job": "Read GDELT articles up to T-14. If activity already disclosed, "
            "downgrade conviction.",
     "LLM?": "Yes (defensive fallback if fails)"},
    {"Step": "5. Investment Board", "Agent": "🏛️ Agent 5",
     "Job": "Bull/Bear LLM debate moderated by Arbiter. Arbiter assigns conviction "
            "tier; deterministic lookup → size (high=15%, medium=10%, low=5%, none=0%).",
     "LLM?": "Yes (debate only — size in code)"},
])
st.dataframe(agents_df, hide_index=True, width="stretch")

st.info(
    "**Why this design?**  An LLM is good at reading news and debating; an LLM is "
    "bad at picking exact numbers. So the *numbers* — forecast, divergence, size — "
    "are computed in Python. The LLM does the natural-language work it's good at."
)

st.divider()

# =============================================================================
# Section 4: Worked Example
# =============================================================================
st.header("4. Walk through one cell end-to-end", anchor="section-4")

st.markdown(
    "Pick a (ticker, quarter) and see what each agent produced. "
    "**Recommended demo cell:** `FANG / 2024-Q2` — one of the two trades that fired."
)

if cells.empty:
    st.warning("No cell results available.")
else:
    col1, col2 = st.columns(2)
    default_ticker_idx = (
        list(sorted(cells.ticker.unique())).index("FANG")
        if "FANG" in cells.ticker.unique() else 0
    )
    ticker = col1.selectbox(
        "Ticker", sorted(cells.ticker.unique()), index=default_ticker_idx,
    )
    quarter_options = sorted(
        cells[cells.ticker == ticker].fiscal_quarter_end.unique()
    )
    default_quarter_idx = (
        quarter_options.index("2024-06-30") if "2024-06-30" in quarter_options else 0
    )
    fpe = col2.selectbox(
        "Fiscal quarter end", quarter_options, index=default_quarter_idx,
    )

    cell_row = cells[
        (cells.ticker == ticker) & (cells.fiscal_quarter_end == fpe)
    ].iloc[0]

    # Look up Agent 1 + Agent 3 numbers so the banner can show why
    a1_preview = load_agent_json(ticker, fpe, "agent1") or {}
    a3_preview = load_agent_json(ticker, fpe, "agent3") or {}
    n_active_preview = (
        a1_preview.get("n_newly_active", 0)
        + a1_preview.get("n_continuously_active", 0)
    )
    n_pads_preview = n_active_preview + a1_preview.get("n_idle", 0)
    div_preview = a3_preview.get("divergence_pct")

    # Decision banner — one short line
    if cell_row["decision"] == "long":
        st.success(
            f"📈 **LONG** — {cell_row['conviction_tier']} conviction, "
            f"{cell_row['final_size_pct']:.0%} size  ·  "
            f"{n_active_preview}/{n_pads_preview} pads active  ·  "
            f"divergence {div_preview:+.1f}% vs consensus"
        )
    else:
        err = str(cell_row.get("error") or "")
        if err:
            st.error(f"Cell errored: {err[:140]}")
        elif n_pads_preview:
            st.info(
                f"🚫 **NO TRADE** — only {n_active_preview}/{n_pads_preview} pads active "
                f"({div_preview:+.1f}% divergence; need ≥ 3 active for the gate to open)"
            )
        else:
            st.info("🚫 **NO TRADE** — Agent 3 gate fired.")

    # Agent 1 details
    with st.expander("🛰️ **Step 1 — Agent 1 (GIS Detection)**", expanded=True):
        a1 = load_agent_json(ticker, fpe, "agent1")
        if a1 and "error" not in a1:
            cols = st.columns(4)
            cols[0].metric("Newly active pads", a1["n_newly_active"])
            cols[1].metric("Continuously active", a1["n_continuously_active"])
            cols[2].metric("Idle", a1["n_idle"])
            cols[3].metric("Active share", f"{a1['share_active']:.0%}")
            st.caption(
                f"`relative_activity_delta = {a1['relative_activity_delta']:+.2f}` "
                "— activity now vs trailing baseline."
            )
            sar_T = cell_row["decision_date_T"]
            sig = load_sar_aggregate(ticker, fpe, sar_T)
            if sig and "pad_classifications" in sig:
                st.markdown("**Per-pad classifications from real radar pixels:**")
                pads_df = pd.DataFrame(sig["pad_classifications"])
                st.dataframe(pads_df, hide_index=True, width="stretch")
                st.caption(
                    f"This cell read **{sig['n_observations_total']} real Sentinel-1 "
                    f"acquisitions** across {sig['n_pads_sampled']} representative pads."
                )
        else:
            st.warning("Agent 1 output not available for this cell.")

    with st.expander("💰 **Step 2 — Agent 2 (Revenue Forecast)**"):
        a2 = load_agent_json(ticker, fpe, "agent2")
        if a2 and "error" not in a2:
            cols = st.columns(2)
            cols[0].metric(
                "Deterministic revenue forecast",
                f"${a2['revenue_forecast_usd']/1e6:,.0f}M"
            )
            comps = a2.get("components", {})
            if comps.get("consensus_anchor_usd"):
                cols[1].metric(
                    "IBES consensus anchor",
                    f"${comps['consensus_anchor_usd']/1e6:,.0f}M"
                )
            if comps.get("drilling_signal_clipped") is not None:
                st.caption(
                    f"`drilling_signal = {comps.get('drilling_signal_clipped'):+.2f}`, "
                    f"`alpha = {comps.get('alpha')}`"
                )
            st.markdown("**LLM qualitative outlook** (does NOT drive the number):")
            st.write(a2.get("outlook_paragraph", "—"))
        else:
            st.caption(
                "Agent 2 did not run — Agent 3 short-circuited the cell, or the "
                "cell errored upstream."
            )

    with st.expander("⚖️ **Step 3 — Agent 3 (Consensus Comparison)**"):
        a3 = load_agent_json(ticker, fpe, "agent3")
        if a3 and "error" not in a3:
            cols = st.columns(3)
            cols[0].metric("Divergence", f"{a3['divergence_pct']:+.2f}%")
            cols[1].metric("Class", a3["divergence_class"])
            cols[2].metric("Confidence", a3["confidence"])
            st.caption(
                "Threshold rule (Python, not LLM): strong_beat > +15% • "
                "modest_beat +5% to +15% • in_line ±5% • modest_miss −5% to −15% • "
                "strong_miss < −15%"
            )
            if a3["divergence_class"] not in ("modest_beat", "strong_beat"):
                st.warning(
                    f"Divergence class is **{a3['divergence_class']}** → "
                    "Agent-3 gate fires → **no_trade**. Agents 4 and 5 do not run."
                )
            else:
                st.success(
                    f"Divergence class is **{a3['divergence_class']}** → cell proceeds "
                    "to Agents 4 and 5."
                )
        else:
            st.caption("No Agent 3 output for this cell.")

    with st.expander("📰 **Step 4 — Agent 4 (News Verification)**"):
        a4 = load_agent_json(ticker, fpe, "agent4")
        if a4 and "error" not in a4:
            cols = st.columns(2)
            cols[0].metric("Articles in window", a4.get("n_articles_in_window", 0))
            cols[1].metric(
                "Already disclosed?",
                "Yes" if a4.get("gdelt_disclosed") else "No"
            )
            reasoning = str(a4.get("reasoning", ""))
            if "fallback" in reasoning.lower():
                st.warning(
                    "⚠️ Agent 4 hit the **defensive fallback path** — the LLM "
                    "returned malformed JSON or rate-limited. Default no-disclosure "
                    "result was used so the cell could proceed."
                )
            st.write(reasoning)
        else:
            st.caption(
                "Agent 4 did not run for this cell (likely Agent-3 short-circuit)."
            )

    with st.expander("🏛️ **Step 5 — Agent 5 (Investment Board: Bull/Bear/Arbiter)**"):
        a5 = load_agent_json(ticker, fpe, "agent5")
        if a5 and "error" not in a5:
            cols = st.columns(3)
            cols[0].metric("Decision", a5.get("decision", "—"))
            cols[1].metric("Conviction", a5.get("conviction_tier", "—"))
            cols[2].metric("Size", f"{a5.get('final_size_pct', 0):.0%}")
            st.markdown("**Bull side:**")
            st.write(a5.get("bull_opinion", {}).get("reasoning_short", "—"))
            st.markdown("**Bear side:**")
            st.write(a5.get("bear_opinion", {}).get("reasoning_short", "—"))
            st.markdown("**Arbiter verdict:**")
            st.write(a5.get("arbiter_reasoning", "—"))
        else:
            st.caption("Agent 5 did not run (Agent-3 short-circuit or cell error).")

st.divider()

# =============================================================================
# Section 5: The Two Trades
# =============================================================================
st.header("5. The two trades that fired in 2024", anchor="section-5")

_MONTH_TO_QUARTER = {3: "Q1", 6: "Q2", 9: "Q3", 12: "Q4"}

if len(trades) == 0:
    st.warning("No trades in the strategy01 ledger yet.")
else:
    # Pretty per-trade card
    for _, t in trades.iterrows():
        outcome = "✅ WIN" if t["net_return_pct"] > 0 else "❌ LOSS"
        month = int(t["fiscal_quarter_end"][5:7])
        year = t["fiscal_quarter_end"][:4]
        quarter_label = f"{_MONTH_TO_QUARTER.get(month, month)} {year}"
        st.markdown(
            f"### {t['ticker']} — {quarter_label} → {outcome}"
        )
        cols = st.columns(5)
        cols[0].metric("Entry T-14", f"${t['entry_price']:.2f}")
        cols[1].metric("Exit (T+2 trading)", f"${t['exit_price']:.2f}")
        cols[2].metric(
            "Net return",
            f"{t['net_return_pct']*100:+.2f}%",
            delta=f"{t['gross_return_pct']*100:+.2f}% gross",
        )
        cols[3].metric("Position size", f"{t['size_pct']:.0%}")
        cols[4].metric("$ P&L (on $1M)", f"${t['net_pnl_usd']:,.0f}")
        st.caption(
            f"Entry date: {t['entry_date_T']} • Exit date: {t['exit_date']}"
        )
        st.markdown("")

    # Aggregate metrics (incl. Sharpe)
    from fin580.inference.pnl import strategy_metrics
    m = strategy_metrics(trades)
    st.markdown("**Aggregate metrics across the trade ledger:**")
    mc = st.columns(4)
    mc[0].metric("Hit rate", f"{m['hit_rate']:.0%}")
    mc[1].metric("Mean net return", f"{m['mean_net_return_pct']*100:+.2f}%")
    sharpe_q = m['sharpe_quarterly'] or 0
    mc[2].metric(
        "Sharpe (per-trade)",
        f"{sharpe_q:.2f}",
        help="Computed as mean(net_return) / std(net_return) over the trade set. "
             "Per-trade scale, not annualised. With n=2 trades the std is "
             "essentially uninformative, so treat as a point estimate only."
    )
    mc[3].metric("Max drawdown", f"{(m['max_drawdown_pct'] or 0)*100:+.2f}%")

    # Cumulative
    sorted_t = trades.sort_values("entry_date_T").reset_index(drop=True)
    sorted_t["cum_growth"] = (1.0 + sorted_t.net_return_pct).cumprod()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[sorted_t.iloc[0]["entry_date_T"]] + list(sorted_t.entry_date_T),
        y=[1.0] + list(sorted_t.cum_growth),
        mode="lines+markers", marker_size=10,
        line=dict(color="steelblue", width=3),
        name="Cumulative growth",
    ))
    fig.add_hline(y=1.0, line_dash="dash", line_color="gray")
    fig.update_layout(
        title="Cumulative equity (real Sentinel-1 SAR Strategy 1)",
        xaxis_title="Entry date",
        yaxis_title="Growth factor (start = 1.0)",
        height=350,
    )
    st.plotly_chart(fig, width="stretch")

st.divider()

# =============================================================================
# Section 6: Comparison
# =============================================================================
st.header("6. How does the multi-agent system compare to baselines?",
          anchor="section-6")

headline = load_headline_table()
if headline.empty:
    st.warning("Headline table not yet generated.")
else:
    # Add labels for nicer chart
    strat_labels = {
        1: "1. Multi-agent (real SAR)",
        2: "2. No-news ablation",
        3: "3. Analyst revisions",
        4: "4. WTI momentum",
        5: "5. Permian rig count",
        6: "6. Equal-weight",
        7: "7. XLE buy-hold",
        8: "8. 12-1 momentum",
        9: "9. Value composite",
        10: "10. Quality composite",
    }
    headline["label"] = headline["strategy"].map(strat_labels)

    fig = px.bar(
        headline.sort_values("hit_rate", ascending=True),
        x="hit_rate", y="label", orientation="h",
        text="hit_rate",
        title="Hit rate by strategy (2024 — same window, same costs, real data)",
        labels={"label": "", "hit_rate": "Hit rate"},
        color="strategy",
    )
    fig.update_traces(texttemplate="%{text:.0%}", textposition="outside")
    fig.add_vline(x=0.5, line_dash="dash", line_color="gray",
                  annotation_text="Coin-flip", annotation_position="top right")
    fig.update_layout(height=420, showlegend=False, xaxis_tickformat=".0%")
    st.plotly_chart(fig, width="stretch")

    st.markdown(
        """
        **Reading this chart:**
        - Strategy 7 (XLE buy-hold) shows 100% — it has only 1 trade so the rate is degenerate.
        - Strategy 1 (us) is at 50% on 2 trades — small sample, but **higher than every
          deterministic single-signal baseline**.
        - Strategies 3-10 cluster between 19% and 33% — 2024 was a tough year for
          classical signals (rangebound WTI, no momentum to ride).
        """
    )

st.divider()

# =============================================================================
# Section 7: Honest Limitations
# =============================================================================
st.header("7. What we honestly cannot claim", anchor="section-7")

st.warning(
    "**The most honest framing:** With n = 2 trades, no statistical test rejects "
    "the null hypothesis that the system is 50% / coin-flip. Bootstrap p = 0.245, "
    "exact-binomial p = 0.750. The 95% CI on hit rate is essentially uninformative."
)

st.markdown(
    """
    **Why so few trades?** Two project-scope choices:

    1. **Real data only** — we explicitly chose not to scale the sample with synthetic
       substitutes. Real Sentinel-1 SAR ingestion is bandwidth-limited (~50 acquisitions
       per pad per year via cloud-optimised GeoTIFF range-reads).
    2. **One year** — the 2024 window is the most recent calendar year for which all
       real data sources are simultaneously available without paid licenses. The pipeline
       supports the originally-planned 2021-2025 window; running it on real data is
       documented as future work in §12.9 of the paper.

    **What we *can* claim is mechanical:** the α=0 ablation and no-satellite
    ablation both produce **zero long entries** by construction. So whatever signal
    the system did produce in 2024 is mechanically traceable to the satellite input
    — not to the LLM scaffolding.
    """
)

# H1 / H2 inference numbers
if ev_pack:
    h1 = ev_pack.get("primary_test_H1", {})
    h2 = ev_pack.get("secondary_test_H2", {})
    cols = st.columns(2)
    with cols[0]:
        st.markdown("**H1: hit rate > 50%**")
        st.write(f"- Bootstrap p-value: **{h1.get('p_value_one_sided')}**")
        st.write(f"- 95% CI: {h1.get('ci_95')}")
        st.write(f"- Reject H0 = 50%: **{h1.get('reject_50')}**")
    with cols[1]:
        st.markdown("**H2: S1 hit rate > S3 by 3pp**")
        st.write(f"- Observed gap: **+{h2.get('obs_diff', 0)*100:.1f}pp**")
        st.write(f"- Bootstrap p-value: **{h2.get('p_one_sided_diff_le_threshold')}**")
        st.write(f"- Reject H0: **{h2.get('reject_null_at_5pct')}**")

st.divider()

# =============================================================================
# Footer
# =============================================================================
st.caption(
    "FIN 580 — Spring 2026 — Vincent N. W. — "
    "Multi-Agent Permian Trading System with Real Sentinel-1 SAR. "
    "Run reproducibility command: "
    "`FIN580_SAR_MODE=real_sentinel1 python -m fin580.backtest.runner "
    "--strategy 1 --window 2024Q1-2024Q4 --cm-label target --run-suffix realsar`"
)
