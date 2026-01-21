"""Pydantic models for portfolio balance."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PortfolioBalance(BaseModel):
    """Response from GET /portfolio/balance."""

    model_config = ConfigDict(frozen=True)

    balance: int
    """Available balance in cents (cash not tied up in positions)."""

    portfolio_value: int
    """Total portfolio value in cents (balance + value of open positions)."""

    updated_ts: int | None = None
    """Unix timestamp (seconds) when the balance was last updated (may be absent)."""
