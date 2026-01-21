"""Pydantic models for portfolio settlements."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class Settlement(BaseModel):
    """Single settlement record from GET /portfolio/settlements."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    """Market ticker symbol."""

    event_ticker: str
    """Event ticker symbol."""

    market_result: str
    """Settlement outcome: yes/no/scalar/void."""

    yes_count: int
    """Number of YES contracts held at settlement."""

    yes_total_cost: int
    """Cost basis of YES contracts in cents."""

    no_count: int
    """Number of NO contracts held at settlement."""

    no_total_cost: int
    """Cost basis of NO contracts in cents."""

    revenue: int
    """Total revenue earned from settlement in cents."""

    settled_time: str
    """ISO timestamp when settlement processed."""

    fee_cost: str
    """Total fees paid in fixed-point dollars (e.g., "0.3400")."""

    value: int | None = None
    """Payout per YES contract in cents (scalar markets)."""


class SettlementPage(BaseModel):
    """Paginated response from GET /portfolio/settlements."""

    model_config = ConfigDict(frozen=True)

    settlements: list[Settlement]
    """List of settlement records in this page."""

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
