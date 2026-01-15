"""Order group models for the Kalshi API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OrderGroup(BaseModel):
    """Order group summary as returned by `GET /portfolio/order_groups`."""

    model_config = ConfigDict(frozen=True)

    id: str
    is_auto_cancel_enabled: bool


class OrderGroupsResponse(BaseModel):
    """Response schema for `GET /portfolio/order_groups`."""

    model_config = ConfigDict(frozen=True)

    order_groups: list[OrderGroup] = Field(default_factory=list)


class OrderGroupDetailResponse(BaseModel):
    """Response schema for `GET /portfolio/order_groups/{order_group_id}`."""

    model_config = ConfigDict(frozen=True)

    is_auto_cancel_enabled: bool
    orders: list[str] = Field(default_factory=list)


class CreateOrderGroupResponse(BaseModel):
    """Response schema for `POST /portfolio/order_groups/create`."""

    model_config = ConfigDict(frozen=True)

    order_group_id: str


class EmptyResponse(BaseModel):
    """Empty response schema used by some portfolio write endpoints."""

    model_config = ConfigDict(frozen=True)
