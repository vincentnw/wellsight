"""Agent 1 — GIS Detection. No LLM. Wraps synthetic SAR + relative-activity
normalization (spec Section 4.3, Section 3.4, Section 3.6)."""

from __future__ import annotations

from datetime import date, timedelta

from fin580.agents.schemas import Agent1Out, PadClassification
from fin580.data.synthetic_sar import (
    aggregate_to_firm_quarter,
    classify_pads,
)
from fin580.data.trc_permits import load_permit_dump


def _prior_quarter_end(q_end: date, k: int = 1) -> date:
    """k quarters back from q_end."""
    q_idx = {3: 1, 6: 2, 9: 3, 12: 4}[q_end.month]
    y = q_end.year
    q_idx -= k
    while q_idx <= 0:
        q_idx += 4
        y -= 1
    m_back = {1: 3, 2: 6, 3: 9, 4: 12}[q_idx]
    d_back = {3: 31, 6: 30, 9: 30, 12: 31}[m_back]
    return date(y, m_back, d_back)


def _trailing_4_quarter_active_avg(
    *,
    ticker: str,
    fiscal_quarter_end: date,
    permits: list,
    decision_date_T: date,
    cm_label: str,
) -> float:
    """For relative-activity normalization (spec Section 3.6).

    Uses point-in-time decision date adjusted backward by 91 days per quarter
    so each prior-quarter aggregate respects its own information set."""
    out: list[int] = []
    for k in range(1, 5):
        prior_q_end = _prior_quarter_end(fiscal_quarter_end, k=k)
        prior_T = decision_date_T - timedelta(days=91 * k)
        clas = classify_pads(
            permits=permits,
            operator=ticker,
            fiscal_quarter_end=prior_q_end,
            decision_date_T=prior_T,
            cm_label=cm_label,
        )
        agg = aggregate_to_firm_quarter(clas)
        out.append(agg["absolute_active"])
    return sum(out) / len(out) if out else 0.0


def run(
    *,
    ticker: str,
    fiscal_quarter_end: date,
    decision_date_T: date,
    cm_label: str = "target",
) -> Agent1Out:
    # M7 no-satellite ablation (DL #55 / Codex Round-7): when FIN580_ABLATION
    # env var is set to "no_satellite", Agent 1 emits all-idle classifications
    # so the satellite signal has no information content.
    import os
    if os.environ.get("FIN580_ABLATION") == "no_satellite":
        return Agent1Out(
            ticker=ticker, decision_date_T=decision_date_T,
            fiscal_quarter_end=fiscal_quarter_end,
            n_newly_active=0, n_continuously_active=0, n_idle=0,
            absolute_active=0, share_active=0.0,
            relative_activity_delta=0.0,
            pad_classifications=[],
        )

    # FIN580_SAR_MODE=real_sentinel1 — use real Sentinel-1 RTC backscatter
    # via Microsoft Planetary Computer (1-year demo window) instead of the
    # synthetic SAR generator.
    if os.environ.get("FIN580_SAR_MODE") == "real_sentinel1":
        from fin580.data.sentinel1_firm_quarter import aggregate_firm_quarter
        sig = aggregate_firm_quarter(
            ticker=ticker,
            fiscal_quarter_end=fiscal_quarter_end,
            decision_date_T=decision_date_T,
        )
        n_active = sig.n_newly_active + sig.n_continuously_active
        total = max(1, sig.n_pads_sampled)
        share_active = n_active / total

        # Trailing baseline for relative_activity_delta: check cached prior
        # 4 quarter SAR aggregates only (no fresh fetches — fetching trailing
        # quarters at scale is the project's compute bottleneck). If no cache
        # is available, use a fixed expected baseline of 30% of pads sampled
        # (`trailing_avg = 0.3 * total`) — anchored to long-run Permian rig-
        # utilisation literature: roughly 30% of pads are continuously active
        # in any given quarter post-2020 (lower than the 40% naive estimate
        # because most operators rotate equipment across pads, so any single
        # pad is active for only a fraction of the year). The 0.3 coefficient
        # is an ex-ante calibration parameter, not in-sample-tuned. Threshold
        # sensitivity is discussed in paper §11.5 / §12.2.
        import json
        from fin580.data.sentinel1_firm_quarter import SAR_FIRM_CACHE
        trailing_actives: list[int] = []
        for k in range(1, 5):
            prior_q_end = _prior_quarter_end(fiscal_quarter_end, k=k)
            prior_T = decision_date_T - timedelta(days=91 * k)
            cache_key = (
                f"{ticker}_{prior_q_end.isoformat()}_{prior_T.isoformat()}_n5.json"
            )
            cache_path = SAR_FIRM_CACHE / cache_key
            if cache_path.exists():
                d = json.loads(cache_path.read_text())
                if d.get("n_pads_sampled", 0) > 0:
                    trailing_actives.append(
                        d.get("n_newly_active", 0) + d.get("n_continuously_active", 0)
                    )
        if trailing_actives:
            trailing_avg = sum(trailing_actives) / len(trailing_actives)
        else:
            trailing_avg = 0.3 * total
        relative_delta = float(n_active) - trailing_avg
        pad_class_models = [
            PadClassification(pad_id=pc["pad_id"], state=pc["classification"])
            for pc in sig.pad_classifications
        ]
        return Agent1Out(
            ticker=ticker,
            decision_date_T=decision_date_T,
            fiscal_quarter_end=fiscal_quarter_end,
            n_newly_active=sig.n_newly_active,
            n_continuously_active=sig.n_continuously_active,
            n_idle=sig.n_idle,
            absolute_active=n_active,
            share_active=share_active,
            relative_activity_delta=relative_delta,
            pad_classifications=pad_class_models,
        )
    permits = load_permit_dump()
    classifications = classify_pads(
        permits=permits,
        operator=ticker,
        fiscal_quarter_end=fiscal_quarter_end,
        decision_date_T=decision_date_T,
        cm_label=cm_label,
    )
    agg = aggregate_to_firm_quarter(classifications)
    trailing_avg = _trailing_4_quarter_active_avg(
        ticker=ticker,
        fiscal_quarter_end=fiscal_quarter_end,
        permits=permits,
        decision_date_T=decision_date_T,
        cm_label=cm_label,
    )
    relative_delta = agg["absolute_active"] - trailing_avg

    pad_class_models = [
        PadClassification(pad_id=c.pad_id, state=c.observed_state)
        for c in classifications
    ]
    return Agent1Out(
        ticker=ticker,
        decision_date_T=decision_date_T,
        fiscal_quarter_end=fiscal_quarter_end,
        n_newly_active=agg["n_newly_active"],
        n_continuously_active=agg["n_continuously_active"],
        n_idle=agg["n_idle"],
        absolute_active=agg["absolute_active"],
        share_active=agg["share_active"],
        relative_activity_delta=float(relative_delta),
        pad_classifications=pad_class_models,
    )
