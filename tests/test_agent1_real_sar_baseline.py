import json
from datetime import date

from fin580.agents.agent1_gis import _cached_prior_sar_active_counts


def _write_cache(path, *, active, n_pads=25):
    path.write_text(json.dumps({
        "n_pads_sampled": n_pads,
        "n_newly_active": active,
        "n_continuously_active": 0,
        "n_idle": n_pads - active,
    }))


def test_real_sar_trailing_lookup_uses_n25_and_actual_cache_date(tmp_path):
    _write_cache(
        tmp_path / "OVV_2021-03-31_2021-04-15_n25.json",
        active=19,
    )
    _write_cache(
        tmp_path / "OVV_2020-12-31_2021-02-03_n25.json",
        active=0,
    )
    # Old 5-pad cache exists but should not be used for a 25-pad run.
    _write_cache(
        tmp_path / "OVV_2021-03-31_2021-04-15_n5.json",
        active=5,
        n_pads=5,
    )

    counts = _cached_prior_sar_active_counts(
        ticker="OVV",
        fiscal_quarter_end=date(2021, 6, 30),
        decision_date_T=date(2021, 7, 13),
        current_n_pads=25,
        sar_firm_cache=tmp_path,
    )

    assert counts == [19.0, 0.0]


def test_real_sar_trailing_lookup_respects_point_in_time_cutoff(tmp_path):
    _write_cache(
        tmp_path / "OVV_2021-03-31_2021-04-15_n25.json",
        active=19,
    )
    _write_cache(
        tmp_path / "OVV_2021-03-31_2021-08-01_n25.json",
        active=25,
    )

    counts = _cached_prior_sar_active_counts(
        ticker="OVV",
        fiscal_quarter_end=date(2021, 6, 30),
        decision_date_T=date(2021, 7, 13),
        current_n_pads=25,
        sar_firm_cache=tmp_path,
    )

    assert counts == [19.0]
