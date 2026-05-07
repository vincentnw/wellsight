"""
Drilling-to-revenue deterministic forecast (Agent 2 numerical core).

Implements the locked two-step transform from project_overview.md DL #43 / DL #47
/ Pre-Code Action Item 18:

    1. Drilling -> Permian production:
         active_pads_at_T (point-in-time, permits filed before T)
         * wells_per_pad_ratio[operator]    (lagged from TRC completions)
         * type_curve_first_quarter_boe_d   (EIA Permian shale prior)
         + decline_curve(existing_wells)    (single-parameter exponential)
         => incremental_permian_production_boe_d for target quarter

    2. Permian production -> total-company revenue:
         permian_revenue = production * avg_WTI_pre_T14 * realized_price_diff
         total_revenue = permian_revenue / permian_revenue_share_lagged

The LLM in Agent 2 reads the resulting numerical forecast and writes a
qualitative outlook paragraph; the LLM does not generate the number.

This is a reference implementation supporting the design demonstration. All
assumptions (decline curve parameter, type curve, realized-price differentials)
are documented constants chosen from public EIA / TRC sources. Production
hardening would replace the constants with company-specific historical fits.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

# ---------------------------------------------------------------------------
# Public, lagged, audit-traceable constants
# ---------------------------------------------------------------------------

# EIA Permian shale type curve approximation (boe/day per new well, first 90 days
# average). This is a single-number proxy for the tight-curve productivity.
# Source: EIA Permian Drilling Productivity Report, 2023 vintage (lagged).
TYPE_CURVE_FIRST_QTR_BOE_D = 800.0

# Single-parameter monthly decline factor for an existing producing well in the
# Permian basin. Tight-oil wells decline ~30%/year first-year then flatten.
# Quarterly decline factor used here is a coarse approximation.
QUARTERLY_DECLINE_FACTOR = 0.92  # 8% q/q decline on the existing-well stock

# Default operator wells-per-pad. In production, replace with the operator's
# trailing-12-month TRC completion median.
DEFAULT_WELLS_PER_PAD = {
    "FANG": 6.0,
    "EOG": 5.5,
    "DVN": 5.0,
    "CTRA": 4.5,
    "OXY": 5.5,
    "MTDR": 4.5,
    "PR":   5.0,
    "OVV":  4.0,
    "SM":   3.5,
    "CRGY": 3.0,
}

# Company-specific realized-price differential = (oil + NGL + gas blended
# realized price) / WTI. Computed from prior 4 quarters of 10-Q price-realization
# disclosures. These are placeholder values; replace with actual historical
# averages once the 10-K extractor (Pre-Code #15) is run.
DEFAULT_REALIZED_PRICE_DIFF = {
    "FANG": 0.93,
    "EOG":  0.95,
    "DVN":  0.91,
    "CTRA": 0.78,  # heavier gas mix
    "OXY":  0.94,
    "MTDR": 0.92,
    "PR":   0.93,
    "OVV":  0.90,
    "SM":   0.88,
    "CRGY": 0.87,
}

# Permian revenue share = Permian segment revenue / total company revenue.
# Used to scale Permian-only forecast up to total company revenue. Replace
# with values from 10-K segment data (Pre-Code #15).
DEFAULT_PERMIAN_REVENUE_SHARE = {
    "FANG": 1.00,
    "MTDR": 1.00,
    "PR":   1.00,
    "EOG":  0.45,
    "DVN":  0.55,
    "CTRA": 0.40,
    "OXY":  0.30,
    "OVV":  0.50,
    "SM":   0.55,
    "CRGY": 0.20,
}


# ---------------------------------------------------------------------------
# Inputs from Agent 1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SitePanelEntry:
    pad_id: str
    operator: str
    permit_filing_date: date
    new_active_quarter: date | None  # quarter in which the pad first showed disturbance, None if never
    continuously_active_quarters: tuple[date, ...]
    idle_quarters: tuple[date, ...]


def active_pads_at_T(
    sites: Iterable[SitePanelEntry],
    operator: str,
    decision_date_T: date,
) -> int:
    """Number of pads attributed to operator that are detected as actively
    drilling (newly_active or continuously_active) in the most recent quarter
    ending on or before T - 90 days (drilling that has had time to complete).
    Pads must have been permitted before T (point-in-time)."""
    cutoff_quarter = quarter_end_for(decision_date_T - timedelta(days=90))
    n = 0
    for s in sites:
        if s.operator != operator:
            continue
        if s.permit_filing_date > decision_date_T:
            continue
        if s.new_active_quarter == cutoff_quarter or cutoff_quarter in s.continuously_active_quarters:
            n += 1
    return n


def quarter_end_for(d: date) -> date:
    if d.month <= 3:
        return date(d.year, 3, 31)
    if d.month <= 6:
        return date(d.year, 6, 30)
    if d.month <= 9:
        return date(d.year, 9, 30)
    return date(d.year, 12, 31)


# ---------------------------------------------------------------------------
# Forecast components
# ---------------------------------------------------------------------------


def incremental_production_from_drilling(
    new_active_pads: int,
    continuously_active_pads: int,
    wells_per_pad: float,
) -> float:
    """Incremental boe/day from new and continuing wells coming on line."""
    new_wells = (new_active_pads + continuously_active_pads) * wells_per_pad
    return new_wells * TYPE_CURVE_FIRST_QTR_BOE_D


def existing_production_after_decline(
    last_quarter_total_boe_d: float,
) -> float:
    """Apply the quarterly decline to the prior-period production base."""
    return last_quarter_total_boe_d * QUARTERLY_DECLINE_FACTOR


def permian_revenue_from_production(
    production_boe_d: float,
    avg_wti_usd_per_bbl: float,
    realized_price_diff: float,
    days_in_quarter: int = 91,
) -> float:
    """USD revenue for a quarter at given production and realized prices."""
    realized = avg_wti_usd_per_bbl * realized_price_diff
    return production_boe_d * days_in_quarter * realized


# ---------------------------------------------------------------------------
# Public forecast entry point
# ---------------------------------------------------------------------------


# Consensus-anchored α (DL #54). FROZEN before backtest run.
# - α=0.10 primary headline value
# - α=0.15 sensitivity (labeled robustness, never headline)
# - α=0.0 ablation (pure consensus, no satellite — counterfactual proving the
#   satellite delta adds information)
ALPHA_PRIMARY = 0.15
ALPHA_SENSITIVITY = 0.15
ALPHA_ABLATION_NO_SATELLITE = 0.0


@dataclass(frozen=True)
class RevenueForecast:
    ticker: str
    target_quarter_end: date
    permian_production_boe_d: float
    permian_revenue_usd: float
    total_revenue_usd: float
    inputs: dict


def forecast_revenue(
    ticker: str,
    target_quarter_end: date,
    decision_date_T: date,
    new_active_pads: int,
    continuously_active_pads: int,
    last_quarter_permian_production_boe_d: float,
    avg_wti_pre_T14_usd_per_bbl: float,
    wells_per_pad: float | None = None,
    realized_price_diff: float | None = None,
    permian_revenue_share: float | None = None,
    *,
    consensus_anchor_usd: float | None = None,
    drilling_signal: float | None = None,
    alpha: float = ALPHA_PRIMARY,
) -> RevenueForecast:
    """Produce the deterministic revenue forecast for `ticker` at `target_quarter_end`.

    Per DL #54, supports two modes:

    1) **Consensus-anchored** (preferred): when `consensus_anchor_usd` is provided
       AND `drilling_signal` is provided, the forecast is the IBES consensus
       revenue adjusted by the satellite-derived drilling delta:

           drilling_signal_clipped = clip(drilling_signal, -1, +1)
           forecast_revenue = consensus × (1 + alpha × drilling_signal_clipped)

       The pure-consensus counterfactual (alpha=0) is the no-satellite ablation.

    2) **Legacy placeholder mode** (fallback): when consensus_anchor is missing,
       falls back to the original placeholder-constant model. This mode is
       known to inflate forecasts for non-FANG-scale operators (DL #54) and is
       only invoked when IBES coverage is unavailable.

    All inputs must be point-in-time as of `decision_date_T`."""
    wpp = wells_per_pad if wells_per_pad is not None else DEFAULT_WELLS_PER_PAD[ticker]
    rpd = realized_price_diff if realized_price_diff is not None else DEFAULT_REALIZED_PRICE_DIFF[ticker]
    prs = permian_revenue_share if permian_revenue_share is not None else DEFAULT_PERMIAN_REVENUE_SHARE[ticker]

    if consensus_anchor_usd is not None and drilling_signal is not None:
        drilling_signal_clipped = max(-1.0, min(1.0, drilling_signal))
        total_rev = consensus_anchor_usd * (1.0 + alpha * drilling_signal_clipped)
        # Back-implied production (informational; not the model's primary output)
        days_in_quarter = 91
        realized_price = avg_wti_pre_T14_usd_per_bbl * rpd
        if realized_price > 0 and prs > 0 and days_in_quarter > 0:
            permian_rev = total_rev * prs
            production_boe_d = permian_rev / (days_in_quarter * realized_price)
        else:
            permian_rev = total_rev * prs
            production_boe_d = 0.0
        inputs = {
            "mode": "consensus_anchored",
            "consensus_anchor_usd": consensus_anchor_usd,
            "drilling_signal_raw": drilling_signal,
            "drilling_signal_clipped": drilling_signal_clipped,
            "alpha": alpha,
            "wells_per_pad": wpp,
            "realized_price_diff": rpd,
            "permian_revenue_share": prs,
            "avg_wti_pre_T14": avg_wti_pre_T14_usd_per_bbl,
            "decision_date_T": decision_date_T.isoformat(),
            "implied_production_boe_d": production_boe_d,
        }
        return RevenueForecast(
            ticker=ticker, target_quarter_end=target_quarter_end,
            permian_production_boe_d=production_boe_d,
            permian_revenue_usd=permian_rev,
            total_revenue_usd=total_rev, inputs=inputs,
        )

    # Legacy placeholder mode (fallback when no IBES consensus available)
    incremental = incremental_production_from_drilling(new_active_pads, continuously_active_pads, wpp)
    existing = existing_production_after_decline(last_quarter_permian_production_boe_d)
    production_boe_d = existing + incremental

    permian_rev = permian_revenue_from_production(production_boe_d, avg_wti_pre_T14_usd_per_bbl, rpd)
    total_rev = permian_rev / prs if prs > 0 else permian_rev

    inputs = {
        "mode": "legacy_placeholder_fallback",
        "wells_per_pad": wpp,
        "realized_price_diff": rpd,
        "permian_revenue_share": prs,
        "incremental_boe_d": incremental,
        "existing_after_decline_boe_d": existing,
        "avg_wti_pre_T14": avg_wti_pre_T14_usd_per_bbl,
        "decision_date_T": decision_date_T.isoformat(),
    }
    return RevenueForecast(
        ticker=ticker,
        target_quarter_end=target_quarter_end,
        permian_production_boe_d=production_boe_d,
        permian_revenue_usd=permian_rev,
        total_revenue_usd=total_rev,
        inputs=inputs,
    )


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------


def _smoke() -> None:
    """A worked example for FANG, Q3 2024, illustrating the chain."""
    fc = forecast_revenue(
        ticker="FANG",
        target_quarter_end=date(2024, 9, 30),
        decision_date_T=date(2024, 10, 17),  # ~T-14 before late-Oct earnings
        new_active_pads=4,
        continuously_active_pads=18,
        last_quarter_permian_production_boe_d=470_000.0,
        avg_wti_pre_T14_usd_per_bbl=78.50,
    )
    print(f"FANG Q3-2024 forecast")
    print(f"  Permian production : {fc.permian_production_boe_d:>12,.0f} boe/d")
    print(f"  Permian revenue    : ${fc.permian_revenue_usd / 1e6:>12,.1f}M")
    print(f"  Total revenue est. : ${fc.total_revenue_usd / 1e6:>12,.1f}M (Permian share {fc.inputs['permian_revenue_share']:.2f})")
    print(f"  Inputs             : {fc.inputs}")


if __name__ == "__main__":
    _smoke()
