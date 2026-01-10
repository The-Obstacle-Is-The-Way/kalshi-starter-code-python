"""
Data model tests - use REAL SQLAlchemy objects with in-memory SQLite.

These tests verify ORM models and their relationships work correctly.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from kalshi_research.data.models import (
    Base,
    Event,
    Market,
    PriceSnapshot,
    Settlement,
)


@pytest.fixture
def db_session() -> Session:
    """Create an in-memory SQLite database session."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


class TestEventModel:
    """Test Event ORM model."""

    def test_event_creation(self, db_session: Session) -> None:
        """Event can be created and persisted."""
        event = Event(
            ticker="KXBTC-25JAN",
            series_ticker="KXBTC",
            title="Bitcoin Price January 2025",
            category="Crypto",
        )
        db_session.add(event)
        db_session.commit()

        fetched = db_session.get(Event, "KXBTC-25JAN")
        assert fetched is not None
        assert fetched.ticker == "KXBTC-25JAN"
        assert fetched.title == "Bitcoin Price January 2025"

    def test_event_timestamps_auto_set(self, db_session: Session) -> None:
        """created_at and updated_at are automatically set."""
        event = Event(
            ticker="TEST-EVT",
            series_ticker="TEST",
            title="Test Event",
        )
        db_session.add(event)
        db_session.commit()

        fetched = db_session.get(Event, "TEST-EVT")
        assert fetched is not None
        assert fetched.created_at is not None
        assert fetched.updated_at is not None


class TestMarketModel:
    """Test Market ORM model."""

    def test_market_creation_with_event(self, db_session: Session) -> None:
        """Market requires an event (foreign key)."""
        event = Event(
            ticker="KXBTC-25JAN",
            series_ticker="KXBTC",
            title="Bitcoin Price",
        )
        db_session.add(event)
        db_session.flush()

        market = Market(
            ticker="KXBTC-25JAN-T100000",
            event_ticker="KXBTC-25JAN",
            title="Bitcoin above $100,000?",
            status="active",
            open_time=datetime(2024, 1, 1, tzinfo=UTC),
            close_time=datetime(2025, 1, 25, tzinfo=UTC),
            expiration_time=datetime(2025, 1, 26, tzinfo=UTC),
        )
        db_session.add(market)
        db_session.commit()

        fetched = db_session.get(Market, "KXBTC-25JAN-T100000")
        assert fetched is not None
        assert fetched.event_ticker == "KXBTC-25JAN"
        assert fetched.status == "active"

    def test_market_event_relationship(self, db_session: Session) -> None:
        """Market.event relationship loads the parent event."""
        event = Event(
            ticker="EVT1",
            series_ticker="S1",
            title="Event 1",
        )
        market = Market(
            ticker="MKT1",
            event_ticker="EVT1",
            title="Market 1",
            status="active",
            open_time=datetime(2024, 1, 1, tzinfo=UTC),
            close_time=datetime(2025, 1, 1, tzinfo=UTC),
            expiration_time=datetime(2025, 1, 2, tzinfo=UTC),
        )
        db_session.add(event)
        db_session.add(market)
        db_session.commit()

        fetched = db_session.get(Market, "MKT1")
        assert fetched is not None
        assert fetched.event is not None
        assert fetched.event.ticker == "EVT1"


class TestPriceSnapshotModel:
    """Test PriceSnapshot ORM model."""

    def test_snapshot_creation(self, db_session: Session) -> None:
        """PriceSnapshot can be created with market foreign key."""
        event = Event(ticker="EVT", series_ticker="S", title="Event")
        market = Market(
            ticker="MKT",
            event_ticker="EVT",
            title="Market",
            status="active",
            open_time=datetime(2024, 1, 1, tzinfo=UTC),
            close_time=datetime(2025, 1, 1, tzinfo=UTC),
            expiration_time=datetime(2025, 1, 2, tzinfo=UTC),
        )
        db_session.add_all([event, market])
        db_session.flush()

        snapshot = PriceSnapshot(
            ticker="MKT",
            snapshot_time=datetime.now(UTC),
            yes_bid=45,
            yes_ask=47,
            no_bid=53,
            no_ask=55,
            volume=10000,
            volume_24h=500,
            open_interest=5000,
        )
        db_session.add(snapshot)
        db_session.commit()

        assert snapshot.id is not None

    def test_snapshot_computed_properties(self, db_session: Session) -> None:
        """PriceSnapshot computed properties return correct values."""
        event = Event(ticker="EVT2", series_ticker="S", title="Event")
        market = Market(
            ticker="MKT2",
            event_ticker="EVT2",
            title="Market",
            status="active",
            open_time=datetime(2024, 1, 1, tzinfo=UTC),
            close_time=datetime(2025, 1, 1, tzinfo=UTC),
            expiration_time=datetime(2025, 1, 2, tzinfo=UTC),
        )
        snapshot = PriceSnapshot(
            ticker="MKT2",
            snapshot_time=datetime.now(UTC),
            yes_bid=45,
            yes_ask=47,
            no_bid=53,
            no_ask=55,
            volume=10000,
            volume_24h=500,
            open_interest=5000,
        )
        db_session.add_all([event, market, snapshot])
        db_session.commit()

        # Midpoint = (45 + 47) / 2 = 46
        assert snapshot.midpoint == 46.0
        # Spread = 47 - 45 = 2
        assert snapshot.spread == 2
        # Implied probability = 46 / 100 = 0.46
        assert snapshot.implied_probability == 0.46

    def test_market_snapshots_relationship(self, db_session: Session) -> None:
        """Market.price_snapshots relationship loads all snapshots."""
        event = Event(ticker="EVT3", series_ticker="S", title="Event")
        market = Market(
            ticker="MKT3",
            event_ticker="EVT3",
            title="Market",
            status="active",
            open_time=datetime(2024, 1, 1, tzinfo=UTC),
            close_time=datetime(2025, 1, 1, tzinfo=UTC),
            expiration_time=datetime(2025, 1, 2, tzinfo=UTC),
        )
        db_session.add_all([event, market])
        db_session.flush()

        # Add multiple snapshots
        for i in range(3):
            snapshot = PriceSnapshot(
                ticker="MKT3",
                snapshot_time=datetime(2024, 6, 1, i, 0, 0, tzinfo=UTC),
                yes_bid=45 + i,
                yes_ask=47 + i,
                no_bid=53 - i,
                no_ask=55 - i,
                volume=10000,
                volume_24h=500,
                open_interest=5000,
            )
            db_session.add(snapshot)
        db_session.commit()

        fetched = db_session.get(Market, "MKT3")
        assert fetched is not None
        assert len(fetched.price_snapshots) == 3


class TestSettlementModel:
    """Test Settlement ORM model."""

    def test_settlement_creation(self, db_session: Session) -> None:
        """Settlement can be created for a resolved market."""
        event = Event(ticker="EVT4", series_ticker="S", title="Event")
        market = Market(
            ticker="MKT4",
            event_ticker="EVT4",
            title="Market",
            status="finalized",
            result="yes",
            open_time=datetime(2024, 1, 1, tzinfo=UTC),
            close_time=datetime(2024, 6, 1, tzinfo=UTC),
            expiration_time=datetime(2024, 6, 2, tzinfo=UTC),
        )
        db_session.add_all([event, market])
        db_session.flush()

        settlement = Settlement(
            ticker="MKT4",
            event_ticker="EVT4",
            settled_at=datetime(2024, 6, 2, 12, 0, 0, tzinfo=UTC),
            result="yes",
            final_yes_price=100,
            final_no_price=0,
            yes_payout=100,
            no_payout=0,
        )
        db_session.add(settlement)
        db_session.commit()

        fetched = db_session.get(Settlement, "MKT4")
        assert fetched is not None
        assert fetched.result == "yes"
        assert fetched.yes_payout == 100

    def test_market_settlement_relationship(self, db_session: Session) -> None:
        """Market.settlement relationship loads the settlement."""
        event = Event(ticker="EVT5", series_ticker="S", title="Event")
        market = Market(
            ticker="MKT5",
            event_ticker="EVT5",
            title="Market",
            status="finalized",
            open_time=datetime(2024, 1, 1, tzinfo=UTC),
            close_time=datetime(2024, 6, 1, tzinfo=UTC),
            expiration_time=datetime(2024, 6, 2, tzinfo=UTC),
        )
        settlement = Settlement(
            ticker="MKT5",
            event_ticker="EVT5",
            settled_at=datetime.now(UTC),
            result="no",
        )
        db_session.add_all([event, market, settlement])
        db_session.commit()

        fetched = db_session.get(Market, "MKT5")
        assert fetched is not None
        assert fetched.settlement is not None
        assert fetched.settlement.result == "no"
