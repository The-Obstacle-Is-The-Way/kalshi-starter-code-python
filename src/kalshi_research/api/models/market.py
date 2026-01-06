"""Market data models for Kalshi API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MarketStatus(str, Enum):
    """Market status as returned in API responses."""

    ACTIVE = "active"
    CLOSED = "closed"
    DETERMINED = "determined"
    FINALIZED = "finalized"


class MarketFilterStatus(str, Enum):
    """Market status values for API filter parameters."""

    UNOPENED = "unopened"
    OPEN = "open"
    CLOSED = "closed"
    SETTLED = "settled"


class Market(BaseModel):
    """Represents a Kalshi prediction market."""

    model_config = ConfigDict(frozen=True)

    ticker: str = Field(..., description="Unique market identifier")
    event_ticker: str = Field(..., description="Parent event ticker")
    # Note: series_ticker may not be present in all responses
    series_ticker: str | None = Field(default=None, description="Parent series ticker")

    title: str = Field(..., description="Market question/title")
    subtitle: str = Field(default="", description="Additional context")

    status: MarketStatus
    # Result can be "yes", "no", "void", or "" (empty string when undetermined)
    result: Literal["yes", "no", "void", ""] = ""

    # Pricing (in cents, 0-100)
    yes_bid: int = Field(..., ge=0, le=100, description="Best yes bid in cents")
    yes_ask: int = Field(..., ge=0, le=100, description="Best yes ask in cents")
    no_bid: int = Field(..., ge=0, le=100, description="Best no bid in cents")
    no_ask: int = Field(..., ge=0, le=100, description="Best no ask in cents")
    last_price: int | None = Field(default=None, ge=0, le=100)

    # Volume
    volume: int = Field(..., ge=0, description="Total contracts traded")
    volume_24h: int = Field(..., ge=0, description="24h volume")
    open_interest: int = Field(..., ge=0, description="Open contracts")

    # Timestamps
    open_time: datetime
    close_time: datetime
    expiration_time: datetime

    # Liquidity
    liquidity: int = Field(..., ge=0, description="Dollar liquidity")
