"""5-call advisory stability check per agent (spec Section 8.3).

Per Codex weakness #6 + Round-5 cleanup #G: this is advisory, not gating.
Provider-side nondeterminism is real; failures are logged but do not block
the backtest run."""

from __future__ import annotations

from typing import Callable


def check_field_stability(
    call_fn: Callable,
    fixed_input: dict,
    fields: list[str],
    n: int = 5,
) -> dict:
    """Fire `call_fn(fixed_input)` n times. Return per-field stability stats.

    A field is 'stable' if all n responses agree on its value (set equality
    for lists). Result is purely advisory."""
    responses = [call_fn(fixed_input) for _ in range(n)]
    stats: dict[str, dict] = {}
    for f in fields:
        values = [r.get(f) for r in responses]
        # Convert lists to sorted tuples for comparison
        normalized = [
            tuple(sorted(v)) if isinstance(v, list) else v for v in values
        ]
        stats[f] = {
            "values": values,
            "all_match": len(set(normalized)) == 1,
        }
    return {
        "n_calls": n,
        "fields": stats,
        "advisory_passed": all(s["all_match"] for s in stats.values()),
    }
