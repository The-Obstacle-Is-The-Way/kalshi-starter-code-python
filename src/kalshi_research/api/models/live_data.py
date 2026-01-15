"""Live data models for the Kalshi API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LiveData(BaseModel):
    """Live data item as returned by `GET /live_data/*` endpoints."""

    model_config = ConfigDict(frozen=True)

    type: str
    milestone_id: str
    details: dict[str, Any] = Field(
        ...,
        description="Type-specific live data payload (shape varies by live data type).",
    )


class LiveDataResponse(BaseModel):
    """Response schema for `GET /live_data/{type}/milestone/{milestone_id}`."""

    model_config = ConfigDict(frozen=True)

    live_data: LiveData


class LiveDataBatchResponse(BaseModel):
    """Response schema for `GET /live_data/batch`."""

    model_config = ConfigDict(frozen=True)

    live_datas: list[LiveData]
