from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from kalshi_research.api.models.market import Market, MarketStatus
from kalshi_research.data import DatabaseManager, DataFetcher

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class StubSingleMarketClient:
    def __init__(self, market: Market) -> None:
        self._market = market

    async def get_all_markets(
        self, status: object | None = None, max_pages: int | None = None
    ) -> AsyncIterator[Market]:
        del status, max_pages
        yield self._market


@pytest.mark.asyncio
async def test_concurrent_sync_markets_is_idempotent(tmp_path) -> None:
    """Two concurrent sync_markets runs should not fail with IntegrityError."""
    db_path = tmp_path / "concurrent_sync_markets.db"

    base = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    api_market = Market(
        ticker="TEST-MARKET",
        event_ticker="TEST-EVENT",
        series_ticker=None,
        title="Test Market",
        subtitle="",
        status=MarketStatus.ACTIVE,
        result="",
        yes_bid=None,
        yes_ask=None,
        no_bid=None,
        no_ask=None,
        last_price=None,
        volume=0,
        volume_24h=0,
        open_interest=0,
        open_time=base - timedelta(days=2),
        close_time=base + timedelta(days=2),
        expiration_time=base + timedelta(days=3),
        settlement_ts=None,
        liquidity=None,
    )

    async with DatabaseManager(db_path) as db:
        await db.create_tables()

        async def run_once() -> None:
            async with DataFetcher(db, client=StubSingleMarketClient(api_market)) as fetcher:
                await fetcher.sync_markets(status="open")

        results = await asyncio.gather(run_once(), run_once(), return_exceptions=True)
        assert all(r is None for r in results), results


@pytest.mark.asyncio
async def test_concurrent_sync_settlements_is_idempotent(tmp_path) -> None:
    """Two concurrent sync_settlements runs should not fail with IntegrityError."""
    db_path = tmp_path / "concurrent_sync_settlements.db"

    base = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    expiration_time = base - timedelta(days=1)
    settlement_ts = expiration_time - timedelta(hours=1)

    api_market = Market(
        ticker="TEST-MARKET",
        event_ticker="TEST-EVENT",
        series_ticker=None,
        title="Test Market",
        subtitle="",
        status=MarketStatus.FINALIZED,
        result="yes",
        yes_bid=None,
        yes_ask=None,
        no_bid=None,
        no_ask=None,
        last_price=None,
        volume=0,
        volume_24h=0,
        open_interest=0,
        open_time=base - timedelta(days=3),
        close_time=base - timedelta(days=2),
        expiration_time=expiration_time,
        settlement_ts=settlement_ts,
        liquidity=None,
    )

    async with DatabaseManager(db_path) as db:
        await db.create_tables()

        async def run_once() -> None:
            async with DataFetcher(db, client=StubSingleMarketClient(api_market)) as fetcher:
                await fetcher.sync_settlements()

        results = await asyncio.gather(run_once(), run_once(), return_exceptions=True)
        assert all(r is None for r in results), results
