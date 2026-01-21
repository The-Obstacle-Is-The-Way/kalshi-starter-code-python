"""Pydantic models for portfolio orders."""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from kalshi_research.api.models.error import ErrorResponse  # noqa: TC001


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


class CancelOrderResponse(BaseModel):
    """Response from DELETE /portfolio/orders/{id}."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    """ID of the canceled order."""

    status: str = Field(validation_alias=AliasChoices("status", "order_status"))
    """New status (typically 'canceled')."""

    reduced_by: int | None = None
    """Number of contracts that were canceled (may be absent)."""


class GetOrderResponse(BaseModel):
    """Response from GET /portfolio/orders/{order_id}."""

    model_config = ConfigDict(frozen=True)

    order: Order
    """The requested order."""


class BatchCreateOrdersIndividualResponse(BaseModel):
    """Per-order result from POST /portfolio/orders/batched."""

    model_config = ConfigDict(frozen=True)

    client_order_id: str | None = None
    order: Order | None = None
    error: ErrorResponse | None = None


class BatchCreateOrdersResponse(BaseModel):
    """Response from POST /portfolio/orders/batched."""

    model_config = ConfigDict(frozen=True)

    orders: list[BatchCreateOrdersIndividualResponse]


class BatchCancelOrdersIndividualResponse(BaseModel):
    """Per-order result from DELETE /portfolio/orders/batched."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    reduced_by: int
    order: Order | None = None
    error: ErrorResponse | None = None


class BatchCancelOrdersResponse(BaseModel):
    """Response from DELETE /portfolio/orders/batched."""

    model_config = ConfigDict(frozen=True)

    orders: list[BatchCancelOrdersIndividualResponse]


class DecreaseOrderResponse(BaseModel):
    """Response from POST /portfolio/orders/{order_id}/decrease."""

    model_config = ConfigDict(frozen=True)

    order: Order


class GetOrderQueuePositionResponse(BaseModel):
    """Response from GET /portfolio/orders/{order_id}/queue_position."""

    model_config = ConfigDict(frozen=True)

    queue_position: int


class OrderQueuePosition(BaseModel):
    """Queue position for a single resting order (OpenAPI OrderQueuePosition)."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    market_ticker: str
    queue_position: int


class GetOrderQueuePositionsResponse(BaseModel):
    """Response from GET /portfolio/orders/queue_positions.

    Note: API returns null/None for queue_positions when there are no positions.
    """

    model_config = ConfigDict(frozen=True)

    queue_positions: list[OrderQueuePosition] | None = None


class GetPortfolioRestingOrderTotalValueResponse(BaseModel):
    """Response from GET /portfolio/summary/total_resting_order_value."""

    model_config = ConfigDict(frozen=True)

    total_resting_order_value: int
