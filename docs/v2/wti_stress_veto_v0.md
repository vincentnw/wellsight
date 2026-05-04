# WTI Stress Veto v0 — Pre-Registration

**Status:** sensitivity only. This veto is a portfolio-construction / risk
control layer, not a satellite signal and not a revenue-forecasting input. It
does not change the headline H1 ledger, the deterministic Agent-3 gate, or the
canonical `strategy01_trades.csv`.

**Implementation:** `fin580/inference/wti_veto.py`

**Data source:** `phase1/output/eia_wti_weekly.csv`, EIA weekly WTI spot price
cache used elsewhere in the project.

**Rule (frozen at v2.4 commit):**

For each Strategy 1 long trade with entry date `T`, compute:

```
wti_4w_return(T) =
    latest_wti_price_on_or_before(T)
    / latest_wti_price_on_or_before(T - 28 calendar days)
    - 1
```

Block the long entry if:

```
wti_4w_return(T) <= -10.0%
```

Blocked trades are treated as `no_trade` in the sensitivity ledger. Position
size, transaction cost, and exit rule for non-blocked trades are unchanged.

**Motivation:** v2.2 diagnostics showed that several losing trades were not
failed revenue mechanisms; they were failed monetization during market stress.
The 2019-Q4 OXY and SM entries opened in February 2020 while WTI was already
falling sharply. This veto asks whether a simple, point-in-time oil-stress
guardrail would have prevented monetizing otherwise valid satellite signals in
an acute adverse regime.

**Explicit exclusions:**

- WTI is not included in the v2.3 signal-confidence score.
- WTI does not alter Agent 1, Agent 2, or Agent 3 outputs.
- WTI does not create new long trades.
- The threshold is not tuned after running v2.4; changing it requires a new
  versioned pre-registration document.

**Reporting:** v2.4 is reported as a Section 11 sensitivity:

- Baseline headline H1 remains Strategy 1 without the veto.
- `strategy01_trades_wti_veto.csv` reports the post-veto sensitivity ledger.
- `evidence_pack.json` includes `wti_veto_summary`.
