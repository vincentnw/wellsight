# 8. Portfolio Construction and Risk Management

The portfolio rules are deliberately rigid to prevent the multi-agent system from drifting into ad-hoc allocation decisions. Position sizing follows a deterministic conviction-to-size lookup, so the Investment Board's only discretion is over which trades to take, not over how much capital to allocate.

**Sizing.** The Risk Arbiter assigns each long candidate one of four conviction tiers — `high`, `medium`, `low`, or `none`. The lookup table is fixed at `high → 15%`, `medium → 10%`, `low → 5%`, `none → 0%`. The 15% per-name cap is binding even when conviction would otherwise warrant a larger position; this prevents single-name concentration regardless of LLM reasoning quality.

**Concurrency cap.** A maximum of eight names may be held simultaneously out of the ten-name candidate universe. When more than eight names trigger entries in the same earnings season, the selection priority is conviction tier first (`high` before `medium` before `low`) and divergence magnitude as the tie-breaker within a tier. This rule is documented explicitly so the system does not silently drop candidates.

**Cash sleeve.** When fewer than four eligible names trigger long entries — which the M2 diagnostic suggests will be common under the consensus-anchored α = 0.10 regime — the unallocated capital is held in BIL (the SPDR Bloomberg 1–3 Month T-Bill ETF) rather than left as zero-yielding cash. BIL is the system's only non-WRDS-sourced price input; the choice keeps the cash sleeve tradable, free, and total-return-comparable to equity legs.

**Trade timing.** All long entries open at the closing price two weeks before the company's earnings announcement (`T-14`) and close two trading days after the earnings report (`T+2`). The holding period is therefore approximately two-to-three weeks per trade. This window is short enough that we treat WTI level as approximately constant and long enough to capture the earnings-surprise reaction.

**Costs.** A flat 30 basis points round-trip transaction cost is applied to the entry value of each trade. We do not separately model bid-ask spread, market impact, borrow costs, or earnings-event slippage; the long-only restriction makes these simplifications defensible.

**Risk attribution.** Because position sizing is deterministic given conviction tier, the portfolio's realized return decomposes cleanly across the agent stack. The selection of which names to hold is the LLM-driven step (Investment Board choice plus upstream agent inputs); the magnitude of each position is the deterministic step. The attribution analysis in Section 11 leverages this separation by reporting per-strategy results both for trade selection and for sizing aggregation.
