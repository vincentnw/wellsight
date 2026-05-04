"""Pydantic schemas for inter-agent JSON contracts (spec Section 4.1)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class PadClassification(BaseModel):
    pad_id: str
    state: Literal["newly_active", "continuously_active", "idle"]


class Agent1Out(BaseModel):
    ticker: str
    decision_date_T: date
    fiscal_quarter_end: date
    n_newly_active: int = Field(ge=0)
    n_continuously_active: int = Field(ge=0)
    n_idle: int = Field(ge=0)
    absolute_active: int = Field(ge=0)
    share_active: float = Field(ge=0.0, le=1.0)
    relative_activity_delta: float
    pad_classifications: list[PadClassification]

    @model_validator(mode="after")
    def _check_aggregation_consistency(self) -> "Agent1Out":
        if self.absolute_active != self.n_newly_active + self.n_continuously_active:
            raise ValueError(
                f"absolute_active={self.absolute_active} != "
                f"n_newly_active+n_continuously_active="
                f"{self.n_newly_active + self.n_continuously_active}"
            )
        total = self.n_newly_active + self.n_continuously_active + self.n_idle
        if total > 0:
            implied_share = (self.n_newly_active + self.n_continuously_active) / total
            if abs(implied_share - self.share_active) > 1e-6:
                raise ValueError(
                    f"share_active={self.share_active} inconsistent with counts "
                    f"(implied {implied_share})"
                )
        # Per-pad classifications composition must match aggregated counts
        if self.pad_classifications:
            from collections import Counter
            counts = Counter(p.state for p in self.pad_classifications)
            if counts.get("newly_active", 0) != self.n_newly_active:
                raise ValueError("pad_classifications newly_active count mismatch")
            if counts.get("continuously_active", 0) != self.n_continuously_active:
                raise ValueError("pad_classifications continuously_active count mismatch")
            if counts.get("idle", 0) != self.n_idle:
                raise ValueError("pad_classifications idle count mismatch")
        return self


class Agent2Out(BaseModel):
    ticker: str
    revenue_forecast_usd: float
    components: dict
    outlook_paragraph: str = Field(max_length=2000)
    key_drivers: list[str] = Field(max_length=5)


class Agent3Out(BaseModel):
    ticker: str
    our_estimate_usd: float
    consensus_median_usd: float
    consensus_dispersion_usd: float
    n_analysts_at_T_minus_14: int = Field(ge=0)
    divergence_pct: float
    divergence_class: Literal[
        "strong_beat", "modest_beat", "in_line", "modest_miss", "strong_miss"
    ]
    confidence: Literal["high", "medium", "low"]
    reasoning: str = Field(max_length=1500)

    @model_validator(mode="after")
    def _check_class_matches_pct(self) -> "Agent3Out":
        """Codex Issue 5 fix: divergence_class must agree with divergence_pct
        under the threshold table from the prompt. This is the crucial
        consistency check because divergence_class is the trade gate."""
        p = self.divergence_pct
        if p > 15.0:
            expected = "strong_beat"
        elif p > 5.0:
            expected = "modest_beat"
        elif p >= -5.0:
            expected = "in_line"
        elif p >= -15.0:
            expected = "modest_miss"
        else:
            expected = "strong_miss"
        if self.divergence_class != expected:
            raise ValueError(
                f"divergence_class={self.divergence_class} does not match "
                f"divergence_pct={p:.2f} (expected {expected})"
            )
        return self


class CatalystRef(BaseModel):
    """A single positive or negative catalyst extracted from a news article.

    Added by the Agent 4 redesign (docs/AGENT4_5_REDESIGN.md). The Bull/Bear
    debate uses these as evidence; the article reference enables audit-trail
    sourcing back to GDELT."""
    summary: str = Field(max_length=300)
    article_id: str | None = None
    article_date: str | None = None  # ISO date string; T-14 cutoff enforced upstream


class Agent4Out(BaseModel):
    """Agent 4 output schema. Backward-compatible: legacy fields are kept
    optional so existing run dirs (using the novelty-check Agent 4) still
    validate. The new redesign populates the catalyst-brief fields instead.

    See docs/AGENT4_5_REDESIGN.md."""
    ticker: str
    n_articles_in_window: int
    fallback_used: bool = False

    # Legacy novelty-check fields (kept optional for backward-compat with old runs)
    gdelt_disclosed: bool | None = None
    matching_article_ids: list[str] | None = None
    conviction_modifier: Literal["none", "downgrade_one_tier"] | None = None
    reasoning: str | None = Field(default=None, max_length=1500)

    # New catalyst-brief fields (populated by the redesigned Agent 4)
    positive_catalysts: list[CatalystRef] | None = Field(default=None, max_length=5)
    negative_catalysts: list[CatalystRef] | None = Field(default=None, max_length=5)
    overall_sentiment: Literal["bullish", "neutral", "bearish"] | None = None
    sar_complement: str | None = Field(default=None, max_length=600)
    novelty_assessment: Literal["yes", "no", "partial"] | None = None


class BoardMemberOpinion(BaseModel):
    role: Literal["bull", "bear", "arbiter"]
    direction: Literal["long", "no_trade"]
    confidence: Literal["high", "medium", "low"]
    key_evidence: list[str] = Field(max_length=3)
    counter_evidence: list[str] = Field(max_length=3)
    reasoning_short: str = Field(max_length=1500)


class UpstreamAgentSummary(BaseModel):
    """Required structure for Agent 5's upstream attribution summary
    (spec Section 4.1)."""
    agent2_decisive: bool
    agent3_decisive: bool
    agent4_decisive: bool
    agent2_weight: float = Field(ge=0.0, le=1.0)
    agent3_weight: float = Field(ge=0.0, le=1.0)
    agent4_weight: float = Field(ge=0.0, le=1.0)


CONVICTION_TO_SIZE = {"high": 0.15, "medium": 0.10, "low": 0.05, "none": 0.0}


class Agent5Out(BaseModel):
    ticker: str
    decision: Literal["long", "no_trade"]
    conviction_tier: Literal["high", "medium", "low", "none"]
    final_size_pct: float
    bull_opinion: BoardMemberOpinion
    bear_opinion: BoardMemberOpinion
    arbiter_reasoning: str = Field(max_length=3000)
    upstream_agent_summary: UpstreamAgentSummary

    # New (Agent 4+5 redesign): conviction_score 0-100 from the Arbiter,
    # used by the trade-selection layer to rank cells and pick top K per cycle.
    # Optional for backward-compat with existing run dirs (None on old cells).
    # See docs/AGENT4_5_REDESIGN.md.
    conviction_score: float | None = Field(default=None, ge=0.0, le=100.0)

    @field_validator("final_size_pct")
    @classmethod
    def size_must_be_locked(cls, v: float) -> float:
        if v not in {0.0, 0.05, 0.10, 0.15}:
            raise ValueError(
                f"final_size_pct {v} not in locked set {{0, 0.05, 0.10, 0.15}}"
            )
        return v

    @model_validator(mode="after")
    def _check_size_matches_conviction(self) -> "Agent5Out":
        # When deciding no_trade the size must be 0 regardless of tier.
        if self.decision == "no_trade":
            if self.final_size_pct != 0.0:
                raise ValueError(
                    f"decision=no_trade but final_size_pct={self.final_size_pct}"
                )
            return self
        # When deciding long, size must follow the locked lookup table.
        expected = CONVICTION_TO_SIZE[self.conviction_tier]
        if abs(self.final_size_pct - expected) > 1e-9:
            raise ValueError(
                f"final_size_pct={self.final_size_pct} does not match "
                f"conviction_tier={self.conviction_tier} (expected {expected})"
            )
        return self


class CellResult(BaseModel):
    ticker: str
    fiscal_quarter_end: date
    decision_date_T: date
    decision: Literal["long", "no_trade"]
    conviction_tier: Literal["high", "medium", "low", "none"]
    final_size_pct: float
    low_quality_flag: bool = False
    error: str | None = None


class TradeDecision(BaseModel):
    ticker: str
    decision_date_T: date
    direction: Literal["long", "no_trade"]
    size_pct: float
