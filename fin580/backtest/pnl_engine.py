"""P&L engine (spec Section 6.3).

Computes a single trade's gross / net return given entry/exit prices, position
size, and round-trip transaction cost in basis points."""

from __future__ import annotations


def compute_trade_pnl(
    *,
    entry_price: float,
    exit_price: float,
    size_pct: float,
    direction: str = "long",
    capital_usd: float = 1_000_000,
    cost_bps: int = 30,
) -> dict:
    if size_pct == 0.0 or direction == "no_trade":
        return {
            "gross_return_pct": 0.0,
            "net_return_pct": 0.0,
            "gross_pnl_usd": 0.0,
            "net_pnl_usd": 0.0,
            "position_value_usd": 0.0,
            "cost_usd": 0.0,
        }
    position_value_usd = capital_usd * size_pct
    # Shorts profit when price falls; longs profit when price rises.
    if direction == "short":
        gross_return_pct = (entry_price - exit_price) / entry_price
    else:
        gross_return_pct = (exit_price - entry_price) / entry_price
    gross_pnl_usd = position_value_usd * gross_return_pct
    cost_usd = position_value_usd * (cost_bps / 10_000)  # round-trip already
    net_pnl_usd = gross_pnl_usd - cost_usd
    net_return_pct = (
        net_pnl_usd / position_value_usd if position_value_usd else 0.0
    )
    return {
        "gross_return_pct": gross_return_pct,
        "net_return_pct": net_return_pct,
        "gross_pnl_usd": gross_pnl_usd,
        "net_pnl_usd": net_pnl_usd,
        "position_value_usd": position_value_usd,
        "cost_usd": cost_usd,
    }
