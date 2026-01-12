"""Models for Exa /research/v1 endpoint."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResearchModel(str, Enum):
    """Exa research model tiers."""

    STANDARD = "exa-research"
    PRO = "exa-research-pro"


class ResearchStatus(str, Enum):
    """Research task status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"


class ResearchRequest(BaseModel):
    """Request body for /research/v1 endpoint."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    instructions: str = Field(max_length=4096)
    model: ResearchModel = ResearchModel.STANDARD
    output_schema: dict[str, Any] | None = Field(default=None, alias="outputSchema")


class ResearchOutput(BaseModel):
    """Output from completed research task."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    content: str
    parsed: dict[str, Any] | None = None


class ResearchCostDollars(BaseModel):
    """Cost information for research tasks (completed responses only)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    total: float
    num_searches: float = Field(alias="numSearches")
    num_pages: float = Field(alias="numPages")
    reasoning_tokens: float = Field(alias="reasoningTokens")


class ResearchTask(BaseModel):
    """Research task response."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    class Citation(BaseModel):
        """Citation returned by research output (may be absent)."""

        model_config = ConfigDict(frozen=True, populate_by_name=True)

        id: str
        url: str
        title: str | None = None

    research_id: str = Field(alias="researchId")
    status: ResearchStatus
    created_at: int = Field(alias="createdAt")
    finished_at: int | None = Field(default=None, alias="finishedAt")
    model: str | None = None
    instructions: str
    output: ResearchOutput | None = None
    citations: list[Citation] | None = None
    cost_dollars: ResearchCostDollars | None = Field(default=None, alias="costDollars")
    error: str | None = None
