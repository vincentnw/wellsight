"""Strategy registry. Each strategy module exposes a `signal(...)` function."""

from fin580.backtest.strategies import (
    s01_full_system,
    s02_no_news,
    s03_analyst_revision,
    s04_oil_momentum,
    s05_bhi_basin,
    s06_equal_weight,
    s07_xle_buy_hold,
    s08_stock_momentum,
    s09_value,
    s10_quality,
)

REGISTRY = {
    1: s01_full_system,
    2: s02_no_news,
    3: s03_analyst_revision,
    4: s04_oil_momentum,
    5: s05_bhi_basin,
    6: s06_equal_weight,
    7: s07_xle_buy_hold,
    8: s08_stock_momentum,
    9: s09_value,
    10: s10_quality,
}
