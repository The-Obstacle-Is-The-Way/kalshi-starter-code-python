"""Structured target models for the Kalshi API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StructuredTarget(BaseModel):
    """Structured target as returned by `GET /structured_targets` endpoints."""

    model_config = ConfigDict(frozen=True)

    id: str
    type: str
    source_id: str
    name: str
    last_updated_ts: datetime
    details: dict[str, Any] = Field(
        ...,
        description="Type-specific payload (shape depends on structured target type).",
    )


class StructuredTargetsListResponse(BaseModel):
    """Response schema for `GET /structured_targets`."""

    model_config = ConfigDict(frozen=True)

    cursor: str | None = None
    structured_targets: list[StructuredTarget]


class StructuredTargetResponse(BaseModel):
    """Response schema for `GET /structured_targets/{structured_target_id}`."""

    model_config = ConfigDict(frozen=True)

    structured_target: StructuredTarget
