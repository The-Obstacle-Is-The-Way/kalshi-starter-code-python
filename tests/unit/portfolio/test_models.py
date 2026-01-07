"""Unit tests for portfolio database models (Position, Trade)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from kalshi_research.data.models import Base
from kalshi_research.portfolio.models import Position, Trade


@pytest.fixture
async def db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


class TestPositionModel:
    """Tests for Position database model."""

    async def test_create_position(self, db_session: AsyncSession):
        """Test creating a position in the database."""
        position = Position(
            ticker="KXBTC-25JAN10-50000",
            side="yes",
            quantity=100,
            avg_price_cents=4500,
            current_price_cents=5200,
            unrealized_pnl_cents=7000,
            realized_pnl_cents=0,
            opened_at=datetime.now(UTC),
            last_synced=datetime.now(UTC),
        )

        db_session.add(position)
        await db_session.commit()
        await db_session.refresh(position)

        assert position.id is not None
        assert position.ticker == "KXBTC-25JAN10-50000"
        assert position.side == "yes"
        assert position.quantity == 100
        assert position.avg_price_cents == 4500

    async def test_position_with_thesis_link(self, db_session: AsyncSession):
        """Test linking a position to a thesis."""
        position = Position(
            ticker="KXBTC-25JAN10-50000",
            side="yes",
            quantity=100,
            avg_price_cents=4500,
            thesis_id=42,  # Link to thesis
            opened_at=datetime.now(UTC),
            last_synced=datetime.now(UTC),
        )

        db_session.add(position)
        await db_session.commit()
        await db_session.refresh(position)

        assert position.thesis_id == 42

    async def test_position_nullable_fields(self, db_session: AsyncSession):
        """Test that optional fields can be None."""
        position = Position(
            ticker="KXBTC-25JAN10-50000",
            side="yes",
            quantity=100,
            avg_price_cents=4500,
            current_price_cents=None,
            unrealized_pnl_cents=None,
            realized_pnl_cents=0,
            opened_at=datetime.now(UTC),
            last_synced=datetime.now(UTC),
            thesis_id=None,
            closed_at=None,
        )

        db_session.add(position)
        await db_session.commit()
        await db_session.refresh(position)

        assert position.current_price_cents is None
        assert position.unrealized_pnl_cents is None
        assert position.thesis_id is None
        assert position.closed_at is None

    async def test_query_positions_by_ticker(self, db_session: AsyncSession):
        """Test querying positions by ticker."""
        # Create two positions with different tickers
        position1 = Position(
            ticker="KXBTC-25JAN10-50000",
            side="yes",
            quantity=100,
            avg_price_cents=4500,
            opened_at=datetime.now(UTC),
            last_synced=datetime.now(UTC),
        )
        position2 = Position(
            ticker="PRES-24-DEM",
            side="no",
            quantity=50,
            avg_price_cents=5500,
            opened_at=datetime.now(UTC),
            last_synced=datetime.now(UTC),
        )

        db_session.add_all([position1, position2])
        await db_session.commit()

        # Query for specific ticker
        result = await db_session.execute(
            select(Position).where(Position.ticker == "KXBTC-25JAN10-50000")
        )
        found = result.scalar_one()

        assert found.ticker == "KXBTC-25JAN10-50000"
        assert found.quantity == 100


class TestTradeModel:
    """Tests for Trade database model."""

    async def test_create_trade(self, db_session: AsyncSession):
        """Test creating a trade in the database."""
        trade = Trade(
            kalshi_trade_id="trade_12345",
            ticker="KXBTC-25JAN10-50000",
            side="yes",
            action="buy",
            quantity=100,
            price_cents=4500,
            total_cost_cents=450000,
            fee_cents=225,
            executed_at=datetime.now(UTC),
            synced_at=datetime.now(UTC),
        )

        db_session.add(trade)
        await db_session.commit()
        await db_session.refresh(trade)

        assert trade.id is not None
        assert trade.kalshi_trade_id == "trade_12345"
        assert trade.ticker == "KXBTC-25JAN10-50000"
        assert trade.side == "yes"
        assert trade.action == "buy"
        assert trade.quantity == 100
        assert trade.price_cents == 4500
        assert trade.total_cost_cents == 450000
        assert trade.fee_cents == 225

    async def test_trade_with_position_link(self, db_session: AsyncSession):
        """Test linking a trade to a position."""
        # Create position first
        position = Position(
            ticker="KXBTC-25JAN10-50000",
            side="yes",
            quantity=100,
            avg_price_cents=4500,
            opened_at=datetime.now(UTC),
            last_synced=datetime.now(UTC),
        )
        db_session.add(position)
        await db_session.commit()
        await db_session.refresh(position)

        # Create trade linked to position
        trade = Trade(
            kalshi_trade_id="trade_12345",
            ticker="KXBTC-25JAN10-50000",
            side="yes",
            action="buy",
            quantity=100,
            price_cents=4500,
            total_cost_cents=450000,
            fee_cents=225,
            position_id=position.id,
            executed_at=datetime.now(UTC),
            synced_at=datetime.now(UTC),
        )

        db_session.add(trade)
        await db_session.commit()
        await db_session.refresh(trade)

        assert trade.position_id == position.id

    async def test_trade_unique_kalshi_id(self, db_session: AsyncSession):
        """Test that kalshi_trade_id must be unique."""
        trade1 = Trade(
            kalshi_trade_id="trade_12345",
            ticker="KXBTC-25JAN10-50000",
            side="yes",
            action="buy",
            quantity=100,
            price_cents=4500,
            total_cost_cents=450000,
            executed_at=datetime.now(UTC),
            synced_at=datetime.now(UTC),
        )

        trade2 = Trade(
            kalshi_trade_id="trade_12345",  # Same ID
            ticker="PRES-24-DEM",
            side="no",
            action="buy",
            quantity=50,
            price_cents=5500,
            total_cost_cents=275000,
            executed_at=datetime.now(UTC),
            synced_at=datetime.now(UTC),
        )

        db_session.add(trade1)
        await db_session.commit()

        # Should fail on duplicate kalshi_trade_id
        db_session.add(trade2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_query_trades_by_ticker(self, db_session: AsyncSession):
        """Test querying trades by ticker."""
        # Create multiple trades
        trade1 = Trade(
            kalshi_trade_id="trade_1",
            ticker="KXBTC-25JAN10-50000",
            side="yes",
            action="buy",
            quantity=100,
            price_cents=4500,
            total_cost_cents=450000,
            executed_at=datetime.now(UTC),
            synced_at=datetime.now(UTC),
        )
        trade2 = Trade(
            kalshi_trade_id="trade_2",
            ticker="KXBTC-25JAN10-50000",
            side="yes",
            action="sell",
            quantity=50,
            price_cents=5000,
            total_cost_cents=250000,
            executed_at=datetime.now(UTC),
            synced_at=datetime.now(UTC),
        )
        trade3 = Trade(
            kalshi_trade_id="trade_3",
            ticker="PRES-24-DEM",
            side="no",
            action="buy",
            quantity=50,
            price_cents=5500,
            total_cost_cents=275000,
            executed_at=datetime.now(UTC),
            synced_at=datetime.now(UTC),
        )

        db_session.add_all([trade1, trade2, trade3])
        await db_session.commit()

        # Query trades for specific ticker
        result = await db_session.execute(
            select(Trade).where(Trade.ticker == "KXBTC-25JAN10-50000")
        )
        found_trades = result.scalars().all()

        assert len(found_trades) == 2
        assert all(t.ticker == "KXBTC-25JAN10-50000" for t in found_trades)
