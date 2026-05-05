"""H2 secondary test: Strategy 1 hit rate exceeds Strategy 3 (analyst-revision
follower, our pure-consensus baseline) by ≥3 percentage points (one-sided,
quarter-block bootstrap, 5% level).

Pre-registered in spec Section 4 / paper §4.1 / DL #38.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from fin580.inference.pnl import compute_pnl_for_strategy

OUT_DIR = Path(__file__).resolve().parents[2] / "runs" / "inference"

THRESHOLD_PCT = 0.03  # 3 percentage points
N_ITER = 1000
SEED = 0


def quarter_block_diff(
    a: pd.DataFrame,
    b: pd.DataFrame,
    n_iter: int = N_ITER,
    seed: int = SEED,
) -> dict:
    """Resample fiscal quarters with replacement; compute hit_rate(a) - hit_rate(b)
    on the resampled trades (keeping each strategy's actual cells per quarter).

    Codex Audit Round-2 fix: previously reported p = (samples <= threshold).mean()
    which is the lower-tail percentile of the bootstrap distribution of the
    OBSERVED diff, not a true null test against H0: diff <= threshold. The fix
    null-centers the bootstrap diffs so the test is against H0 explicitly.
    """
    rng = np.random.default_rng(seed)
    quarters_a = a["fiscal_quarter_end"].unique()
    quarters_b = b["fiscal_quarter_end"].unique()
    quarters = np.array(sorted(set(quarters_a) | set(quarters_b)))
    n_q = len(quarters)
    obs_a = (a["net_return_pct"] > 0).mean()
    obs_b = (b["net_return_pct"] > 0).mean()
    obs_diff = obs_a - obs_b

    samples = []
    for _ in range(n_iter):
        chosen = rng.choice(quarters, size=n_q, replace=True)
        sa = pd.concat([a[a["fiscal_quarter_end"] == q] for q in chosen])
        sb = pd.concat([b[b["fiscal_quarter_end"] == q] for q in chosen])
        if len(sa) == 0 or len(sb) == 0:
            continue
        ha = (sa["net_return_pct"] > 0).mean()
        hb = (sb["net_return_pct"] > 0).mean()
        samples.append(ha - hb)
    samples = np.array(samples)
    # Null-center under H0: diff = THRESHOLD_PCT, then test P(centered >= obs_diff).
    null_centered = samples - samples.mean() + THRESHOLD_PCT
    p_one_sided = float((null_centered >= obs_diff).mean())
    return {
        "n_iter": int(len(samples)),
        "obs_hit_rate_strategy1": float(obs_a),
        "obs_hit_rate_strategy3": float(obs_b),
        "obs_diff": float(obs_diff),
        "threshold_pct": THRESHOLD_PCT,
        "p_one_sided_diff_le_threshold": p_one_sided,
        "reject_null_at_5pct": bool(p_one_sided < 0.05),
        "ci_95_diff_low": float(np.percentile(samples, 2.5)),
        "ci_95_diff_high": float(np.percentile(samples, 97.5)),
    }


def main() -> None:
    s1 = compute_pnl_for_strategy(1)
    s3 = compute_pnl_for_strategy(3)
    print(f"Strategy 1: n={len(s1)} trades, obs hit_rate={(s1.net_return_pct>0).mean():.4f}")
    print(f"Strategy 3: n={len(s3)} trades, obs hit_rate={(s3.net_return_pct>0).mean():.4f}")
    result = quarter_block_diff(s1, s3)
    print()
    print("H2 quarter-block bootstrap (Strategy 1 hit rate − Strategy 3 hit rate ≥ 3pp):")
    for k, v in result.items():
        print(f"  {k}: {v}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "h2_test.json", "w") as f:
        json.dump(result, f, indent=2)
    print()
    print(f"Wrote {OUT_DIR / 'h2_test.json'}")


if __name__ == "__main__":
    main()
