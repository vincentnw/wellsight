"""Smoke tests for the PnL engine (spec Section 6.3, plan Task 20)."""

from fin580.backtest.pnl_engine import compute_trade_pnl


def test_long_trade_with_dividend_and_costs():
    pnl = compute_trade_pnl(
        entry_price=100.0,
        exit_price=105.0,
        size_pct=0.10,
        capital_usd=1_000_000,
        cost_bps=30,
    )
    # 10% of $1M = $100k position. Gross return $5k. Costs $300. Net $4700.
    assert 4500 <= pnl["net_pnl_usd"] <= 4900, pnl


def test_no_trade_returns_zero():
    pnl = compute_trade_pnl(
        entry_price=100.0,
        exit_price=110.0,
        size_pct=0.0,
        capital_usd=1_000_000,
        cost_bps=30,
    )
    assert pnl["net_pnl_usd"] == 0.0
    assert pnl["position_value_usd"] == 0.0


def test_loss_with_costs_amplifies_loss():
    pnl = compute_trade_pnl(
        entry_price=100.0,
        exit_price=98.0,
        size_pct=0.15,
        capital_usd=1_000_000,
        cost_bps=30,
    )
    # 15% × $1M = $150k. Gross loss = -$3000. Costs = $450. Net = -$3450.
    assert -3500 <= pnl["net_pnl_usd"] <= -3300, pnl


def test_costs_scale_with_position_size():
    small = compute_trade_pnl(
        entry_price=100.0, exit_price=100.0, size_pct=0.05,
        capital_usd=1_000_000, cost_bps=30,
    )
    large = compute_trade_pnl(
        entry_price=100.0, exit_price=100.0, size_pct=0.15,
        capital_usd=1_000_000, cost_bps=30,
    )
    assert large["cost_usd"] == 3 * small["cost_usd"]
