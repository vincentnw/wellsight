"""Firm-clustered + quarter-block bootstrap for hit-rate inference (spec
Section 7.1, DL #38: pre-registered primary test)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def firm_clustered_bootstrap(
    trades: pd.DataFrame,
    n_iter: int = 1000,
    metric: str = "hit_rate",
    seed: int = 0,
) -> dict:
    """Resample firms with replacement; keep all of each firm's trades together.
    Returns mean + 95% percentile CI for the chosen metric."""
    if len(trades) == 0:
        return {"mean": None, "ci_low": None, "ci_high": None, "n_iter": 0}
    rng = np.random.default_rng(seed)
    firms = trades["ticker"].unique()
    n_firms = len(firms)
    samples = []
    for _ in range(n_iter):
        chosen = rng.choice(firms, size=n_firms, replace=True)
        sample_df = pd.concat([trades[trades["ticker"] == f] for f in chosen])
        if len(sample_df) == 0:
            continue
        if metric == "hit_rate":
            samples.append((sample_df["net_return_pct"] > 0).mean())
        elif metric == "mean_return":
            samples.append(sample_df["net_return_pct"].mean())
        elif metric == "sharpe":
            r = sample_df["net_return_pct"]
            samples.append(r.mean() / r.std() if r.std() > 0 else 0)
    samples = np.array(samples)
    return {
        "mean": float(samples.mean()),
        "ci_low": float(np.percentile(samples, 2.5)),
        "ci_high": float(np.percentile(samples, 97.5)),
        "n_iter": int(len(samples)),
    }


def quarter_block_bootstrap(
    trades: pd.DataFrame,
    n_iter: int = 1000,
    metric: str = "hit_rate",
    seed: int = 0,
) -> dict:
    """Resample quarters with replacement; keep all of each quarter's trades
    together. Sensitivity per spec Section 7.1."""
    if len(trades) == 0:
        return {"mean": None, "ci_low": None, "ci_high": None, "n_iter": 0}
    rng = np.random.default_rng(seed)
    quarters = trades["fiscal_quarter_end"].unique()
    n_q = len(quarters)
    samples = []
    for _ in range(n_iter):
        chosen = rng.choice(quarters, size=n_q, replace=True)
        sample_df = pd.concat([trades[trades["fiscal_quarter_end"] == q] for q in chosen])
        if len(sample_df) == 0:
            continue
        if metric == "hit_rate":
            samples.append((sample_df["net_return_pct"] > 0).mean())
        elif metric == "mean_return":
            samples.append(sample_df["net_return_pct"].mean())
        elif metric == "sharpe":
            r = sample_df["net_return_pct"]
            samples.append(r.mean() / r.std() if r.std() > 0 else 0)
    samples = np.array(samples)
    return {
        "mean": float(samples.mean()),
        "ci_low": float(np.percentile(samples, 2.5)),
        "ci_high": float(np.percentile(samples, 97.5)),
        "n_iter": int(len(samples)),
    }


def primary_test(trades: pd.DataFrame, n_iter: int = 1000, seed: int = 0) -> dict:
    """Pre-registered primary test (DL #38): is hit rate > 50% under
    firm-clustered bootstrap at the 5% level (one-sided)?

    Codex Audit Round-2 fix: the previous implementation reported the
    percentile of the observed hit-rate distribution itself (P(resample ≤ 0.5))
    rather than a properly null-centered test. The corrected implementation
    centers the resamples under H0 = 50% by subtracting the observed shift,
    so the reported p-value is the bootstrap-equivalent of a null-centered
    one-sided test.
    """
    if len(trades) == 0:
        return {"hit_rate_obs": None, "p_value_one_sided": None,
                "reject_50": False, "ci_95": None}
    rng = np.random.default_rng(seed)
    firms = trades["ticker"].unique()
    obs_hit_rate = (trades["net_return_pct"] > 0).mean()

    samples = []
    for _ in range(n_iter):
        chosen = rng.choice(firms, size=len(firms), replace=True)
        sample = pd.concat([trades[trades["ticker"] == f] for f in chosen])
        if len(sample) == 0:
            continue
        samples.append((sample["net_return_pct"] > 0).mean())
    samples = np.array(samples)
    # Null-centered: shift samples so their mean is 50% (the H0), then test
    # P(centered statistic <= 0.5 - obs_hit_rate). Equivalently, p-value is
    # P(samples - mean(samples) + 0.5 <= 0.5) = P(samples <= mean(samples)).
    null_centered = samples - samples.mean() + 0.5
    p_value = (null_centered >= obs_hit_rate).mean()
    # Two-sided exact binomial cross-check
    from scipy.stats import binomtest
    n = len(trades)
    k = int((trades["net_return_pct"] > 0).sum())
    binom = binomtest(k, n, p=0.5, alternative="greater")
    return {
        "hit_rate_obs": float(obs_hit_rate),
        "p_value_one_sided": float(p_value),
        "p_value_exact_binomial": float(binom.pvalue),
        "reject_50": bool(p_value < 0.05),
        "ci_95": (float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))),
        "n_iter": int(len(samples)),
    }
