"""Market data models for Kalshi API."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
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

    # Pricing - NEW dollar fields (strings from API, format: "0.4500")
    # These will become the primary fields after Jan 15, 2026
    yes_bid_dollars: str | None = Field(default=None, description="Yes bid (dollars)")
    yes_ask_dollars: str | None = Field(default=None, description="Yes ask (dollars)")
    no_bid_dollars: str | None = Field(default=None, description="No bid (dollars)")
    no_ask_dollars: str | None = Field(default=None, description="No ask (dollars)")
    last_price_dollars: str | None = Field(default=None, description="Last price (dollars)")
    previous_price_dollars: str | None = Field(default=None, description="Prev close (dollars)")
    previous_yes_bid_dollars: str | None = Field(default=None, description="Prev yes bid (dollars)")
    previous_yes_ask_dollars: str | None = Field(default=None, description="Prev yes ask (dollars)")

    # Legacy pricing (DEPRECATED: removed Jan 15, 2026 - use *_dollars fields)
    yes_bid: int | None = Field(default=None, ge=0, le=100, description="DEPRECATED")
    yes_ask: int | None = Field(default=None, ge=0, le=100, description="DEPRECATED")
    no_bid: int | None = Field(default=None, ge=0, le=100, description="DEPRECATED")
    no_ask: int | None = Field(default=None, ge=0, le=100, description="DEPRECATED")
    last_price: int | None = Field(default=None, ge=0, le=100, description="DEPRECATED")

    # Volume
    volume: int = Field(..., ge=0, description="Total contracts traded")
    volume_24h: int = Field(..., ge=0, description="24h volume")
    open_interest: int = Field(..., ge=0, description="Open contracts")

    # Timestamps
    created_time: datetime | None = Field(default=None, description="When the market was created")
    open_time: datetime
    close_time: datetime
    expiration_time: datetime
    settlement_ts: datetime | None = Field(
        default=None,
        description="Actual settlement timestamp (None if not yet settled).",
    )

    # Liquidity (DEPRECATED: removed Jan 15, 2026 - use dollar fields)
    liquidity: int | None = Field(
        default=None,
        description="DEPRECATED: Use dollar-denominated fields. Removed Jan 15, 2026.",
    )
    liquidity_dollars: str | None = Field(
        default=None,
        description="Current offer value in fixed-point dollars (replacement for `liquidity`).",
    )
    notional_value_dollars: str | None = Field(
        default=None,
        description="Contract notional value in fixed-point dollars.",
    )

    @field_validator(
        "created_time",
        "open_time",
        "close_time",
        "expiration_time",
        "settlement_ts",
        mode="after",
    )
    @classmethod
    def ensure_utc_aware(cls, dt: datetime | None) -> datetime | None:
        """Normalize datetime fields to timezone-aware UTC values."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)

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

    # Computed properties for backwards compatibility
    # These provide cents values, preferring new dollar fields over legacy cent fields

    @property
    def yes_bid_cents(self) -> int:
        """Get yes_bid in cents, preferring dollars field over legacy cents field."""
        if self.yes_bid_dollars:
            return int(Decimal(self.yes_bid_dollars) * 100)
        return self.yes_bid or 0

    @property
    def yes_ask_cents(self) -> int:
        """Get yes_ask in cents, preferring dollars field over legacy cents field."""
        if self.yes_ask_dollars:
            return int(Decimal(self.yes_ask_dollars) * 100)
        return self.yes_ask or 0

    @property
    def no_bid_cents(self) -> int:
        """Get no_bid in cents, preferring dollars field over legacy cents field."""
        if self.no_bid_dollars:
            return int(Decimal(self.no_bid_dollars) * 100)
        return self.no_bid or 0

    @property
    def no_ask_cents(self) -> int:
        """Get no_ask in cents, preferring dollars field over legacy cents field."""
        if self.no_ask_dollars:
            return int(Decimal(self.no_ask_dollars) * 100)
        return self.no_ask or 0

    @property
    def last_price_cents(self) -> int | None:
        """Get last_price in cents, preferring dollars field over legacy cents field."""
        if self.last_price_dollars:
            return int(Decimal(self.last_price_dollars) * 100)
        return self.last_price

    @property
    def midpoint(self) -> float:
        """Calculate midpoint from yes bid/ask using cents values."""
        return (self.yes_bid_cents + self.yes_ask_cents) / 2

    @property
    def spread(self) -> int:
        """Calculate spread (ask - bid) using cents values."""
        return self.yes_ask_cents - self.yes_bid_cents
