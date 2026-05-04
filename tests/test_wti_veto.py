import pandas as pd

from fin580.inference.wti_veto import apply_wti_veto, wti_4w_return_at_T


def test_wti_4w_return_blocks_threshold_breach():
    wti = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-03", "2020-01-31"]),
            "wti_usd_per_bbl": [62.09, 52.70],
        }
    )

    out = wti_4w_return_at_T("2020-02-05", wti=wti)

    assert round(out["wti_4w_return_pct"], 2) == -15.12
    assert out["wti_veto"] is True
    assert out["wti_veto_reason"] == "wti_4w_return_le_minus_10pct"


def test_apply_wti_veto_zeroes_blocked_trade_only():
    trades = pd.DataFrame(
        [
            {
                "strategy": 1,
                "ticker": "SM",
                "fiscal_quarter_end": "2019-12-31",
                "entry_date_T": "2020-02-05",
                "size_pct": 0.10,
                "gross_return_pct": -0.12,
                "net_return_pct": -0.123,
                "gross_pnl_usd": -12000.0,
                "net_pnl_usd": -12300.0,
            },
            {
                "strategy": 1,
                "ticker": "OVV",
                "fiscal_quarter_end": "2021-03-31",
                "entry_date_T": "2021-04-15",
                "size_pct": 0.10,
                "gross_return_pct": 0.03,
                "net_return_pct": 0.027,
                "gross_pnl_usd": 3000.0,
                "net_pnl_usd": 2700.0,
            },
        ]
    )

    out = apply_wti_veto(trades)

    blocked = out[out["ticker"] == "SM"].iloc[0]
    kept = out[out["ticker"] == "OVV"].iloc[0]
    assert bool(blocked["wti_veto"]) is True
    assert blocked["direction_after_veto"] == "no_trade"
    assert blocked["net_pnl_usd"] == 0.0
    assert blocked["baseline_net_pnl_usd"] == -12300.0
    assert bool(kept["wti_veto"]) is False
    assert kept["direction_after_veto"] == "long"
    assert kept["net_pnl_usd"] == 2700.0
