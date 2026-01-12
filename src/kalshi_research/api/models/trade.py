"""Trade data models for Kalshi API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Trade(BaseModel):
    """Public trade record."""

    model_config = ConfigDict(frozen=True)

    trade_id: str
    ticker: str
    created_time: datetime  # Note: API uses created_time, not timestamp
    yes_price: int = Field(..., ge=0, le=100, description="YES price in cents (rounded)")
    yes_price_dollars: str | None = None
    no_price: int = Field(..., ge=0, le=100, description="NO price in cents (rounded)")
    no_price_dollars: str | None = None
    price: float | None = None
    count: int = Field(..., ge=1, description="Number of contracts")
    taker_side: Literal["yes", "no"]
