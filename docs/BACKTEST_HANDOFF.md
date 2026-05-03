# Backtest Collaboration Handoff — 2019-2021 Strategy 1

**You are running:** Strategy 1 (full multi-agent, real Sentinel-1 SAR) on calendar years **2019, 2020, 2021**.

**Vincent is running:** A clean 2022-2023 re-run on his machine.

**Goal:** Extend the headline 2024 empirical claim to a 6-year window (2019-2024). Each year takes ~3-4 hours on a single machine due to LLM API rate limits.

---

## Why this is parallelizable

Each cell in the backtest makes 5+ LLM calls (Agents 2, 3, 4, 5 — Agent 5 is Bull/Bear/Arbiter = 3 calls). Cerebras free tier rate-limits to roughly 1 request every 4 seconds. **Per-call latency dominates total time**, so running on a separate machine with a separate API key gives ~linear speedup.

You will use **your own free Cerebras API key** so you don't share rate limits with Vincent.

---

## Setup (one-time, ~10-30 min)

### 1. Pull the latest repo

```bash
cd ~/wellsight  # or wherever you cloned
git pull origin main
```

This brings down code, SAR caches, GDELT caches, and the existing run dirs. **~25 MB.**

### 2. Get WRDS-licensed CSVs separately

The repo's `.gitignore` excludes WRDS-licensed data per redistribution terms. You need these 6 files in `phase1/output/`:

| File | Source | Size |
|---|---|---:|
| `ibes_tr_ibes_sal_query11220958.csv` | WRDS LSEG IBES Academic / Detail History | ~3 MB |
| `crsp_daily.csv` | WRDS CRSP Daily Stock File | ~2 MB |
| `compustat_fundq.csv` | WRDS Compustat Fundamentals Quarterly | ~50 KB |
| `equity_universe_panel.csv` | derived from above | ~30 KB |
| `permian_fraction.csv` | derived (SEC EDGAR + LLM) | ~20 KB |
| `ibes_revenue_coverage.csv` | derived from IBES master | ~30 KB |
| `earnings_dates.csv` | derived from IBES master | ~20 KB |

**Two options:**

**Option A — If you have WRDS access:** re-pull the queries yourself. See `phase1/output/data_provenance.json` in the repo for the exact query IDs and parameters Vincent used. Quick recipe:

1. Log in to https://wrds-www.wharton.upenn.edu
2. Go to **My Queries** in the left nav
3. Find the queries Vincent saved (he can share `saved_query` IDs):
   - 7294297 → IBES Detail (Rerun → Submit unchanged → CSV)
   - 7294343 → CRSP Daily (Rerun → Submit unchanged → CSV)
   - Compustat fundq (query 11220995) → Rerun → Submit
4. Download CSVs and place in `phase1/output/`

If you don't have a WRDS account, your university library or research office can almost always set one up for free in 1-2 days.

**Option B — Vincent sends you a zip** (recommended if Option A is friction):

Vincent zips `phase1/output/{ibes,crsp,compustat,equity,permian,earnings}*.csv` and shares via Slack DM, Google Drive private link, or encrypted email. After unzip, your `phase1/output/` should contain all 7 files above.

### 2. Verify Python environment

```bash
python3 -m pip install -r requirements.txt
```

You may already have most deps from the earlier SAR download work.

### 3. Get a free Cerebras API key

1. Go to https://cloud.cerebras.ai → sign up (free, no credit card).
2. Click **API Keys** in the left nav → **Create API Key** → copy the value.
3. Free tier currently allows ~30 requests/minute and ~1M tokens/day. **You will use ~150K-300K tokens running all 3 years**, so well within limits.

### 4. Create your `.env` file (do NOT commit it — already in `.gitignore`)

```bash
cat > .env <<'EOF'
CEREBRAS_API_KEY=your-key-here
FIN580_SAR_MODE=real_sentinel1
CEREBRAS_MIN_INTERVAL_SECONDS=4.0
EOF

# Source it
set -a; source .env; set +a
```

### 5. Sanity check

```bash
python3 -c "
from fin580.agents.llm_client import chat
r = chat(prompt='Reply with the JSON object {\"ok\": true}.', input_json={}, model_id='qwen-3-235b-a22b-instruct-2507', temperature=0.0)
print(r)
"
```

You should see `{'ok': True}` (or similar). If you get a 404 or 401, your API key isn't set correctly.

---

## Run the backtests

Run them **sequentially** — running multiple in parallel on one machine doesn't help (same API key shares the rate limit) and burns more time on retries.

### 2019 backtest

```bash
python3 -m fin580.backtest.runner \
    --strategy 1 \
    --window 2019Q1-2019Q4 \
    --cm-label target \
    --run-suffix realsar
```

**Expected runtime:** 3-5 hours. Output: `runs/<today>-strategy1-2019Q1_2019Q4-target-realsar/`.

### 2020 backtest

```bash
python3 -m fin580.backtest.runner \
    --strategy 1 \
    --window 2020Q1-2020Q4 \
    --cm-label target \
    --run-suffix realsar
```

**Expected runtime:** 3-5 hours.

### 2021 backtest

```bash
python3 -m fin580.backtest.runner \
    --strategy 1 \
    --window 2021Q1-2021Q4 \
    --cm-label target \
    --run-suffix realsar
```

**Expected runtime:** 3-5 hours.

### Or run all three in one command (sequential)

```bash
for year in 2019 2020 2021; do
    python3 -m fin580.backtest.runner \
        --strategy 1 \
        --window ${year}Q1-${year}Q4 \
        --cm-label target \
        --run-suffix realsar
done
```

You can run this with `nohup ... &` in the background and let it grind overnight.

---

## What to expect during execution

- The runner logs each cell as `[ticker fiscal-quarter-end] starting...` and prints agent outputs.
- Most cells will short-circuit quickly to `no_trade` (≤30 seconds) because Agent 1's radar signal doesn't pass Agent 3's modest_beat threshold. These cells skip Agents 4 and 5 entirely.
- A few cells per year will pass the gate and run full Bull/Bear/Arbiter debate (~2-3 minutes each). Watch for `decision: long` lines — those are the trades.
- **If you see `Error code: 429 - queue_exceeded`**: bump throttle. Set `CEREBRAS_MIN_INTERVAL_SECONDS=6.0` (or 8.0) and re-run. Already-completed cells skip via the per-cell `cell_complete()` check, so re-running is safe.

---

## Expected results (rough hint, based on 2024)

The 2024 backtest fired **2 long trades** out of 40 cells. The system is highly conservative; many years may produce 0-3 long trades. Don't be surprised if 2020 has 0 longs (COVID dip — drilling activity collapsed) and 2021 has more (recovery).

For reference, from Vincent's SAR aggregation analysis, expected **candidate firing cells** (cells where ≥3 of 5 pads are active — the necessary condition for `long` to fire):

| Year | Candidate firings (radar alone) |
|---|---:|
| 2019 | 5 (FANG Q2, MTDR Q3, OXY Q4, SM Q2, SM Q4) |
| 2020 | 2 (MTDR Q2, OXY Q1) |
| 2021 | 12 (drilling boom recovery) |

Of those candidates, many will be filtered out by Agents 3/4/5 (eligibility, news, Bull/Bear debate). Final long count will likely be lower.

---

## Ship results back to Vincent

When all 3 years finish, send Vincent the three run directories. They are small (~10-30 MB each):

```bash
cd /path/to/wellsight
tar czf backtest_results_2019_2021.tar.gz \
    runs/*-strategy1-2019Q1_2019Q4-target-realsar \
    runs/*-strategy1-2020Q1_2020Q4-target-realsar \
    runs/*-strategy1-2021Q1_2021Q4-target-realsar
```

**Send via:** Slack DM, Drive, email — anything works.

If you want to share via git:

```bash
git add runs/*-strategy1-{2019,2020,2021}*-target-realsar
git commit -m "Add 2019-2021 Strategy 1 backtest results"
git push origin main
```

(Run dirs are NOT in `.gitignore` so they're committable. The LLM cache `runs/_global_cache/` IS gitignored to keep the repo size sane — your individual cache will stay local.)

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'cerebras'`**
- Run `pip install cerebras_cloud_sdk`

**`Error code: 429 - queue_exceeded` repeatedly**
- Cerebras is overloaded. Wait 5 min and re-run. The runner skips already-completed cells.

**`Error code: 401 - invalid api key`**
- Re-source your `.env` or re-export `CEREBRAS_API_KEY`.

**Backtest hangs on a cell for >5 minutes**
- Likely an MPC SAR fetch retry loop (Microsoft Planetary Computer is sometimes slow). The runner has a 4-attempt retry with progressive backoff. Wait it out or kill and re-run — the per-pad SAR cache is reused.

**Cell errors with `LLM call failed after 2 attempts`**
- Cerebras transient failure. The cell is marked errored in `cell_results.parquet` but the run continues. After all years finish, identify errored cells and re-run with higher `CEREBRAS_MIN_INTERVAL_SECONDS`.

---

## Acknowledgements

You're a hero. Thanks for splitting this with Vincent — saves ~10 hours of wall-clock time vs running everything sequentially on one machine.

— Vincent (vincentnw24@gmail.com)
