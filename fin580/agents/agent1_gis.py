"""Agent 1 — GIS Detection. No LLM. Wraps synthetic SAR + relative-activity
normalization (spec Section 4.3, Section 3.4, Section 3.6)."""

from __future__ import annotations

from datetime import date, timedelta
import json
import re

from fin580.agents.schemas import Agent1Out, PadClassification
from fin580.data.synthetic_sar import (
    aggregate_to_firm_quarter,
    classify_pads,
)
from fin580.data.trc_permits import load_permit_dump


_SAR_CACHE_RE = re.compile(
    r"^(?P<ticker>[^_]+)_(?P<fpe>\d{4}-\d{2}-\d{2})_"
    r"(?P<T>\d{4}-\d{2}-\d{2})_n(?P<n>\d+)\.json$"
)


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


def _cached_prior_sar_active_counts(
    *,
    ticker: str,
    fiscal_quarter_end: date,
    decision_date_T: date,
    current_n_pads: int,
    sar_firm_cache,
) -> list[float]:
    """Read cached prior-quarter SAR active counts for real-Sentinel mode.

    Firm-quarter aggregate cache names include the decision date T. That date is
    not necessarily current_T - 91*k, so exact filename construction can miss a
    valid prior-quarter cache. Match by ticker, fiscal quarter end, and pad count
    instead, keeping only cache files whose own T is point-in-time before the
    current decision date.
    """
    out: list[float] = []
    for k in range(1, 5):
        prior_q_end = _prior_quarter_end(fiscal_quarter_end, k=k)
        matches = []
        for cache_path in sar_firm_cache.glob(
            f"{ticker}_{prior_q_end.isoformat()}_*_n{current_n_pads}.json"
        ):
            m = _SAR_CACHE_RE.match(cache_path.name)
            if not m:
                continue
            cache_T = date.fromisoformat(m.group("T"))
            if cache_T <= decision_date_T:
                matches.append((cache_T, cache_path))
        if not matches:
            continue
        _, cache_path = max(matches, key=lambda item: item[0])
        d = json.loads(cache_path.read_text())
        n_pads = int(d.get("n_pads_sampled", 0) or 0)
        if n_pads <= 0:
            continue
        active = float(d.get("n_newly_active", 0) + d.get("n_continuously_active", 0))
        out.append(active)
    return out


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
        # Read FIN580_SAR_PADS_PER_OP at call time, not import time. The default
        # arg `pads_per_op=PADS_PER_OP_DEFAULT` in aggregate_firm_quarter
        # captures whatever the env var was when sentinel1_firm_quarter was
        # imported, which can fall back to 5 if the import happened before the
        # runner set FIN580_SAR_PADS_PER_OP=25. Reading here makes the call
        # explicit and immune to import order.
        pads_per_op = int(os.environ.get("FIN580_SAR_PADS_PER_OP", 5))
        sig = aggregate_firm_quarter(
            ticker=ticker,
            fiscal_quarter_end=fiscal_quarter_end,
            decision_date_T=decision_date_T,
            pads_per_op=pads_per_op,
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
        from fin580.data.sentinel1_firm_quarter import SAR_FIRM_CACHE
        trailing_actives = _cached_prior_sar_active_counts(
            ticker=ticker,
            fiscal_quarter_end=fiscal_quarter_end,
            decision_date_T=decision_date_T,
            current_n_pads=total,
            sar_firm_cache=SAR_FIRM_CACHE,
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
