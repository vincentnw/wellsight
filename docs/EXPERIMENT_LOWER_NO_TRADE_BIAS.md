# Experiment: Lower No-Trade Bias

**Branch:** `experiment/lower-no-trade-bias`
**Started:** 2026-05-03
**Author:** Vincent (with Claude collaborator)

## Hypothesis

The headline 2024 backtest produced only **2 long trades out of 40 cells** (1W/1L, coin-flip
hit rate). The result is statistically meaningless and economically uninteresting vs an
S&P 500 buy-and-hold baseline. The system is too conservative.

Three plausible levers to reduce no-trade bias:

1. **Bump α (Agent 2's consensus-anchor coefficient)** from 0.10 → 0.20.
   - Doubles the satellite-derived divergence relative to consensus.
   - Effectively halves the activity threshold needed to clear Agent 3's `modest_beat` gate.
   - Cheapest experiment: env var change only, reuses existing SAR cache.
2. **Bump pads-per-firm-quarter** from 5 → 20.
   - Reduces sampling variance, but with the *same* 60% activity threshold this would
     actually fire LESS often (sample-size law of large numbers). Only useful if combined
     with a lower activity threshold.
   - Cost: 13-27 hr additional SAR fetch.
3. **Lower the divergence threshold** in Agent 3 from `+5%` (modest_beat) to `+3%`.
   - Already a documented robustness check (DL #20 — threshold sweep at 5/10/15/20%).
   - Requires code change in `fin580/agents/agent3_consensus.py` (or env var if exposed).

## Phase 1: α experiment (cheap, reuses existing SAR cache)

Re-run 2024Q1-2024Q4 with `FIN580_ALPHA=0.20` (vs baseline 0.10) and compare:

| Metric | Baseline (α=0.10) | Experiment (α=0.20) |
|---|---|---|
| Trades fired | 2 | TBD |
| Hit rate | 50% | TBD |
| Cells short-circuited | 38 | TBD |
| Mean net return per trade | +0.31% | TBD |

Run command (inline env override; does NOT modify project `.env`):

```powershell
$env:FIN580_ALPHA = "0.20"
conda run -n sar-fetch --no-capture-output python -u -m fin580.backtest.runner `
    --strategy 1 --window 2024Q1-2024Q4 --cm-label target --run-suffix realsar-alpha020
```

Output run dir: `runs/<today>-strategy1-2024Q1_2024Q4-target-realsar-alpha020/`.

Compare against baseline at: `runs/2026-04-30-strategy1-2024Q1_2024Q4-target-realsar/`.

## Acceptance criteria

This experiment is meant to **inform**, not to set a new headline. Even if α=0.20 fires
more trades, switching the headline would carry a publication-credibility cost
("did you tune α to manufacture trades?"). The α=0 ablation is the project's defense.

If results show meaningful trade-count increase **with** still-coherent hit rate (>50%),
the path forward might be:
- Run a small α-sweep (0.10, 0.15, 0.20, 0.30) on 2024 only.
- Report the sweep as a robustness check in the paper, not as a replacement headline.

## Phase 2: pads-per-firm experiment (only if Phase 1 is interesting)

Bump `FIN580_SAR_PADS_PER_OP=20` and re-fetch SAR for 2024 only. Then re-run with both
α=0.20 AND 20 pads to see joint effect.

## Notes

- Do NOT cherry-pick the experimental result as the new headline. The headline is the
  pre-registered α=0.10 specification (DL #56).
- The α=0 ablation must still produce 0 trades (mechanical). The experiment doesn't
  invalidate that ablation.
- Run results into `runs/inference/` will not auto-include this experimental run; it
  stays in the experiment dir.
