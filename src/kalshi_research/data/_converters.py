"""Conversion helpers for API models to database models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kalshi_research.data.models import Event as DBEvent
from kalshi_research.data.models import Market as DBMarket
from kalshi_research.data.models import PriceSnapshot
from kalshi_research.data.models import Settlement as DBSettlement

if TYPE_CHECKING:
    from datetime import datetime

    from kalshi_research.api.models.event import Event as APIEvent
    from kalshi_research.api.models.market import Market as APIMarket


def api_event_to_db(api_event: APIEvent) -> DBEvent:
    """Convert API event to database model."""
    return DBEvent(
        ticker=api_event.event_ticker,
        series_ticker=api_event.series_ticker,
        title=api_event.title,
        status=None,  # API doesn't return status for events list
        category=api_event.category,
        mutually_exclusive=False,  # API doesn't return this
    )


def api_market_to_db(api_market: APIMarket) -> DBMarket:
    """Convert API market to database model."""
    return DBMarket(
        ticker=api_market.ticker,
        event_ticker=api_market.event_ticker,
        series_ticker=api_market.series_ticker,
        title=api_market.title,
        subtitle=api_market.subtitle,
        status=api_market.status.value,
        result=api_market.result,
        open_time=api_market.open_time,
        close_time=api_market.close_time,
        expiration_time=api_market.expiration_time,
        category=None,  # Denormalized from event
        subcategory=None,
    )


def api_market_to_snapshot(api_market: APIMarket, snapshot_time: datetime) -> PriceSnapshot:
    """Convert API market to price snapshot.

    Uses computed properties derived from Kalshi `*_dollars` fields (SSOT).
    Database stores cents (integers) for precision - avoids floating-point rounding issues.
    """
    yes_bid = api_market.yes_bid_cents
    yes_ask = api_market.yes_ask_cents
    no_bid = api_market.no_bid_cents
    no_ask = api_market.no_ask_cents
    if yes_bid is None or yes_ask is None or no_bid is None or no_ask is None:
        raise ValueError(
            f"Market {api_market.ticker} missing dollar quote fields; "
            "expected `*_dollars` prices to be present."
        )
    return PriceSnapshot(
        ticker=api_market.ticker,
        snapshot_time=snapshot_time,
        yes_bid=yes_bid,
        yes_ask=yes_ask,
        no_bid=no_bid,
        no_ask=no_ask,
        last_price=api_market.last_price_cents,
        volume=api_market.volume,
        volume_24h=api_market.volume_24h,
        open_interest=api_market.open_interest,
    )


def api_market_to_settlement(api_market: APIMarket) -> DBSettlement | None:
    """Convert a settled API market to a settlement row.

    Notes:
        Prefer `settlement_ts` (added Dec 19, 2025) when available. Fall back to
        `expiration_time` for historical data or older synced markets.
    """
    if not api_market.result:
        return None

    settled_at = api_market.settlement_ts or api_market.expiration_time
    return DBSettlement(
        ticker=api_market.ticker,
        event_ticker=api_market.event_ticker,
        settled_at=settled_at,
        result=api_market.result,
    )
