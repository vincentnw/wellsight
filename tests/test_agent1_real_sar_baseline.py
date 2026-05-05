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


def test_real_sar_run_passes_env_pads_per_op_at_call_time(monkeypatch):
    """If FIN580_SAR_MODE=real_sentinel1 and FIN580_SAR_PADS_PER_OP=25 are set
    at runner start, Agent 1 must call aggregate_firm_quarter with
    pads_per_op=25 even when sentinel1_firm_quarter was imported earlier with
    a different (or missing) env var. Guards against the import-time capture
    failure mode where PADS_PER_OP_DEFAULT silently stays 5 and Agent 1's
    trailing-cache helper would then look at _n5 caches."""
    from fin580.agents import agent1_gis
    from fin580.data import sentinel1_firm_quarter as sfq

    captured = {}

    def fake_aggregate(*, ticker, fiscal_quarter_end, decision_date_T, pads_per_op):
        captured["pads_per_op"] = pads_per_op
        return sfq.FirmQuarterSarSignal(
            ticker=ticker,
            fiscal_quarter_end=fiscal_quarter_end,
            decision_date_T=decision_date_T,
            n_pads_sampled=pads_per_op,
            n_newly_active=0,
            n_continuously_active=0,
            n_idle=pads_per_op,
            n_observations_total=0,
            pad_classifications=[],
        )

    monkeypatch.setattr(sfq, "aggregate_firm_quarter", fake_aggregate)
    monkeypatch.setenv("FIN580_SAR_MODE", "real_sentinel1")
    monkeypatch.setenv("FIN580_SAR_PADS_PER_OP", "25")

    out = agent1_gis.run(
        ticker="OVV",
        fiscal_quarter_end=date(2021, 6, 30),
        decision_date_T=date(2021, 7, 13),
    )

    assert captured["pads_per_op"] == 25
    assert out.ticker == "OVV"


def test_real_sar_run_falls_back_to_five_when_env_unset(monkeypatch):
    """Without FIN580_SAR_PADS_PER_OP set, Agent 1 calls aggregate_firm_quarter
    with the legacy default of 5 — preserving prior behavior so older runners
    that never set the env var keep working."""
    from fin580.agents import agent1_gis
    from fin580.data import sentinel1_firm_quarter as sfq

    captured = {}

    def fake_aggregate(*, ticker, fiscal_quarter_end, decision_date_T, pads_per_op):
        captured["pads_per_op"] = pads_per_op
        return sfq.FirmQuarterSarSignal(
            ticker=ticker, fiscal_quarter_end=fiscal_quarter_end,
            decision_date_T=decision_date_T,
            n_pads_sampled=pads_per_op, n_newly_active=0,
            n_continuously_active=0, n_idle=pads_per_op,
            n_observations_total=0, pad_classifications=[],
        )

    monkeypatch.setattr(sfq, "aggregate_firm_quarter", fake_aggregate)
    monkeypatch.setenv("FIN580_SAR_MODE", "real_sentinel1")
    monkeypatch.delenv("FIN580_SAR_PADS_PER_OP", raising=False)

    agent1_gis.run(
        ticker="OVV",
        fiscal_quarter_end=date(2021, 6, 30),
        decision_date_T=date(2021, 7, 13),
    )

    assert captured["pads_per_op"] == 5
