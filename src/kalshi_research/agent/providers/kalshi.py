"""Kalshi provider adapter for market data and orderbook snapshots."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kalshi_research.api.client import KalshiPublicClient
    from kalshi_research.api.models.market import Market
    from kalshi_research.api.models.orderbook import Orderbook

from ..schemas import MarketInfo, MarketPriceSnapshot


async def fetch_market_info(client: KalshiPublicClient, ticker: str) -> MarketInfo:
    """Fetch market metadata from Kalshi API.

    Args:
        client: Kalshi public client instance
        ticker: Market ticker (e.g., KXBTC-24DEC31-50K)

    Returns:
        MarketInfo schema with market metadata

    Raises:
        httpx.HTTPStatusError: If ticker not found or API error
    """
    market: Market = await client.get_market(ticker=ticker)

    return MarketInfo(
        ticker=market.ticker,
        event_ticker=market.event_ticker,
        series_ticker=market.series_ticker,
        title=market.title,
        subtitle=market.subtitle or "",
        status=market.status.value if hasattr(market.status, "value") else str(market.status),
        open_time=market.open_time,
        close_time=market.close_time,
        expiration_time=market.expiration_time,
        settlement_ts=market.settlement_ts,
    )


async def fetch_price_snapshot(client: KalshiPublicClient, ticker: str) -> MarketPriceSnapshot:
    """Fetch current orderbook and derive price snapshot.

    Args:
        client: Kalshi public client instance
        ticker: Market ticker

    Returns:
        MarketPriceSnapshot with current prices and volumes

    Raises:
        httpx.HTTPStatusError: If ticker not found or API error
    """
    orderbook: Orderbook = await client.get_orderbook(ticker=ticker)

    best_yes_bid = orderbook.best_yes_bid
    best_no_bid = orderbook.best_no_bid

    # Get top of book prices. Kalshi's orderbook endpoint is bid-only, so asks are implied.
    yes_bid = best_yes_bid if best_yes_bid is not None else 0
    no_bid = best_no_bid if best_no_bid is not None else 0
    yes_ask = 100 - no_bid if best_no_bid is not None else 100
    no_ask = 100 - yes_bid if best_yes_bid is not None else 100

    # Calculate midpoint probability (yes side, 0..1)
    yes_mid_cents = (yes_bid + yes_ask) / 2
    midpoint_prob = yes_mid_cents / 100.0

    # Calculate spread (in cents)
    spread_cents = yes_ask - yes_bid

    # Get volume and OI (requires fetching market object)
    market: Market = await client.get_market(ticker=ticker)

    return MarketPriceSnapshot(
        yes_bid_cents=yes_bid,
        yes_ask_cents=yes_ask,
        no_bid_cents=no_bid,
        no_ask_cents=no_ask,
        last_price_cents=market.last_price_cents,
        volume_24h=market.volume_24h or 0,
        open_interest=market.open_interest or 0,
        midpoint_prob=midpoint_prob,
        spread_cents=spread_cents,
        captured_at=datetime.now(UTC),
    )
