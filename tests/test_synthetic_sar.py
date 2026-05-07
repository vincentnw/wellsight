"""Smoke tests for the synthetic SAR generator (spec Section 3, plan Task 7)."""

import random
from datetime import date

from fin580.data.synthetic_sar import (
    CONFUSION_MATRICES,
    _sample_observation,
    _truth_for_pad_quarter,
)
from fin580.data.trc_permits import Permit


def test_target_matrix_recovers_calibration():
    """Run target matrix on 1000 synthetic ground-truth samples; recovered
    recall should be within ±8% of calibration target (0.78)."""
    rng = random.Random(0)
    truth = []
    for _ in range(1000):
        truth.append(
            rng.choices(
                ["newly_active", "continuously_active", "idle"],
                weights=[0.2, 0.3, 0.5],
            )[0]
        )
    cm = CONFUSION_MATRICES["target"]
    classified = [_sample_observation(t, cm, rng) for t in truth]
    tp = sum(
        1 for t, c in zip(truth, classified)
        if t == "newly_active" and c == "newly_active"
    )
    fn = sum(
        1 for t, c in zip(truth, classified)
        if t == "newly_active" and c != "newly_active"
    )
    n_true_active = sum(1 for t in truth if t == "newly_active")
    if n_true_active > 0:
        recall = tp / (tp + fn)
        assert 0.70 <= recall <= 0.86, f"Recall {recall} outside ±8% of target 0.78"


def test_q1_truth_mapping_uses_same_year_q1_start():
    """Codex Round-5 fix: Q1 quarter-start must be Jan 1 of the SAME year,
    not prior year."""
    spud_in_q1 = date(2024, 2, 15)
    permit_d = date(2024, 1, 5)
    p = Permit(
        pad_id="P", operator_at_permit="X", operator_normalized="FANG",
        state="TX", county="Midland", latitude=31.9, longitude=-102.0,
        permit_filing_date=permit_d, spud_filing_date=spud_in_q1,
        completion_filing_date=None, api_number="",
    )
    truth = _truth_for_pad_quarter(p, date(2024, 3, 31))
    assert truth == "newly_active", f"Expected newly_active, got {truth}"


def test_old_completion_no_longer_continuously_active_forever():
    """Codex Round-5 fix: completions older than 8 quarters resolve to idle."""
    very_old_completion = date(2019, 6, 30)
    p = Permit(
        pad_id="P", operator_at_permit="X", operator_normalized="FANG",
        state="TX", county="Midland", latitude=31.9, longitude=-102.0,
        permit_filing_date=date(2018, 1, 1),
        spud_filing_date=None,
        completion_filing_date=very_old_completion,
        api_number="",
    )
    # Q3 2024 is far more than 8 quarters after 2019Q2 completion
    truth = _truth_for_pad_quarter(p, date(2024, 9, 30))
    assert truth == "idle", f"Expected idle for stale completion, got {truth}"


def test_recent_completion_is_continuously_active():
    completion = date(2024, 1, 15)
    p = Permit(
        pad_id="P", operator_at_permit="X", operator_normalized="FANG",
        state="TX", county="Midland", latitude=31.9, longitude=-102.0,
        permit_filing_date=date(2023, 6, 1),
        spud_filing_date=date(2023, 8, 1),
        completion_filing_date=completion,
        api_number="",
    )
    truth = _truth_for_pad_quarter(p, date(2024, 9, 30))
    assert truth == "continuously_active", f"Expected continuously_active, got {truth}"
