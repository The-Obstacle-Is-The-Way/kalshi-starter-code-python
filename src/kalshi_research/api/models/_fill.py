"""Pydantic models for portfolio fills (trades)."""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class Fill(BaseModel):
    """Single fill (completed trade) from GET /portfolio/fills."""

    model_config = ConfigDict(frozen=True)

    fill_id: str | None = None
    """Unique fill identifier (may be redundant with trade_id)."""

    trade_id: str
    """Unique trade identifier."""

    order_id: str | None = None
    """Order identifier that resulted in this fill (may be absent)."""

    client_order_id: str | None = None
    """Client-provided identifier for the order that resulted in this fill (may be absent)."""

    ticker: str = Field(validation_alias=AliasChoices("ticker", "market_ticker"))
    """Market ticker symbol (accepts legacy `market_ticker`)."""

    side: str | None = None
    """Position side: 'yes' or 'no' (may be absent in some API responses)."""

    action: str | None = None
    """Trade action: 'buy' or 'sell' (may be absent in some API responses)."""

    price: float | None = None
    """Deprecated fill price (may be absent; prefer yes_price/no_price)."""

    yes_price: int
    """YES price in cents (0-100)."""

    no_price: int | None = None
    """NO price in cents (0-100), may be derived from yes_price."""

    yes_price_fixed: str | None = None
    """YES price in fixed-point dollars (may be absent)."""

    no_price_fixed: str | None = None
    """NO price in fixed-point dollars (may be absent)."""

    is_taker: bool | None = None
    """True if this fill removed liquidity from the orderbook (may be absent)."""

    count: int
    """Number of contracts filled."""

    created_time: str
    """ISO timestamp of when the fill occurred."""

    ts: int | None = None
    """Unix timestamp (seconds) of the fill (may be absent)."""


class FillPage(BaseModel):
    """Paginated response from GET /portfolio/fills."""

    model_config = ConfigDict(frozen=True)

    fills: list[Fill]
    """List of fills in this page."""

    cursor: str | None = None
    """Cursor for next page (None if last page)."""

    @field_validator("cursor", mode="before")
    @classmethod
    def normalize_cursor(cls, value: object) -> str | None:
        """Normalize empty-string cursors to None (API may return "" for last page)."""
        if value is None or value == "":
            return None
        if isinstance(value, str):
            return value
        return str(value)
