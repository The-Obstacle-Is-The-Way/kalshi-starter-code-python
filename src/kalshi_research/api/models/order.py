"""Order models."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


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


class CreateOrderRequest(BaseModel):
    """Request to create an order."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    action: OrderAction
    side: OrderSide
    count: int = Field(gt=0, description="Number of contracts")
    type: OrderType = OrderType.LIMIT
    yes_price: int | None = Field(
        None, ge=1, le=99, description="Limit price in CENTS (1-99). Required for limit orders."
    )
    no_price: int | None = Field(
        None, ge=1, le=99, description="Implicit no price (100 - yes_price). Optional."
    )
    yes_price_dollars: str | None = Field(
        None, description="YES price in fixed-point dollars (e.g., '0.5500')."
    )
    no_price_dollars: str | None = Field(
        None, description="NO price in fixed-point dollars (e.g., '0.4500')."
    )
    client_order_id: str | None = None
    expiration_ts: int | None = None
    time_in_force: (
        Literal[
            "fill_or_kill",
            "good_till_canceled",
            "immediate_or_cancel",
        ]
        | None
    ) = None
    sell_position_floor: int | None = None
    buy_max_cost: int | None = None
    post_only: bool | None = None
    reduce_only: bool | None = None
    self_trade_prevention_type: Literal["taker_at_cross", "maker"] | None = None
    order_group_id: str | None = None
    cancel_order_on_pause: bool | None = None

    @model_validator(mode="after")
    def validate_limit_price(self) -> CreateOrderRequest:
        """Ensure limit orders include at least one price field."""
        if self.type != OrderType.LIMIT:
            return self

        has_any_price = any(
            price is not None
            for price in (
                self.yes_price,
                self.no_price,
                self.yes_price_dollars,
                self.no_price_dollars,
            )
        )
        if not has_any_price:
            raise ValueError("Limit orders must provide yes_price/no_price (or *_dollars)")
        return self


class OrderResponse(BaseModel):
    """Response from create order."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    order_status: str = Field(validation_alias=AliasChoices("order_status", "status"))
