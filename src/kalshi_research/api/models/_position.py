"""Pydantic models for portfolio positions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PortfolioPosition(BaseModel):
    """Single market position from GET /portfolio/positions (`market_positions`)."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    """Market ticker symbol."""

    position: int
    """Net position: positive for YES, negative for NO, zero if closed."""

    market_exposure: int | None = None
    """Current market exposure in cents (may be absent)."""

    market_exposure_dollars: str | None = None
    """Current market exposure in dollars (fixed-point string, may be absent)."""

    realized_pnl: int | None = None
    """Realized profit/loss in cents from closed trades (may be absent)."""

    realized_pnl_dollars: str | None = None
    """Realized profit/loss in dollars (fixed-point string, may be absent)."""

    fees_paid: int | None = None
    """Total fees paid in cents (may be absent)."""

    fees_paid_dollars: str | None = None
    """Total fees paid in dollars (fixed-point string, may be absent)."""

    total_traded: int | None = None
    """Total spent on this market in cents (may be absent)."""

    total_traded_dollars: str | None = None
    """Total spent on this market in dollars (fixed-point string, may be absent)."""

    resting_orders_count: int | None = None
    """Count of currently resting orders (may be absent)."""

    last_updated_ts: str | None = None
    """RFC3339 timestamp of last position update (may be absent)."""
