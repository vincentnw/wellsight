# Signal-Confidence Score v0 — Pre-Registration

**Status:** diagnostic only. Scope explicitly excludes any effect on H1, trade
eligibility, sizing, or the deterministic Agent-3 gate. Score is annotation
on per-cell diagnostics; it does not enter any pre-registered test.

**Implementation:** `fin580/inference/signal_confidence.py`

**Formula (frozen at v2.3 commit):**

Composite score = sum of five 0-20 sub-scores → 0-100.

| Sub-score | Input field | Bin edges (≤) | Scores |
|---|---|---|---|
| `sc_activity_strength` | `share_active` | 0.0, 0.20, 0.40, 0.60, 0.80 | 0, 4, 8, 12, 16, 20 |
| `sc_newness` | `n_newly_active / absolute_active` | 0.0, 0.20, 0.40, 0.60, 0.80 | 0, 4, 8, 12, 16, 20 |
| `sc_qoq_delta` | `relative_activity_delta` | -0.5, 0.0, 0.5, 1.0, 1.5 | 0, 4, 8, 12, 16, 20 |
| `sc_dispersion` | `\|consensus_dispersion\| / \|consensus_median\|` | 0.02, 0.05, 0.10, 0.20, 0.40 | 20, 16, 12, 8, 4, 0 (inverted) |
| `sc_analyst_breadth` | `n_analysts_at_T_minus_14` | 3, 6, 10, 15, 20 | 0, 4, 8, 12, 16, 20 |

Missing inputs fall back to a neutral midpoint score (10) for that sub-score —
specifically, the midpoint of the sub-score range `(min(scores)+max(scores))/2`,
which is 10 for all five sub-scores above.

**Tier mapping:** `score >= 70 → high`, `40 <= score < 70 → medium`, `< 40 → low`.

**v0 finding (2019-2024 Strategy 1):** all 10 actual long trades cluster in
the medium tier (48-64); none reach high. Eight cells score `high` but
produce zero long trades — categorized as:

| Count | Divergence class | Reason for no_trade |
|---|---|---|
| 4 | `in_line` | Agent 3 short-circuit (consensus already pricing the activity in) |
| 2 (FANG, SM 2019-Q2) | `modest_beat` | Agent 5 Bear flagged GDELT info-leakage (75 / 36 matching articles) |
| 2 (MTDR 2019-Q3, 2021-Q3) | `modest_beat` | Agent 5 Bear vetoed: "modest_beat + only medium Agent-3 confidence is insufficient conviction" |

So the high-confidence no-trade pool is roughly half "consensus already
priced in" and half "downstream agents (4 or 5) found a reason to veto a
modest_beat." The score itself is purely descriptive of input quality and
intentionally does not penalize for either of these downstream reasons.

**Components explicitly NOT in this score:**

- WTI / oil-price momentum (lives in v2.4 as a separate portfolio-construction veto)
- XLE / sector trend (same reason)
- Stock-return outcome or any post-decision information (would be look-ahead)
- Any LLM-generated rating (the Bull/Bear/Arbiter stack already produces qualitative ratings; this score is meant to be deterministic)

**Pre-registration discipline:** the formula is frozen at the commit that
introduces this file. Any change to bin edges, weights, or component set
requires a new commit, a new version (`v1`, `v2`, …), and explicit disclosure
in the paper that the score has been re-tuned. Diagnostic-only status holds
across all versions unless the project explicitly promotes the score to a
gating or sizing input — which would require a separate pre-registration
including a held-out validation window.
