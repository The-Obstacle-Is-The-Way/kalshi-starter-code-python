"""
Repository tests - use REAL SQLAlchemy objects with in-memory SQLite.

These tests verify repository methods work correctly against a real database.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from kalshi_research.data.models import Base, Event, Market, PriceSnapshot, Settlement
from kalshi_research.data.repositories import (
    EventRepository,
    MarketRepository,
    PriceRepository,
    SettlementRepository,
)


@pytest_asyncio.fixture
async def async_session() -> AsyncSession:
    """Create an async in-memory SQLite database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def seeded_session(async_session: AsyncSession) -> AsyncSession:
    """Session with pre-seeded test data."""
    # Create events
    events = [
        Event(ticker="EVT1", series_ticker="S1", title="Event 1", category="Crypto"),
        Event(ticker="EVT2", series_ticker="S1", title="Event 2", category="Sports"),
        Event(ticker="EVT3", series_ticker="S2", title="Event 3", category="Crypto"),
    ]
    async_session.add_all(events)
    await async_session.flush()

    # Create markets
    now = datetime.now(UTC)
    markets = [
        Market(
            ticker="MKT1",
            event_ticker="EVT1",
            title="Market 1",
            status="active",
            open_time=now - timedelta(days=30),
            close_time=now + timedelta(days=30),
            expiration_time=now + timedelta(days=31),
        ),
        Market(
            ticker="MKT2",
            event_ticker="EVT1",
            title="Market 2",
            status="active",
            open_time=now - timedelta(days=30),
            close_time=now + timedelta(days=5),
            expiration_time=now + timedelta(days=6),
        ),
        Market(
            ticker="MKT3",
            event_ticker="EVT2",
            title="Market 3",
            status="closed",
            open_time=now - timedelta(days=60),
            close_time=now - timedelta(days=1),
            expiration_time=now,
        ),
    ]
    async_session.add_all(markets)
    await async_session.flush()

    # Create snapshots
    for market in markets[:2]:  # Only for active markets
        for i in range(5):
            snapshot = PriceSnapshot(
                ticker=market.ticker,
                snapshot_time=now - timedelta(hours=i),
                yes_bid=45 + i,
                yes_ask=47 + i,
                no_bid=53 - i,
                no_ask=55 - i,
                volume=10000 + i * 100,
                volume_24h=500,
                open_interest=5000,
                liquidity=1000,
            )
            async_session.add(snapshot)

    await async_session.commit()
    return async_session


class TestEventRepository:
    """Test EventRepository methods."""

    @pytest.mark.asyncio
    async def test_add_and_get(self, async_session: AsyncSession) -> None:
        """Can add and retrieve an event."""
        repo = EventRepository(async_session)
        event = Event(
            ticker="TEST-EVT",
            series_ticker="TEST",
            title="Test Event",
        )
        await repo.add(event)
        await repo.commit()

        fetched = await repo.get("TEST-EVT")
        assert fetched is not None
        assert fetched.title == "Test Event"

    @pytest.mark.asyncio
    async def test_get_by_series(self, seeded_session: AsyncSession) -> None:
        """Can filter events by series."""
        repo = EventRepository(seeded_session)
        events = await repo.get_by_series("S1")

        assert len(events) == 2
        assert all(e.series_ticker == "S1" for e in events)

    @pytest.mark.asyncio
    async def test_get_by_category(self, seeded_session: AsyncSession) -> None:
        """Can filter events by category."""
        repo = EventRepository(seeded_session)
        events = await repo.get_by_category("Crypto")

        assert len(events) == 2
        assert all(e.category == "Crypto" for e in events)

    @pytest.mark.asyncio
    async def test_upsert_new(self, async_session: AsyncSession) -> None:
        """Upsert creates new event if not exists."""
        repo = EventRepository(async_session)
        event = Event(
            ticker="NEW-EVT",
            series_ticker="S",
            title="New Event",
            mutually_exclusive=False,
        )

        await repo.upsert(event)
        await repo.commit()

        fetched = await repo.get("NEW-EVT")
        assert fetched is not None
        assert fetched.ticker == "NEW-EVT"

    @pytest.mark.asyncio
    async def test_upsert_existing(self, seeded_session: AsyncSession) -> None:
        """Upsert updates existing event."""
        repo = EventRepository(seeded_session)
        updated = Event(
            ticker="EVT1",
            series_ticker="S1",
            title="Updated Title",
            mutually_exclusive=False,
        )

        await repo.upsert(updated)
        await repo.commit()

        fetched = await repo.get("EVT1")
        assert fetched is not None
        assert fetched.title == "Updated Title"


class TestMarketRepository:
    """Test MarketRepository methods."""

    @pytest.mark.asyncio
    async def test_get_by_status(self, seeded_session: AsyncSession) -> None:
        """Can filter markets by status."""
        repo = MarketRepository(seeded_session)

        active = await repo.get_by_status("active")
        assert len(active) == 2

        closed = await repo.get_by_status("closed")
        assert len(closed) == 1

    @pytest.mark.asyncio
    async def test_get_by_event(self, seeded_session: AsyncSession) -> None:
        """Can filter markets by event."""
        repo = MarketRepository(seeded_session)
        markets = await repo.get_by_event("EVT1")

        assert len(markets) == 2
        assert all(m.event_ticker == "EVT1" for m in markets)

    @pytest.mark.asyncio
    async def test_get_active(self, seeded_session: AsyncSession) -> None:
        """Can get all active markets."""
        repo = MarketRepository(seeded_session)
        active = await repo.get_active()

        assert len(active) == 2
        assert all(m.status == "active" for m in active)

    @pytest.mark.asyncio
    async def test_get_expiring_before(self, seeded_session: AsyncSession) -> None:
        """Can find markets expiring before a date."""
        repo = MarketRepository(seeded_session)
        now = datetime.now(UTC)
        expiring = await repo.get_expiring_before(now + timedelta(days=10))

        # MKT2 expires in 6 days
        assert len(expiring) == 1
        assert expiring[0].ticker == "MKT2"

    @pytest.mark.asyncio
    async def test_count_by_status(self, seeded_session: AsyncSession) -> None:
        """Can count markets by status."""
        repo = MarketRepository(seeded_session)
        counts = await repo.count_by_status()

        assert counts["active"] == 2
        assert counts["closed"] == 1


class TestPriceRepository:
    """Test PriceRepository methods."""

    @pytest.mark.asyncio
    async def test_get_for_market(self, seeded_session: AsyncSession) -> None:
        """Can get snapshots for a market."""
        repo = PriceRepository(seeded_session)
        snapshots = await repo.get_for_market("MKT1")

        assert len(snapshots) == 5

    @pytest.mark.asyncio
    async def test_get_for_market_with_time_range(self, seeded_session: AsyncSession) -> None:
        """Can filter snapshots by time range."""
        repo = PriceRepository(seeded_session)
        now = datetime.now(UTC)

        snapshots = await repo.get_for_market(
            "MKT1",
            start_time=now - timedelta(hours=2),
            end_time=now,
        )

        # Should get snapshots from last 2 hours (including the boundaries)
        assert len(snapshots) <= 3

    @pytest.mark.asyncio
    async def test_get_latest(self, seeded_session: AsyncSession) -> None:
        """Can get the most recent snapshot."""
        repo = PriceRepository(seeded_session)
        latest = await repo.get_latest("MKT1")

        assert latest is not None
        # Most recent snapshot has i=0, so yes_bid=45
        assert latest.yes_bid == 45

    @pytest.mark.asyncio
    async def test_get_latest_batch(self, seeded_session: AsyncSession) -> None:
        """Can get latest snapshots for multiple markets at once."""
        repo = PriceRepository(seeded_session)
        latest = await repo.get_latest_batch(["MKT1", "MKT2"])

        assert len(latest) == 2
        assert "MKT1" in latest
        assert "MKT2" in latest

    @pytest.mark.asyncio
    async def test_count_for_market(self, seeded_session: AsyncSession) -> None:
        """Can count snapshots for a market."""
        repo = PriceRepository(seeded_session)
        count = await repo.count_for_market("MKT1")

        assert count == 5

    @pytest.mark.asyncio
    async def test_delete_older_than(self, seeded_session: AsyncSession) -> None:
        """Can delete old snapshots."""
        repo = PriceRepository(seeded_session)
        now = datetime.now(UTC)

        # Delete snapshots older than 3 hours
        deleted = await repo.delete_older_than(now - timedelta(hours=3))
        await repo.commit()

        # Should have deleted some snapshots
        assert deleted > 0

        # Verify remaining snapshots are newer
        remaining = await repo.count_for_market("MKT1")
        assert remaining < 5


class TestSettlementRepository:
    """Test SettlementRepository methods."""

    @pytest_asyncio.fixture
    async def settlement_session(self, async_session: AsyncSession) -> AsyncSession:
        """Session with settlement data."""
        now = datetime.now(UTC)
        settlements = [
            Settlement(
                ticker="MKT1",
                event_ticker="EVT1",
                result="yes",
                settled_at=now - timedelta(days=1),
            ),
            Settlement(
                ticker="MKT2",
                event_ticker="EVT1",
                result="no",
                settled_at=now - timedelta(days=2),
            ),
            Settlement(
                ticker="MKT3",
                event_ticker="EVT2",
                result="yes",
                settled_at=now - timedelta(hours=6),
            ),
        ]
        async_session.add_all(settlements)
        await async_session.commit()
        return async_session

    @pytest.mark.asyncio
    async def test_get_by_event(self, settlement_session: AsyncSession) -> None:
        """Can filter settlements by event."""
        repo = SettlementRepository(settlement_session)
        settlements = await repo.get_by_event("EVT1")

        assert len(settlements) == 2
        assert all(s.event_ticker == "EVT1" for s in settlements)

    @pytest.mark.asyncio
    async def test_get_by_result(self, settlement_session: AsyncSession) -> None:
        """Can filter settlements by result."""
        repo = SettlementRepository(settlement_session)

        yes_settlements = await repo.get_by_result("yes")
        assert len(yes_settlements) == 2

        no_settlements = await repo.get_by_result("no")
        assert len(no_settlements) == 1

    @pytest.mark.asyncio
    async def test_get_settled_after(self, settlement_session: AsyncSession) -> None:
        """Can filter settlements by settlement time."""
        repo = SettlementRepository(settlement_session)
        now = datetime.now(UTC)

        recent = await repo.get_settled_after(now - timedelta(hours=12))
        assert len(recent) == 1
        assert recent[0].ticker == "MKT3"

    @pytest.mark.asyncio
    async def test_count_by_result(self, settlement_session: AsyncSession) -> None:
        """Can count settlements by result."""
        repo = SettlementRepository(settlement_session)
        counts = await repo.count_by_result()

        assert counts["yes"] == 2
        assert counts["no"] == 1
