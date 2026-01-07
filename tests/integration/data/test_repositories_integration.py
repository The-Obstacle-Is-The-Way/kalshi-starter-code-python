from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from kalshi_research.data import DatabaseManager
from kalshi_research.data.models import Event, Market, PriceSnapshot, Settlement
from kalshi_research.data.repositories import (
    EventRepository,
    MarketRepository,
    PriceRepository,
    SettlementRepository,
)

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_repositories_crud_lifecycle(tmp_path) -> None:
    db_path = tmp_path / "kalshi_repo.db"
    db = DatabaseManager(db_path)
    try:
        await db.create_tables()
        now = datetime.now(UTC)

        async with db.session_factory() as session:
            event_repo = EventRepository(session)
            market_repo = MarketRepository(session)
            price_repo = PriceRepository(session)
            settlement_repo = SettlementRepository(session)

            await event_repo.upsert(Event(ticker="EVT1", series_ticker="S1", title="Event 1"))
            await event_repo.commit()
            assert await event_repo.get("EVT1") is not None

            market = Market(
                ticker="MKT1",
                event_ticker="EVT1",
                title="Market 1",
                status="active",
                open_time=now - timedelta(days=1),
                close_time=now + timedelta(days=1),
                expiration_time=now + timedelta(days=2),
            )
            await market_repo.upsert(market)
            await market_repo.commit()
            assert len(await market_repo.get_by_event("EVT1")) == 1

            snapshot = PriceSnapshot(
                ticker="MKT1",
                snapshot_time=now,
                yes_bid=45,
                yes_ask=47,
                no_bid=53,
                no_ask=55,
                last_price=46,
                volume=100,
                volume_24h=100,
                open_interest=50,
                liquidity=1000,
            )
            await price_repo.add(snapshot)
            await price_repo.commit()
            latest = await price_repo.get_latest("MKT1")
            assert latest is not None
            assert latest.ticker == "MKT1"

            settlement = Settlement(
                ticker="MKT1",
                event_ticker="EVT1",
                settled_at=now,
                result="yes",
            )
            await settlement_repo.add(settlement)
            await settlement_repo.commit()
            assert len(await settlement_repo.get_by_event("EVT1")) == 1

            await market_repo.upsert(
                Market(
                    ticker="MKT1",
                    event_ticker="EVT1",
                    title="Market 1 (updated)",
                    status="active",
                    open_time=now - timedelta(days=2),
                    close_time=now + timedelta(days=2),
                    expiration_time=now + timedelta(days=3),
                )
            )
            await market_repo.commit()
            updated = await market_repo.get("MKT1")
            assert updated is not None
            assert updated.title == "Market 1 (updated)"
    finally:
        await db.close()
