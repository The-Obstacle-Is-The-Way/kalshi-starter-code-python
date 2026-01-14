"""Market data models for Kalshi API."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .pricing import fixed_dollars_to_cents

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


class MarketType(str, Enum):
    """Market type as returned by the API."""

    BINARY = "binary"
    SCALAR = "scalar"


class StrikeType(str, Enum):
    """Strike type for scalar/structured markets (OpenAPI enum)."""

    GREATER = "greater"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS = "less"
    LESS_OR_EQUAL = "less_or_equal"
    BETWEEN = "between"
    FUNCTIONAL = "functional"
    CUSTOM = "custom"
    STRUCTURED = "structured"


class MveSelectedLeg(BaseModel):
    """Selected leg in a multivariate market combination."""

    model_config = ConfigDict(frozen=True)

    event_ticker: str | None = None
    market_ticker: str | None = None
    side: str | None = None


class PriceRange(BaseModel):
    """Valid price range and tick size (OpenAPI PriceRange schema)."""

    model_config = ConfigDict(frozen=True)

    start: str
    end: str
    step: str


class Market(BaseModel):
    """Represents a Kalshi prediction market."""

    model_config = ConfigDict(frozen=True)

    ticker: str = Field(..., description="Unique market identifier")
    event_ticker: str = Field(..., description="Parent event ticker")
    market_type: MarketType | None = Field(
        default=None, description="Market type: binary or scalar"
    )
    # Note: series_ticker may not be present in all responses
    series_ticker: str | None = Field(default=None, description="Parent series ticker")

    title: str = Field(..., description="Market question/title")
    subtitle: str = Field(default="", description="Additional context")
    yes_sub_title: str | None = Field(default=None, description="Short title for YES side")
    no_sub_title: str | None = Field(default=None, description="Short title for NO side")

    status: MarketStatus
    # Result can be "yes", "no", "void", or "" (empty string when undetermined)
    result: Literal["yes", "no", "void", ""] = ""

    response_price_units: Literal["usd_cent"] | None = Field(
        default=None,
        description="DEPRECATED: Use price_level_structure and price_ranges instead.",
    )

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
    previous_yes_bid: int | None = Field(default=None, ge=0, le=100, description="DEPRECATED")
    previous_yes_ask: int | None = Field(default=None, ge=0, le=100, description="DEPRECATED")
    previous_price: int | None = Field(default=None, ge=0, le=100, description="DEPRECATED")

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
    expected_expiration_time: datetime | None = Field(
        default=None,
        description="Projected market expiration time (may be absent).",
    )
    expiration_time: datetime
    latest_expiration_time: datetime | None = Field(
        default=None,
        description="Latest possible market expiration time (may be absent).",
    )
    settlement_timer_seconds: int | None = Field(
        default=None,
        ge=0,
        description="Time after determination before settlement (seconds).",
    )
    settlement_ts: datetime | None = Field(
        default=None,
        description="Actual settlement timestamp (None if not yet settled).",
    )
    fee_waiver_expiration_time: datetime | None = Field(
        default=None,
        description="When promotional fee waiver expires (may be absent).",
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
    notional_value: int | None = Field(
        default=None,
        description="DEPRECATED: Use notional_value_dollars. Contract notional in cents.",
    )
    notional_value_dollars: str | None = Field(
        default=None,
        description="Contract notional value in fixed-point dollars.",
    )

    # Market rules and settlement
    can_close_early: bool | None = Field(
        default=None,
        description="Whether the market can close early (may be absent).",
    )
    settlement_value: int | None = Field(
        default=None,
        description="YES payout in cents after determination (may be absent).",
    )
    settlement_value_dollars: str | None = Field(
        default=None,
        description="YES payout in dollars after determination (may be absent).",
    )
    expiration_value: str | None = Field(
        default=None,
        description="Value used for settlement (may be absent).",
    )
    rules_primary: str | None = Field(
        default=None, description="Primary rules text (may be absent)."
    )
    rules_secondary: str | None = Field(
        default=None, description="Secondary rules text (may be absent)."
    )
    early_close_condition: str | None = Field(
        default=None,
        description="Condition for early close (may be absent).",
    )

    # Pricing structure (subpenny / structured pricing)
    tick_size: int | None = Field(
        default=None,
        description="DEPRECATED: Use price_level_structure and price_ranges instead.",
    )
    price_level_structure: str | None = Field(
        default=None,
        description="Price level structure defining allowed tick sizes (may be absent).",
    )
    price_ranges: list[PriceRange] | None = Field(
        default=None,
        description="Valid price ranges for orders on this market (may be absent).",
    )

    # Strike configuration (scalar / structured markets)
    strike_type: StrikeType | None = Field(default=None, description="Strike evaluation type")
    floor_strike: float | None = Field(
        default=None,
        description="Minimum expiration value that yields a YES settlement (may be absent).",
    )
    cap_strike: float | None = Field(
        default=None,
        description="Maximum expiration value that yields a YES settlement (may be absent).",
    )
    functional_strike: str | None = Field(
        default=None,
        description="Mapping from expiration values to settlement values (may be absent).",
    )
    custom_strike: dict[str, Any] | None = Field(
        default=None,
        description="Per-target expiration values that yield a YES settlement (may be absent).",
    )

    # Multivariate markets
    mve_collection_ticker: str | None = Field(
        default=None,
        description="Ticker of the multivariate event collection (may be absent).",
    )
    mve_selected_legs: list[MveSelectedLeg] | None = Field(
        default=None,
        description="Selected legs in the multivariate combination (may be absent).",
    )
    primary_participant_key: str | None = Field(
        default=None,
        description="Primary participant identifier (may be absent).",
    )
    is_provisional: bool | None = Field(
        default=None,
        description="Whether the market is provisional and may be deleted (may be absent).",
    )

    @field_validator(
        "created_time",
        "open_time",
        "close_time",
        "expected_expiration_time",
        "expiration_time",
        "latest_expiration_time",
        "settlement_ts",
        "fee_waiver_expiration_time",
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
        if self.yes_bid_dollars is not None:
            return fixed_dollars_to_cents(self.yes_bid_dollars, label="market yes_bid_dollars")
        return self.yes_bid or 0

    @property
    def yes_ask_cents(self) -> int:
        """Get yes_ask in cents, preferring dollars field over legacy cents field."""
        if self.yes_ask_dollars is not None:
            return fixed_dollars_to_cents(self.yes_ask_dollars, label="market yes_ask_dollars")
        return self.yes_ask or 0

    @property
    def no_bid_cents(self) -> int:
        """Get no_bid in cents, preferring dollars field over legacy cents field."""
        if self.no_bid_dollars is not None:
            return fixed_dollars_to_cents(self.no_bid_dollars, label="market no_bid_dollars")
        return self.no_bid or 0

    @property
    def no_ask_cents(self) -> int:
        """Get no_ask in cents, preferring dollars field over legacy cents field."""
        if self.no_ask_dollars is not None:
            return fixed_dollars_to_cents(self.no_ask_dollars, label="market no_ask_dollars")
        return self.no_ask or 0

    @property
    def last_price_cents(self) -> int | None:
        """Get last_price in cents, preferring dollars field over legacy cents field."""
        if self.last_price_dollars is not None:
            return fixed_dollars_to_cents(
                self.last_price_dollars, label="market last_price_dollars"
            )
        return self.last_price

    @property
    def midpoint(self) -> float:
        """Calculate midpoint from yes bid/ask using cents values."""
        return (self.yes_bid_cents + self.yes_ask_cents) / 2

    @property
    def spread(self) -> int:
        """Calculate spread (ask - bid) using cents values."""
        return self.yes_ask_cents - self.yes_bid_cents
