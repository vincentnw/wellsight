# 8. Portfolio Construction and Risk Management

Portfolio rules are deliberately rigid to prevent the multi-agent system from drifting into ad-hoc allocation. Sizing is a deterministic conviction-to-size lookup, so the Investment Board's only discretion is *which* trades to take, not *how much* capital to allocate.

**Sizing.** The Arbiter assigns each long candidate one of four conviction tiers — `high`, `medium`, `low`, `none`. The lookup is fixed at `high → 15%`, `medium → 10%`, `low → 5%`, `none → 0%`. The 15% per-name cap binds even when conviction would otherwise warrant more, preventing single-name concentration regardless of LLM reasoning quality.

**Concurrency cap (documented, non-binding in this sample).** The runner manifest records `max_names: 8` as a documented portfolio-construction parameter. In the empirical 2019–2024 sample the cap never binds — the maximum simultaneous longs in any single quarter is 2021-Q3 with 8 trades (every then-eligible firm), exactly at the cap. The inference pipeline does not enforce the cap; the headline P&L in §9 counts every long the system generated. We disclose this gap in §12.6 rather than enforce the cap retroactively.

**Cash sleeve.** Unallocated capital is held in BIL (SPDR Bloomberg 1–3 Month T-Bill ETF) rather than zero-yield cash. BIL is the system's only non-WRDS price input; it keeps the cash sleeve tradable, free, and total-return-comparable to equity legs.

**Trade timing.** All entries open at the close on T-14 (two weeks before earnings) and close on the second trading day after the earnings report (T+2). The holding window is short enough that we treat WTI level as approximately constant and long enough to capture the earnings-surprise reaction.

**Costs.** A flat 30 bps round-trip cost is applied to entry value. We do not separately model bid-ask spread, market impact, borrow, or earnings-event slippage; the long-only restriction makes these simplifications defensible.

**Risk attribution.** Because sizing is deterministic given conviction tier, realised return decomposes cleanly across the agent stack: name selection is the LLM-driven step (Investment Board plus upstream agents), magnitude is the deterministic step. The attribution analysis in §11 leverages this separation.
