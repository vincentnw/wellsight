from datetime import date

from fin580.agents.schemas import (
    Agent1Out,
    Agent2Out,
    Agent3Out,
    Agent4Out,
    Agent5Out,
    BoardMemberOpinion,
    PadClassification,
)


def test_agent1_out_round_trip():
    pads = (
        [PadClassification(pad_id=f"N{i}", state="newly_active") for i in range(4)]
        + [PadClassification(pad_id=f"C{i}", state="continuously_active") for i in range(18)]
        + [PadClassification(pad_id=f"I{i}", state="idle") for i in range(8)]
    )
    obj = Agent1Out(
        ticker="FANG",
        decision_date_T=date(2024, 10, 17),
        fiscal_quarter_end=date(2024, 9, 30),
        n_newly_active=4,
        n_continuously_active=18,
        n_idle=8,
        absolute_active=22,
        share_active=22 / 30,
        relative_activity_delta=2.5,
        pad_classifications=pads,
    )
    j = obj.model_dump_json()
    obj2 = Agent1Out.model_validate_json(j)
    assert obj2.ticker == "FANG" and obj2.absolute_active == 22


def _valid_upstream():
    return {
        "agent2_decisive": True, "agent3_decisive": False,
        "agent4_decisive": False,
        "agent2_weight": 1.0, "agent3_weight": 0.0, "agent4_weight": 0.0,
    }


def _valid_member(role="bull"):
    return BoardMemberOpinion(
        role=role, direction="long", confidence="high",
        key_evidence=["e1"], counter_evidence=[], reasoning_short="r",
    )


def test_agent5_out_size_lookup_constraint():
    obj = Agent5Out(
        ticker="FANG", decision="long", conviction_tier="high", final_size_pct=0.15,
        bull_opinion=_valid_member("bull"),
        bear_opinion=_valid_member("bear"),
        arbiter_reasoning="r",
        upstream_agent_summary=_valid_upstream(),
    )
    assert obj.final_size_pct in {0.0, 0.05, 0.10, 0.15}


def test_agent5_out_rejects_nonlocked_size():
    try:
        Agent5Out(
            ticker="FANG", decision="long", conviction_tier="high",
            final_size_pct=0.07,
            bull_opinion=_valid_member("bull"),
            bear_opinion=_valid_member("bear"),
            arbiter_reasoning="r",
            upstream_agent_summary=_valid_upstream(),
        )
    except Exception:
        return
    raise AssertionError("Expected pydantic validation failure for size=0.07")


def test_agent5_out_rejects_size_inconsistent_with_conviction():
    # high tier should map to 0.15, not 0.05
    try:
        Agent5Out(
            ticker="FANG", decision="long", conviction_tier="high",
            final_size_pct=0.05,
            bull_opinion=_valid_member("bull"),
            bear_opinion=_valid_member("bear"),
            arbiter_reasoning="r",
            upstream_agent_summary=_valid_upstream(),
        )
    except Exception:
        return
    raise AssertionError("Expected validation failure for high tier with size=0.05")


def test_agent5_out_no_trade_must_be_zero_size():
    try:
        Agent5Out(
            ticker="FANG", decision="no_trade", conviction_tier="none",
            final_size_pct=0.05,
            bull_opinion=_valid_member("bull"),
            bear_opinion=_valid_member("bear"),
            arbiter_reasoning="r",
            upstream_agent_summary=_valid_upstream(),
        )
    except Exception:
        return
    raise AssertionError("Expected validation failure for no_trade with size>0")


def test_agent5_out_rejects_missing_upstream_keys():
    try:
        Agent5Out(
            ticker="FANG", decision="long", conviction_tier="high",
            final_size_pct=0.15,
            bull_opinion=_valid_member("bull"),
            bear_opinion=_valid_member("bear"),
            arbiter_reasoning="r",
            upstream_agent_summary={"agent2_decisive": True},  # missing fields
        )
    except Exception:
        return
    raise AssertionError("Expected validation failure for incomplete upstream summary")


def test_agent5_out_short_decision_accepted():
    obj = Agent5Out(
        ticker="OXY", decision="short", conviction_tier="high", final_size_pct=0.15,
        bull_opinion=BoardMemberOpinion(
            role="bull", direction="short", confidence="high",
            key_evidence=["e1"], counter_evidence=[], reasoning_short="r",
        ),
        bear_opinion=_valid_member("bear"),
        arbiter_reasoning="strong miss",
        upstream_agent_summary=_valid_upstream(),
    )
    assert obj.decision == "short"
    assert obj.final_size_pct == 0.15


def test_agent5_out_short_no_trade_zero_size():
    try:
        Agent5Out(
            ticker="OXY", decision="short", conviction_tier="none",
            final_size_pct=0.05,
            bull_opinion=_valid_member("bull"),
            bear_opinion=_valid_member("bear"),
            arbiter_reasoning="r",
            upstream_agent_summary=_valid_upstream(),
        )
    except Exception:
        return
    raise AssertionError("Expected validation failure for short with tier=none but size>0")


def test_agent1_out_rejects_count_mismatch():
    try:
        Agent1Out(
            ticker="FANG",
            decision_date_T=date(2024, 10, 17),
            fiscal_quarter_end=date(2024, 9, 30),
            n_newly_active=4, n_continuously_active=18, n_idle=8,
            absolute_active=99,  # Should be 22
            share_active=22 / 30, relative_activity_delta=2.5,
            pad_classifications=[],
        )
    except Exception:
        return
    raise AssertionError("Expected validation failure for absolute_active mismatch")
