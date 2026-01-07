from __future__ import annotations

import os
import time

import pytest

from kalshi_research.api.client import KalshiPublicClient
from kalshi_research.api.models.market import MarketFilterStatus


pytestmark = [pytest.mark.integration]


def _require_live_api() -> None:
    if os.getenv("KALSHI_RUN_LIVE_API") != "1":
        pytest.skip("Set KALSHI_RUN_LIVE_API=1 to run live Kalshi API tests")


@pytest.mark.asyncio
async def test_exchange_status_live() -> None:
    _require_live_api()

    async with KalshiPublicClient(timeout=10) as client:
        status = await client.get_exchange_status()

    assert isinstance(status, dict)
    assert isinstance(status.get("exchange_active"), bool)
    assert isinstance(status.get("trading_active"), bool)


@pytest.mark.asyncio
async def test_events_limit_is_capped_to_200_live() -> None:
    """Regression for BUG-011: /events max limit is 200."""
    _require_live_api()

    async with KalshiPublicClient(timeout=10) as client:
        events = await client.get_events(limit=1000)

    assert 0 < len(events) <= 200


@pytest.mark.asyncio
async def test_markets_roundtrip_live() -> None:
    _require_live_api()

    async with KalshiPublicClient(timeout=10) as client:
        markets = await client.get_markets(status=MarketFilterStatus.OPEN, limit=5)
        if not markets:
            pytest.skip("No open markets returned by API")

        market = markets[0]
        market_detail = await client.get_market(market.ticker)

    assert market_detail.ticker == market.ticker
    assert market_detail.event_ticker == market.event_ticker


@pytest.mark.asyncio
async def test_cursor_pagination_markets_live() -> None:
    _require_live_api()

    async with KalshiPublicClient(timeout=10) as client:
        page1, cursor = await client.get_markets_page(status=MarketFilterStatus.OPEN, limit=1)
        if not page1:
            pytest.skip("No open markets returned by API")
        if cursor is None:
            pytest.skip("API did not return a cursor for /markets pagination")

        page2, _ = await client.get_markets_page(
            status=MarketFilterStatus.OPEN,
            limit=1,
            cursor=cursor,
        )

    assert len(page1) == 1
    assert len(page2) == 1
    assert page1[0].ticker != page2[0].ticker


@pytest.mark.asyncio
async def test_cursor_pagination_events_live() -> None:
    _require_live_api()

    async with KalshiPublicClient(timeout=10) as client:
        page1, cursor = await client.get_events_page(limit=1)
        if not page1:
            pytest.skip("No events returned by API")
        if cursor is None:
            pytest.skip("API did not return a cursor for /events pagination")

        page2, _ = await client.get_events_page(limit=1, cursor=cursor)

    assert len(page1) == 1
    assert len(page2) == 1
    assert page1[0].event_ticker != page2[0].event_ticker


@pytest.mark.asyncio
async def test_orderbook_trades_candlesticks_live() -> None:
    _require_live_api()

    async with KalshiPublicClient(timeout=10) as client:
        markets = await client.get_markets(status=MarketFilterStatus.OPEN, limit=5)
        if not markets:
            pytest.skip("No open markets returned by API")

        market = markets[0]
        orderbook = await client.get_orderbook(market.ticker, depth=5)
        trades = await client.get_trades(ticker=market.ticker, limit=5)

        end_ts = int(time.time())
        start_ts = end_ts - 24 * 60 * 60
        candles = await client.get_candlesticks(
            market_tickers=[market.ticker],
            start_ts=start_ts,
            end_ts=end_ts,
            period_interval=60,
        )

    assert orderbook.spread is None or 0 <= orderbook.spread <= 100
    assert all(t.ticker == market.ticker for t in trades)
    assert len(candles) == 1
    assert candles[0].market_ticker == market.ticker

