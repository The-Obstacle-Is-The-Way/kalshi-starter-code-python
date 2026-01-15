"""Milestone models for the Kalshi API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Milestone(BaseModel):
    """Milestone as returned by `GET /milestones` endpoints."""

    model_config = ConfigDict(frozen=True)

    id: str
    category: str
    type: str
    start_date: datetime
    end_date: datetime | None = None
    related_event_tickers: list[str]
    title: str
    notification_message: str
    source_id: str | None = None
    details: dict[str, Any] = Field(
        ...,
        description="Type-specific milestone details (shape varies by milestone type).",
    )
    primary_event_tickers: list[str]
    last_updated_ts: datetime


class MilestoneResponse(BaseModel):
    """Response schema for `GET /milestones/{milestone_id}`."""

    model_config = ConfigDict(frozen=True)

    milestone: Milestone


class MilestonesResponse(BaseModel):
    """Response schema for `GET /milestones`."""

    model_config = ConfigDict(frozen=True)

    milestones: list[Milestone]
    cursor: str | None = None

    @field_validator("cursor", mode="before")
    @classmethod
    def normalize_cursor(cls, value: object) -> str | None:
        """Normalize empty-string cursors to None (API may return \"\" for last page)."""
        if value is None or value == "":
            return None
        if isinstance(value, str):
            return value
        return str(value)
