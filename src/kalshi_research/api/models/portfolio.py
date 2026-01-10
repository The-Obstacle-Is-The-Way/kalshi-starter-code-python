"""Pydantic models for Kalshi Portfolio API responses."""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class PortfolioBalance(BaseModel):
    """Response from GET /portfolio/balance."""

    model_config = ConfigDict(frozen=True)

    balance: int
    """Available balance in cents (cash not tied up in positions)."""

    portfolio_value: int
    """Total portfolio value in cents (balance + value of open positions)."""


class PortfolioPosition(BaseModel):
    """Single market position from GET /portfolio/positions (`market_positions`)."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    """Market ticker symbol."""

    position: int
    """Net position: positive for YES, negative for NO, zero if closed."""

    market_exposure: int | None = None
    """Current market exposure in cents (may be absent)."""

    realized_pnl: int | None = None
    """Realized profit/loss in cents from closed trades (may be absent)."""

    fees_paid: int | None = None
    """Total fees paid in cents (may be absent)."""


class Fill(BaseModel):
    """Single fill (completed trade) from GET /portfolio/fills."""

    model_config = ConfigDict(frozen=True)

    trade_id: str
    """Unique trade identifier."""

    ticker: str
    """Market ticker symbol."""

    side: str | None = None
    """Position side: 'yes' or 'no' (may be absent in some API responses)."""

    action: str | None = None
    """Trade action: 'buy' or 'sell' (may be absent in some API responses)."""

    yes_price: int
    """YES price in cents (0-100)."""

    no_price: int | None = None
    """NO price in cents (0-100), may be derived from yes_price."""

    count: int
    """Number of contracts filled."""

    created_time: str
    """ISO timestamp of when the fill occurred."""


class FillPage(BaseModel):
    """Paginated response from GET /portfolio/fills."""

    model_config = ConfigDict(frozen=True)

    fills: list[Fill]
    """List of fills in this page."""

    cursor: str | None = None
    """Cursor for next page (None if last page)."""


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
    """Total fees paid in fixed-point dollars (e.g., \"0.3400\")."""

    value: int | None = None
    """Payout per YES contract in cents (scalar markets)."""


class SettlementPage(BaseModel):
    """Paginated response from GET /portfolio/settlements."""

    model_config = ConfigDict(frozen=True)

    settlements: list[Settlement]
    """List of settlement records in this page."""

    cursor: str | None = None
    """Cursor for next page (None if last page)."""


class Order(BaseModel):
    """Single order from GET /portfolio/orders."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    """Unique order identifier."""

    ticker: str
    """Market ticker symbol."""

    status: str
    """Order status: 'resting', 'canceled', 'executed', etc."""

    side: str | None = None
    """Position side: 'yes' or 'no'."""

    action: str | None = None
    """Order action: 'buy' or 'sell'."""

    yes_price: int | None = None
    """YES limit price in cents (0-100)."""

    no_price: int | None = None
    """NO limit price in cents (0-100)."""

    count: int | None = None
    """Number of contracts (remaining or total)."""

    placed_at: str | None = None
    """ISO timestamp when order was placed."""


class OrderPage(BaseModel):
    """Response from GET /portfolio/orders."""

    model_config = ConfigDict(frozen=True)

    orders: list[Order]
    """List of orders matching the query."""


class CancelOrderResponse(BaseModel):
    """Response from DELETE /portfolio/orders/{id}."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    """ID of the canceled order."""

    status: str = Field(validation_alias=AliasChoices("status", "order_status"))
    """New status (typically 'canceled')."""

    reduced_by: int | None = None
    """Number of contracts that were canceled (may be absent)."""
