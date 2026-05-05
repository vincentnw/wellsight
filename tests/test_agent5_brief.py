"""Tests for the v2.6 brief coercion layer.

The brief LLM is not trusted to honor the data_insufficient contract on
its own. _coerce_brief() must enforce three guardrails per the v2.6
pre-registration:

  1. If an evidence-packet section has data_sufficient=False, every
     interpretive (non-evidence) field in that brief section is forced
     to "data_insufficient" regardless of what the LLM said.
  2. Risk flags whose validity depends on an insufficient section are
     dropped from overall_risk_flags.
  3. If reaction_history, fundamentals, and positioning are ALL
     insufficient, tradable_setup is forced to "data_insufficient".
"""

from fin580.agents.agent5_brief import _coerce_brief


def _packet(*, reaction_ok=True, fundamentals_ok=True, positioning_ok=True):
    return {
        "reaction_history": {"data_sufficient": reaction_ok},
        "fundamentals": {"data_sufficient": fundamentals_ok},
        "positioning": {"data_sufficient": positioning_ok},
        "regime": {},  # regime has no top-level data_sufficient
    }


def _full_brief():
    return {
        "ticker": "FANG",
        "reaction_history_summary": {
            "revenue_historically_moves_stock": "no",
            "evidence": "fabricated by LLM despite no data",
        },
        "fundamentals_summary": {
            "margin_trajectory": "deteriorating",
            "capex_pressure": "high",
            "evidence": "fabricated",
        },
        "regime_summary": {
            "oil_regime": "tailwind",
            "stock_oil_dependence": "high",
            "evidence": "real",
        },
        "positioning_summary": {
            "extended_or_overbought": "yes",
            "evidence": "fabricated",
        },
        "overall_risk_flags": [
            "weak-revenue-reaction-history",
            "margin-deterioration",
            "extended-positioning",
            "oil-regime-stress",
        ],
        "tradable_setup": "no",
    }


def test_insufficient_section_coerces_interpretive_fields():
    packet = _packet(reaction_ok=False)
    brief = _coerce_brief(_full_brief(), packet)
    # Every non-evidence field in reaction_history_summary becomes data_insufficient.
    assert brief["reaction_history_summary"]["revenue_historically_moves_stock"] == "data_insufficient"
    # Other sections are untouched.
    assert brief["fundamentals_summary"]["margin_trajectory"] == "deteriorating"
    assert brief["regime_summary"]["oil_regime"] == "tailwind"
    assert brief["positioning_summary"]["extended_or_overbought"] == "yes"


def test_evidence_field_neutralized_for_insufficient_sections():
    """Updated v2.6.1: insufficient sections have their evidence text
    replaced with a neutral disclaimer (was: preserved verbatim, but that
    let the LLM's unsupported free-text claims influence the board)."""
    packet = _packet(reaction_ok=False)
    brief = _coerce_brief(_full_brief(), packet)
    assert "Insufficient" in brief["reaction_history_summary"]["evidence"]
    assert "fabricated" not in brief["reaction_history_summary"]["evidence"]


def test_risk_flag_dependent_on_insufficient_section_is_stripped():
    packet = _packet(reaction_ok=False)
    brief = _coerce_brief(_full_brief(), packet)
    flags = brief["overall_risk_flags"]
    assert "weak-revenue-reaction-history" not in flags
    # Flags that don't depend on the insufficient section survive.
    assert "margin-deterioration" in flags
    assert "extended-positioning" in flags
    assert "oil-regime-stress" in flags


def test_multiple_insufficient_sections_strip_multiple_flags():
    packet = _packet(reaction_ok=False, positioning_ok=False)
    brief = _coerce_brief(_full_brief(), packet)
    flags = brief["overall_risk_flags"]
    assert "weak-revenue-reaction-history" not in flags
    assert "extended-positioning" not in flags
    assert "margin-deterioration" in flags
    assert "oil-regime-stress" in flags


def test_all_three_insufficient_downgrades_tradable_setup():
    packet = _packet(reaction_ok=False, fundamentals_ok=False, positioning_ok=False)
    brief = _coerce_brief(_full_brief(), packet)
    assert brief["tradable_setup"] == "data_insufficient"


def test_partial_insufficient_does_not_downgrade_tradable_setup():
    # Only reaction_history insufficient — tradable_setup is preserved.
    packet = _packet(reaction_ok=False)
    brief = _coerce_brief(_full_brief(), packet)
    assert brief["tradable_setup"] == "no"


def test_all_sufficient_passes_through_unchanged():
    packet = _packet()
    brief_in = _full_brief()
    brief_out = _coerce_brief(dict(brief_in), packet)
    assert brief_out["reaction_history_summary"]["revenue_historically_moves_stock"] == "no"
    assert brief_out["overall_risk_flags"] == brief_in["overall_risk_flags"]
    assert brief_out["tradable_setup"] == "no"


def test_non_dict_brief_input_returns_as_is():
    out = _coerce_brief("not a dict", _packet())
    assert out == "not a dict"


def test_insufficient_section_neutralizes_evidence_text():
    """Free-text evidence in an insufficient section is replaced with a
    neutral disclaimer so the board cannot read an unsupported LLM claim."""
    packet = _packet(reaction_ok=False)
    brief = _coerce_brief(_full_brief(), packet)
    assert brief["reaction_history_summary"]["evidence"].startswith(
        "Insufficient point-in-time observations"
    )
    # Sufficient sections retain their original evidence text.
    assert brief["regime_summary"]["evidence"] == "real"


def test_coercion_notes_field_lists_coerced_sections():
    packet = _packet(reaction_ok=False, positioning_ok=False)
    brief = _coerce_brief(_full_brief(), packet)
    assert sorted(brief.get("coercion_notes", [])) == [
        "positioning_summary",
        "reaction_history_summary",
    ]


def test_no_coercion_notes_when_all_sufficient():
    packet = _packet()
    brief = _coerce_brief(_full_brief(), packet)
    # Either absent or empty list — both acceptable
    assert not brief.get("coercion_notes")


def test_rationale_prefixed_with_binding_coercion_notice():
    brief_in = _full_brief()
    brief_in["rationale"] = "Reaction history is weak; recommend no_trade."
    packet = _packet(reaction_ok=False)
    brief = _coerce_brief(brief_in, packet)
    assert brief["rationale"].startswith("[COERCION OVERRIDE — BINDING]")
    assert "reaction_history_summary" in brief["rationale"]
    # Original rationale text is preserved at the end (for audit) but the
    # binding override comes first.
    assert "Reaction history is weak" in brief["rationale"]


def test_rationale_unchanged_when_all_sufficient():
    brief_in = _full_brief()
    brief_in["rationale"] = "Original rationale text."
    packet = _packet()
    brief = _coerce_brief(brief_in, packet)
    assert brief["rationale"] == "Original rationale text."


def test_empty_rationale_still_gets_coercion_notice():
    brief_in = _full_brief()
    brief_in["rationale"] = ""
    packet = _packet(fundamentals_ok=False)
    brief = _coerce_brief(brief_in, packet)
    assert brief["rationale"].startswith("[COERCION OVERRIDE — BINDING]")
