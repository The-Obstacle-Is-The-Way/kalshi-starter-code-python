"""Pydantic models for the trade execution safety harness."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kalshi_research.api.config import Environment
from kalshi_research.api.models.order import OrderAction, OrderSide


class TradeChecks(BaseModel):
    """Result of pre-trade safety checks."""

    model_config = ConfigDict(frozen=True)

    passed: bool
    failures: list[str] = Field(default_factory=list)


class TradeAuditEvent(BaseModel):
    """Append-only JSONL record for every trade attempt."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    mode: Literal["dry_run", "live"]
    environment: Environment

    ticker: str
    side: OrderSide
    action: OrderAction
    count: int
    yes_price_cents: int

    max_order_risk_usd: float | None = None
    estimated_order_risk_usd: float | None = None

    client_order_id: str | None = None
    order_id: str | None = None

    checks: TradeChecks
    error: str | None = None
