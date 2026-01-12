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

    updated_ts: int | None = None
    """Unix timestamp (seconds) when the balance was last updated (may be absent)."""


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
    """Total contracts traded (may be absent)."""

    total_traded_dollars: str | None = None
    """Total traded notional in dollars (fixed-point string, may be absent)."""

    resting_orders_count: int | None = None
    """Count of currently resting orders (may be absent)."""

    last_updated_ts: str | None = None
    """RFC3339 timestamp of last position update (may be absent)."""


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

    ticker: str
    """Market ticker symbol."""

    market_ticker: str | None = None
    """Legacy field name for ticker (may be absent)."""

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

    user_id: str | None = None
    """Unique user identifier (may be absent in some responses)."""

    client_order_id: str | None = None
    """Client-specified identifier for this order (may be absent)."""

    ticker: str
    """Market ticker symbol."""

    status: str
    """Order status: 'resting', 'canceled', 'executed', etc."""

    type: str | None = None
    """Order type: 'limit' or 'market' (may be absent)."""

    side: str | None = None
    """Position side: 'yes' or 'no'."""

    action: str | None = None
    """Order action: 'buy' or 'sell'."""

    yes_price: int | None = None
    """YES limit price in cents (0-100)."""

    no_price: int | None = None
    """NO limit price in cents (0-100)."""

    yes_price_dollars: str | None = None
    """YES limit price in fixed-point dollars (may be absent)."""

    no_price_dollars: str | None = None
    """NO limit price in fixed-point dollars (may be absent)."""

    count: int | None = None
    """Number of contracts (remaining or total)."""

    initial_count: int | None = None
    """Original order size before fills/amendments (may be absent)."""

    fill_count: int | None = None
    """Number of contracts filled so far (may be absent)."""

    remaining_count: int | None = None
    """Number of contracts still resting (may be absent)."""

    taker_fees: int | None = None
    """Fees paid on filled taker contracts, in cents (may be absent)."""

    maker_fees: int | None = None
    """Fees paid on filled maker contracts, in cents (may be absent)."""

    taker_fill_cost: int | None = None
    """Cost of filled taker orders in cents (may be absent)."""

    maker_fill_cost: int | None = None
    """Cost of filled maker orders in cents (may be absent)."""

    taker_fill_cost_dollars: str | None = None
    """Cost of filled taker orders in fixed-point dollars (may be absent)."""

    maker_fill_cost_dollars: str | None = None
    """Cost of filled maker orders in fixed-point dollars (may be absent)."""

    taker_fees_dollars: str | None = None
    """Fees paid on filled taker contracts, in fixed-point dollars (may be absent)."""

    maker_fees_dollars: str | None = None
    """Fees paid on filled maker contracts, in fixed-point dollars (may be absent)."""

    queue_position: int | None = None
    """Deprecated queue position (may be absent; always 0 per OpenAPI)."""

    created_time: str | None = None
    """ISO timestamp when the order was created (may be absent)."""

    expiration_time: str | None = None
    """ISO timestamp when the order expires (may be absent)."""

    last_update_time: str | None = None
    """ISO timestamp of the last order update (may be absent)."""

    self_trade_prevention_type: str | None = None
    """Self-trade prevention mode (may be absent)."""

    order_group_id: str | None = None
    """Order group identifier (may be absent)."""

    cancel_order_on_pause: bool | None = None
    """If true, order is canceled when trading is paused (may be absent)."""


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
