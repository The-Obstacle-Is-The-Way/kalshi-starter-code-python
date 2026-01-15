"""Event data models for Kalshi API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kalshi_research.api.models.market import Market  # noqa: TC001
from kalshi_research.api.models.series import SettlementSource  # noqa: TC001


class Event(BaseModel):
    """Event as returned by the Kalshi API."""

    model_config = ConfigDict(frozen=True)

    event_ticker: str = Field(..., description="Unique event identifier")
    series_ticker: str = Field(..., description="Parent series ticker")
    title: str
    sub_title: str = ""
    category: str | None = None

    markets: list[Market] | None = Field(
        default=None,
        description="Markets associated with this event (only when with_nested_markets=true).",
    )

    mutually_exclusive: bool = False
    available_on_brokers: bool = False

    collateral_return_type: str = ""
    strike_period: str = ""
    strike_date: datetime | None = None

    @field_validator("strike_date", mode="before")
    @classmethod
    def _empty_str_to_none(cls, value: Any) -> Any:
        if value in ("", None):
            return None
        return value


class MarketMetadata(BaseModel):
    """Per-market metadata from `GET /events/{event_ticker}/metadata`."""

    model_config = ConfigDict(frozen=True)

    market_ticker: str
    image_url: str
    color_code: str


class EventMetadataResponse(BaseModel):
    """Response schema for `GET /events/{event_ticker}/metadata`.

    Note: `market_details` and `settlement_sources` may be None for some event types
    (e.g., MVE sports events).
    """

    model_config = ConfigDict(frozen=True)

    image_url: str
    featured_image_url: str | None = None
    market_details: list[MarketMetadata] | None = None
    settlement_sources: list[SettlementSource] | None = None
