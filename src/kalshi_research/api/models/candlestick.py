"""Candlestick data models for Kalshi API."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class CandleSide(BaseModel):
    """Bid/ask series for a candlestick."""

    model_config = ConfigDict(frozen=True)

    open: int | None = None
    high: int | None = None
    low: int | None = None
    close: int | None = None

    open_dollars: str | None = None
    high_dollars: str | None = None
    low_dollars: str | None = None
    close_dollars: str | None = None


class CandlePrice(BaseModel):
    """Trade/mark price series for a candlestick."""

    model_config = ConfigDict(frozen=True)

    open: int | None = None
    high: int | None = None
    low: int | None = None
    close: int | None = None

    open_dollars: str | None = None
    high_dollars: str | None = None
    low_dollars: str | None = None
    close_dollars: str | None = None

    mean: int | None = None
    mean_dollars: str | None = None

    min: int | None = None
    max: int | None = None
    previous: int | None = None
    previous_dollars: str | None = None


class Candlestick(BaseModel):
    """
    Candlestick record as returned by the Kalshi API.

    Note: The API uses `end_period_ts` (Unix seconds) and nested objects for `price`, `yes_bid`,
    and `yes_ask`.
    """

    model_config = ConfigDict(frozen=True)

    end_period_ts: int = Field(..., description="Period end timestamp (Unix seconds)")
    open_interest: int = Field(..., ge=0)
    volume: int = Field(..., ge=0)

    price: CandlePrice
    yes_bid: CandleSide
    yes_ask: CandleSide

    @property
    def period_end(self) -> datetime:
        """Period end as datetime (UTC)."""
        return datetime.fromtimestamp(self.end_period_ts, tz=UTC)


class CandlestickResponse(BaseModel):
    """Response from batch candlesticks endpoint."""

    model_config = ConfigDict(frozen=True)

    market_ticker: str
    candlesticks: list[Candlestick]
