"""Shared Pydantic schemas for agent system I/O.

These models provide stable JSON serialization for research plans and outputs,
designed for downstream consumption by analysis agents and automation tools.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResearchStepStatus(str, Enum):
    """Status of a research step execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class ResearchStep(BaseModel):
    """A single step in a research plan."""

    model_config = ConfigDict(frozen=True)

    step_id: str = Field(description="Unique identifier for this step (e.g., 'news_search_1')")
    endpoint: str = Field(
        description="Exa endpoint type (search, answer, research, contents, similar)"
    )
    description: str = Field(description="Human-readable step description")
    estimated_cost_usd: float = Field(ge=0.0, description="Estimated cost before execution")
    params: dict[str, Any] = Field(default_factory=dict, description="Step-specific parameters")


class ResearchPlan(BaseModel):
    """Serializable research plan with deterministic steps."""

    model_config = ConfigDict(frozen=True)

    plan_id: str = Field(description="Unique plan identifier")
    ticker: str = Field(description="Market ticker this plan targets")
    mode: str = Field(description="Research mode (fast, standard, deep)")
    steps: list[ResearchStep] = Field(description="Ordered list of research steps")
    total_estimated_cost_usd: float = Field(ge=0.0, description="Sum of step estimates")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def model_dump_json(self, **kwargs: Any) -> str:
        """Serialize to JSON with datetime handling."""
        # Pydantic v2 handles datetime serialization natively
        return super().model_dump_json(**kwargs)


class Factor(BaseModel):
    """A single research factor with supporting evidence."""

    model_config = ConfigDict(frozen=True)

    factor_text: str = Field(description="The factor statement or insight")
    source_url: str = Field(description="Primary URL for this factor")
    confidence: str = Field(
        default="unknown",
        description="Confidence level (high, medium, low, unknown)",
    )
    highlight: str | None = Field(
        default=None, description="Relevant quote or highlight from source"
    )
    published_date: datetime | None = Field(default=None, description="Source publish date")


class ResearchSummary(BaseModel):
    """Structured research output for a market."""

    model_config = ConfigDict(frozen=True)

    ticker: str = Field(description="Market ticker researched")
    title: str = Field(description="Market title")
    mode: str = Field(description="Research mode used (fast, standard, deep)")

    factors: list[Factor] = Field(
        default_factory=list, description="Extracted research factors with citations"
    )

    queries_used: list[str] = Field(default_factory=list, description="Search queries executed")
    total_sources_found: int = Field(ge=0, default=0, description="Total sources returned")

    total_cost_usd: float = Field(ge=0.0, description="Actual total cost spent")
    budget_usd: float = Field(ge=0.0, description="Budget limit for this run")
    budget_exhausted: bool = Field(
        default=False, description="Whether budget was exhausted mid-run"
    )

    researched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    steps_executed: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Debug details: steps run with status and costs",
    )

    def model_dump_json(self, **kwargs: Any) -> str:
        """Serialize to JSON with datetime handling."""
        # Pydantic v2 handles datetime serialization natively
        return super().model_dump_json(**kwargs)


class ResearchStepResult(BaseModel):
    """Result of executing a single research step."""

    model_config = ConfigDict(frozen=True)

    step_id: str
    status: ResearchStepStatus
    actual_cost_usd: float = Field(ge=0.0)
    sources_found: int = Field(ge=0, default=0)
    error_message: str | None = None


# === SPEC-032: Agent System Orchestration Schemas ===


class MarketInfo(BaseModel):
    """Market metadata from Kalshi API."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    event_ticker: str
    series_ticker: str | None
    title: str
    subtitle: str
    status: str
    open_time: datetime
    close_time: datetime
    expiration_time: datetime
    settlement_ts: datetime | None


class MarketPriceSnapshot(BaseModel):
    """Market orderbook and price snapshot."""

    model_config = ConfigDict(frozen=True)

    yes_bid_cents: int
    yes_ask_cents: int
    no_bid_cents: int
    no_ask_cents: int
    last_price_cents: int | None
    volume_24h: int
    open_interest: int
    midpoint_prob: float = Field(ge=0.0, le=1.0, description="Probability (0..1)")
    spread_cents: int
    captured_at: datetime


class NewsArticle(BaseModel):
    """A single news article citation."""

    model_config = ConfigDict(frozen=True)

    title: str
    url: str
    source_domain: str
    published_at: datetime | None
    snippet: str | None
    relevance_score: float | None


class AnalysisFactor(BaseModel):
    """A factor influencing predicted probability."""

    model_config = ConfigDict(frozen=True)

    description: str
    impact: str | None = Field(
        default=None,
        description="Impact direction: 'up', 'down', or 'unclear'",
    )
    source_url: str


class AnalysisResult(BaseModel):
    """Synthesized probability estimate with reasoning."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    market_prob: float = Field(ge=0.0, le=1.0, description="Market-implied probability (0..1)")
    predicted_prob: int = Field(ge=0, le=100, description="Predicted probability (0..100)")
    confidence: str = Field(description="Confidence level: 'low', 'medium', or 'high'")
    reasoning: str
    factors: list[AnalysisFactor] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list, description="Unique source URLs cited")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    model_id: str | None = None


class VerificationReport(BaseModel):
    """Rule-based verification report for AnalysisResult."""

    model_config = ConfigDict(frozen=True)

    passed: bool
    issues: list[str] = Field(default_factory=list, description="Validation failures found")
    checked_sources: list[str] = Field(
        default_factory=list, description="Source URLs checked for validity"
    )
    suggested_escalation: bool = Field(
        default=False, description="Whether escalation is recommended"
    )


class AgentRunResult(BaseModel):
    """Complete result of an agent run."""

    model_config = ConfigDict(frozen=True)

    analysis: AnalysisResult
    verification: VerificationReport
    research: ResearchSummary | None = None
    escalated: bool = False
    total_cost_usd: float = Field(ge=0.0, description="Total cost (Exa + LLM)")

    def model_dump_json(self, **kwargs: Any) -> str:
        """Serialize to JSON with datetime handling."""
        return super().model_dump_json(**kwargs)
