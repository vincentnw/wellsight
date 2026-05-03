# Agent 3 Gate Audit — The Gate Is Inverted

**Branch:** `experiment/lower-no-trade-bias`
**Date:** 2026-05-03
**Author:** Vincent (with Claude collaborator + Codex GPT-5.5 review)

## Hypothesis

The user asked: "What if we remove the ≥3-active gate at Agent 3? Will it
improve results?"

Initial Claude response (and what turned out to be wrong): "No — removing
the gate would let weak/no-signal cells fire `long` based on LLM-debate
stochasticity rather than real edge. The α=0.20 experiment already showed
that loosening the gate worsens P&L."

Codex pushed back: "The student's core caution is sound, but the framing
is too dismissive… The flaw in the student's argument is treating 'weak
SAR signal' as equivalent to 'no tradable information,' when the system
is explicitly multi-agent." Codex proposed a **suppressed-cell audit** as
a falsification test using only existing data.

## Method

For every cell in the 2019-2024 backtest (200 cells across 5 windows),
compute the hypothetical T-14 → T+2 long return as if we had traded it,
regardless of the system's actual decision. Group by Agent 3's
`divergence_class`. If `in_line` / `modest_miss` cells (gate-blocked)
average POSITIVE return and `modest_beat` cells (gate-passed) average
NEGATIVE return, the gate is filtering **false negatives**.

## Result — the gate is inverted

| `divergence_class` | n cells | Mean net return | Median net return | Hit rate | Total P&L (10% size, $1M) |
|---|---:|---:|---:|---:|---:|
| **modest_beat** (gate **passes** → actual trades) | 15 | **−0.91%** | +0.49% | 53% | **−$13,583** |
| **in_line** (gate **blocks**) | 113 | **+1.48%** | +0.36% | 52% | **+$167,653** |
| **modest_miss** (gate **blocks**) | 72 | **+1.65%** | −0.34% | 49% | **+$118,990** |

**Aggregate over 185 gate-blocked cells:** +1.55% mean net return,
50.8% hit rate (94W / 91L), **+$286,644 total P&L** if all had been longed.

**Aggregate over 10 actual trades:** −2.06% mean net return, 50% hit rate,
**−$20,623 total P&L**.

The gate is anti-predictive: cells the gate passes lose money on average;
cells the gate blocks make money on average.

## Caveats before declaring "invert the gate"

1. **Mean ≫ median** for in_line (+1.48% mean vs +0.36% median) and
   modest_miss (+1.65% vs −0.34% median). Skewed distribution — a few
   big winners pull the mean. Real portfolio implementation may not
   capture all winners due to capital constraints.
2. **n=15 vs n=113** — sample-size imbalance. The 15 modest_beat cells
   have wide CI. The "−0.91% mean" could easily be a small-sample fluke.
3. **Capital constraints**: 185 longs across 5 years would require
   substantial concurrent positions; the 8-position cap would force
   selection — and the selection rule itself becomes the new question.
4. **No bootstrap test of statistical robustness** yet.
5. **The 10 actual trades' P&L is heavily distorted** by the 2 COVID-2019Q4
   trades (-$34K combined) — these were modest_beat cells that lost
   purely because of regime mismatch, not because the gate was wrong
   on those specific signals.

## Hypotheses for why the gate would be inverted

1. **Market efficiency / pre-pricing:** when our SAR signal predicts a
   modest_beat, the market may have *already priced it* by T-14
   (other quant funds running similar signals). The trade enters with
   no edge left. When the SAR signal is in_line / modest_miss, no one
   else is using it, so the actual surprise (which can be positive
   even when SAR isn't) is unanticipated.
2. **Mean reversion at the firm level:** cells with the strongest SAR
   signals correspond to operators in their *peak drilling quarter* —
   the next quarter mean-reverts negatively.
3. **Sampling artifact:** the 5-pad random sample over-represents
   defensively-permitted operators (filing permits before downturns),
   so "active" sampled pads can correlate with *operationally
   stressed* firms.
4. **Plain noise:** with n=15 modest_beat cells, the mean−return
   estimate has very wide CI; the gate may not actually be inverted,
   just look that way in this sample.

## Implications for the paper

This is a paper-level finding, not a switch to flip. Three honest paths:

1. **Section 12 / Limitations addition:** report that under the
   chosen Agent 3 gate, modest_beat cells averaged negative return
   over 2019-2024 while gate-blocked cells averaged positive return.
   Frame as "the system as designed has anti-predictive Agent 3
   classifications in this sample; the gate calibration may be
   incorrect or the underlying SAR signal may suffer from market
   pre-pricing."
2. **New ablation row:** add an "ungated" variant where every cell
   that runs Agents 4+5 is allowed to fire (subject only to the
   Bull/Bear/Arbiter consensus). Compare hit rate, mean return,
   and Sharpe vs the gated variant.
3. **Anti-gate variant** (more speculative): trade `in_line` and
   `modest_miss` long, skip `modest_beat`. Report as a
   counterfactual that would have produced positive return on this
   sample — but caveat heavily on the small-sample and skewness
   risks. This is NOT a recommended live strategy.

## Codex's recommended follow-up

Run Bull/Bear/Arbiter on the 185 gate-blocked cells (currently they
are skipped). Question: does the LLM layer have *discriminatory
power* within the gate-blocked population, or does it wash out to
coin-flip on more trades?

If LLM debate ranks winners above losers within suppressed cells,
the multi-agent thesis (combining signals) is supported and the
gate should be relaxed.

If LLM debate just adds more random trades, the multi-agent
architecture isn't the source of the suppressed-cell positive
return — there's just an unexploited signal in the underlying data
that needs a different filter.

Estimated cost of follow-up: ~5-8 hours of LLM time (185 cells ×
3-4 LLM calls each at 12s throttle).

## Closing

This audit is a clear example of **multi-agent system design failing
in a way that's only visible from outside the gate**. The system was
graded on directional rightness, not profitability — but a gate that
actively flips positive-return signals into rejected cells is a
meaningful negative finding worth honest reporting.

This belongs in the paper as a research-grade limitation, not as a
silently-fixed parameter.
