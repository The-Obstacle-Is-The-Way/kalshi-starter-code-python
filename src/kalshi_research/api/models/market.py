"""Market data models for Kalshi API."""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


class MarketStatus(str, Enum):
    """Market status as returned in API responses.

    Note: Filter params use different values (MarketFilterStatus).
    See: docs/_vendor-docs/kalshi-api-reference.md
    """

    INITIALIZED = "initialized"  # New markets not yet open
    ACTIVE = "active"
    INACTIVE = "inactive"
    CLOSED = "closed"
    DETERMINED = "determined"
    DISPUTED = "disputed"  # Market outcome under dispute
    AMENDED = "amended"  # Market terms were amended
    FINALIZED = "finalized"


class MarketFilterStatus(str, Enum):
    """Market status values for API filter parameters."""

    UNOPENED = "unopened"
    OPEN = "open"
    PAUSED = "paused"
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
    created_time: datetime | None = Field(default=None, description="When the market was created")
    open_time: datetime
    close_time: datetime
    expiration_time: datetime

    # Liquidity (DEPRECATED: removed Jan 15, 2026 - use dollar fields)
    liquidity: int | None = Field(
        default=None,
        description="DEPRECATED: Use dollar-denominated fields. Removed Jan 15, 2026.",
    )

    @field_validator("liquidity", mode="before")
    @classmethod
    def handle_deprecated_liquidity(cls, v: int | None) -> int | None:
        """Handle deprecated liquidity field gracefully.

        The liquidity field is deprecated as of Jan 15, 2026 per Kalshi API changelog.
        Negative values are observed in production and treated as None.
        """
        if v is None:
            return None
        if v < 0:
            logger.warning(
                "Received negative liquidity value: %s. "
                "Treating as None. Field deprecated Jan 15, 2026.",
                v,
            )
            return None
        return v
