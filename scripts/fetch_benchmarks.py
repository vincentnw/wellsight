"""Pre-fetch XES and VOO daily prices to phase1/output/benchmark_prices.csv
so the dashboard can load benchmarks without internet at runtime.

Run from project root:
    python scripts/fetch_benchmarks.py
"""
import yfinance as yf
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "phase1" / "output" / "benchmark_prices.csv"

print("Fetching XES, VOO daily prices 2019-01-01 -> 2025-03-01...")
data = yf.download(['XES', 'VOO'], start='2019-01-01', end='2025-03-01',
                   auto_adjust=True, progress=False)

# yfinance returns a multi-index dataframe. Pull Close prices.
close = data['Close'] if 'Close' in data.columns.get_level_values(0) else data
# Normalize structure: dates as index, columns = tickers
close = close.reset_index()
close = close.rename(columns={'Date': 'date'})
close['date'] = pd.to_datetime(close['date']).dt.date.astype(str)

# Reorder columns
cols = ['date'] + [c for c in close.columns if c != 'date']
close = close[cols]

print(f"Rows: {len(close)}, columns: {list(close.columns)}")
print(f"Date range: {close['date'].iloc[0]} to {close['date'].iloc[-1]}")
print("Sample:")
print(close.head(3).to_string(index=False))
print("...")
print(close.tail(3).to_string(index=False))

close.to_csv(OUT, index=False)
print(f"\nWrote {OUT}")
