"""Models for Exa /answer endpoint."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kalshi_research.exa.models.common import CostDollars


class Citation(BaseModel):
    """Citation from Answer endpoint."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: str
    url: str
    title: str
    author: str | None = None
    published_date: datetime | None = Field(default=None, alias="publishedDate")
    text: str | None = None
    image: str | None = None
    favicon: str | None = None

    @field_validator("published_date", mode="before")
    @classmethod
    def coerce_empty_published_date(cls, value: object) -> object:
        """Convert empty-string `publishedDate` values to `None`."""
        if isinstance(value, str) and not value.strip():
            return None
        return value


class AnswerRequest(BaseModel):
    """Request body for /answer endpoint."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    query: str
    stream: bool = False
    text: bool = False


class AnswerResponse(BaseModel):
    """Response from /answer endpoint."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    request_id: str | None = Field(default=None, alias="requestId")
    answer: str
    citations: list[Citation]
    cost_dollars: CostDollars | None = Field(default=None, alias="costDollars")
