"""WebSocket message models."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class TickerUpdate(BaseModel):
    """
    Ticker channel update message.
    
    CRITICAL: Integer prices are in CENTS (0-100).
    """

    market_ticker: str
    price: int = Field(..., description="Last traded price in CENTS")
    yes_bid: int = Field(..., description="Best yes bid in CENTS")
    yes_ask: int = Field(..., description="Best yes ask in CENTS")
    volume: int
    open_interest: int
    
    # Dollar fields (strings)
    price_dollars: str | None = None
    yes_bid_dollars: str | None = None
    yes_ask_dollars: str | None = None

    @property
    def price_decimal(self) -> Decimal:
        """Convert price to dollars (Decimal)."""
        return Decimal(self.price) / Decimal(100)


class OrderbookDelta(BaseModel):
    """Orderbook delta update."""
    market_ticker: str
    yes: list[list[int]]  # [[price_cents, count], ...]
    no: list[list[int]]


class TradeUpdate(BaseModel):
    """Public trade update."""
    market_ticker: str
    price: int  # cents
    count: int
    created_time: str
    taker_side: str


class MarketPositionUpdate(BaseModel):
    """
    Market positions channel update.
    
    CRITICAL: Monetary values are in CENTI-CENTS (1/10000 dollar).
    """

    market_ticker: str
    position: int  # contract count
    position_cost: int  # centi-cents
    realized_pnl: int  # centi-cents
    fees_paid: int  # centi-cents

    @property
    def position_cost_dollars(self) -> Decimal:
        """Convert centi-cents to dollars (÷10,000)."""
        return Decimal(self.position_cost) / Decimal(10000)

    @property
    def realized_pnl_dollars(self) -> Decimal:
        """Convert centi-cents to dollars (÷10,000)."""
        return Decimal(self.realized_pnl) / Decimal(10000)
