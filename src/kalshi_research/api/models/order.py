"""Order models."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class OrderSide(str, Enum):
    """Side of the order."""

    YES = "yes"
    NO = "no"


class OrderAction(str, Enum):
    """Action of the order."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Type of the order."""

    LIMIT = "limit"
    MARKET = "market"


class OrderStatus(str, Enum):
    """Status of the order."""

    RESTING = "resting"
    CANCELED = "canceled"
    EXECUTED = "executed"
    PENDING = "pending"  # Deprecated but might still appear? Docs say removed.


class CreateOrderRequest(BaseModel):
    """Request to create an order."""

    ticker: str
    action: OrderAction
    side: OrderSide
    count: int = Field(gt=0, description="Number of contracts")
    type: OrderType = OrderType.LIMIT
    yes_price: int | None = Field(
        None, 
        ge=1, 
        le=99, 
        description="Limit price in CENTS (1-99). Required for limit orders."
    )
    no_price: int | None = Field(
        None, 
        ge=1, 
        le=99, 
        description="Implicit no price (100 - yes_price). Optional."
    )
    client_order_id: str
    expiration_ts: int | None = None
    sell_position_floor: int | None = None
    buy_max_cost: int | None = None


class OrderResponse(BaseModel):
    """Response from create order."""

    order_id: str
    order_status: str


class Order(BaseModel):
    """Order details."""

    order_id: str
    client_order_id: str
    ticker: str
    side: OrderSide
    action: OrderAction
    type: OrderType
    yes_price: int
    count: int
    status: OrderStatus
    created_time: str
    expiration_time: str | None = None
    close_cancel_count: int | None = None
    # Add other fields as needed
