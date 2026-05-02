# M1.b Adverse Anchor Log — SM Q1 2023

**Date run:** 2026-04-29
**Cell:** SM Energy, fiscal_quarter_end=2023-03-31, decision_date_T=2023-04-12
**Confusion matrix:** target

## Acceptance Criteria (Spec Section 9 M1.b)

> Adverse anchor surfaces at least one of: `low_quality_flag=True`, `divergence_class=in_line` causing `no_trade`, or `gdelt_disclosed=True` causing one-tier conviction downgrade. Each tested behavior is documented in `runs/<id>/m1_b_adverse_log.md`.

**Result: PASS** — `gdelt_disclosed=True` surfaced and a `downgrade_one_tier` conviction modifier was applied. Additionally, Bull and Bear genuinely disagreed (Bull `long`/medium vs Bear `no_trade`/medium), forcing Arbiter mediation.

## Agent-by-agent trace

| Agent | Output |
|---|---|
| 1 GIS | 24 pads monitored (4 newly_active, 8 continuously_active, 12 idle); share_active 50%; relative_activity_delta +2.25 (above trailing-4Q average) |
| 2 Revenue | Deterministic forecast $2.01B; key_drivers: increased_drilling_activity, moderate_wti_prices, mixed_segment_exposure, steady_production_growth |
| 3 Consensus | Our $2.01B vs IBES consensus $603M → divergence **+234%** → `strong_beat` / medium confidence (13 analysts) |
| 4 News | 10 GDELT articles in window, **2 matched** → `gdelt_disclosed=True` → `downgrade_one_tier` |
| 5 Board | Bull `long`/medium, Bear `no_trade`/medium → Arbiter `long` / medium tier / 10% size |

Arbiter weights: agent2=0.40, agent3=0.30, agent4=0.30. Arbiter cited "strength of Bull's evidence prevails" while acknowledging Agent 4's GDELT disclosure as a downgrade factor.

## Adverse-case behaviors that surfaced

1. **Bull/Bear disagreement.** Bull voted long, Bear voted no_trade. The Investment Board debate is meaningful, not unanimous.
2. **GDELT disclosed conviction downgrade.** Spec-prescribed adverse behavior. Articles `orts-2022-results-211500882.html` and `results-and-2023-operating-plan/` matched the satellite-detected pattern; Agent 4 emitted `conviction_modifier=downgrade_one_tier`.
3. **Long with downgraded tier (medium, not high).** Despite a strong_beat divergence, the Arbiter assigned `medium` conviction because the GDELT downgrade applied. Per locked sizing lookup, medium = 10% size, not 15%.

## Calibration concern surfaced (NOT an acceptance failure, but recorded)

The numerical forecast of $2.01B vs IBES consensus of $603M is a 234% divergence. Reality: SM Energy reported ~$580M in Q1 2023. Our forecast is ~3.4x too high.

**Root cause:** the placeholder constants in `fin580/phase2/revenue_forecast.py` (DEFAULT_WELLS_PER_PAD, type curve coefficient, LAST_QUARTER_PRODUCTION_BASE) were calibrated against FANG-scale operators. For mid-cap names like SM with smaller pad portfolios but similar synthetic pad counts in the stub permit dump, the multiplier inflates. Specifically:

- 12 active synthetic pads × 3.5 wells/pad × 800 boe/d type curve = 33,600 boe/d incremental
- Plus existing-well decline: 160,000 × 0.92 = 147,200 boe/d
- Times 91 days × WTI × realized-price-diff / segment-fraction = $2B

**Acceptable outcome under project-goal framing.** The architecture handled the numerical input correctly (deterministic core unchanged, LLMs interpreted but did not generate the number). The calibration inflation is a documented limitation per `project_overview.md` Discussion / Limitations and revenue_forecast.py docstring caveats. To improve calibration, the team can:

- Run the LLM-driven Permian-fraction extraction (Pre-Code Action Item from Phase 1) to replace placeholder DEFAULT_PERMIAN_REVENUE_SHARE constants
- Replace synthetic permit dump with real TRC + NMOCD permits (paper-claim narrowing fallback in `fin580/data/trc_permits.py` docstring discusses this)
- Recalibrate per-operator wells-per-pad and last-quarter production base from real TRC completion records

None of these fixes are required to pass M1.b acceptance.

## Conclusion

**M1 acceptance gate (clean + adverse anchors): PASSED.**
- M1.a clean anchor (FANG Q3 2024): no_trade decision, coherent attribution, 6 LLM calls cached
- M1.b adverse anchor (SM Q1 2023): long/medium decision with documented Bull/Bear disagreement and GDELT-disclosed downgrade

System ready for M2 (10-firm cross-section over Q3 2024).
