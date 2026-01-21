"""Pydantic models for Kalshi Portfolio API responses.

This module re-exports all portfolio models from their focused submodules
to preserve backwards-compatible imports:

    from kalshi_research.api.models.portfolio import (
        PortfolioBalance, PortfolioPosition, Fill, FillPage,
        Settlement, SettlementPage, Order, OrderPage, ...
    )
"""

from __future__ import annotations

# Re-export all models from focused submodules
from kalshi_research.api.models._balance import PortfolioBalance
from kalshi_research.api.models._fill import Fill, FillPage
from kalshi_research.api.models._order import (
    BatchCancelOrdersIndividualResponse,
    BatchCancelOrdersResponse,
    BatchCreateOrdersIndividualResponse,
    BatchCreateOrdersResponse,
    CancelOrderResponse,
    DecreaseOrderResponse,
    GetOrderQueuePositionResponse,
    GetOrderQueuePositionsResponse,
    GetOrderResponse,
    GetPortfolioRestingOrderTotalValueResponse,
    Order,
    OrderPage,
    OrderQueuePosition,
)
from kalshi_research.api.models._position import PortfolioPosition
from kalshi_research.api.models._settlement import Settlement, SettlementPage

__all__ = [
    "BatchCancelOrdersIndividualResponse",
    "BatchCancelOrdersResponse",
    "BatchCreateOrdersIndividualResponse",
    "BatchCreateOrdersResponse",
    "CancelOrderResponse",
    "DecreaseOrderResponse",
    "Fill",
    "FillPage",
    "GetOrderQueuePositionResponse",
    "GetOrderQueuePositionsResponse",
    "GetOrderResponse",
    "GetPortfolioRestingOrderTotalValueResponse",
    "Order",
    "OrderPage",
    "OrderQueuePosition",
    "PortfolioBalance",
    "PortfolioPosition",
    "Settlement",
    "SettlementPage",
]
