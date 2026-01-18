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
