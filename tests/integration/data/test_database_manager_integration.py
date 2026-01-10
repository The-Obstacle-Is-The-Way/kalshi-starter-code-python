from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError

from kalshi_research.data import DatabaseManager
from kalshi_research.data.models import Event, Market, PriceSnapshot
from kalshi_research.portfolio.models import Position, Trade

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_create_tables_includes_all_models(tmp_path) -> None:
    db_path = tmp_path / "kalshi_test.db"
    db = DatabaseManager(db_path)
    try:
        await db.create_tables()

        async with db.engine.begin() as conn:
            table_names = await conn.run_sync(
                lambda sync_conn: set(inspect(sync_conn).get_table_names())
            )

        # Core data tables
        assert "events" in table_names
        assert "markets" in table_names
        assert "price_snapshots" in table_names
        assert "settlements" in table_names
        # Portfolio tables (share same Base)
        assert "positions" in table_names
        assert "trades" in table_names
        # News/sentiment tables
        assert "tracked_items" in table_names
        assert "news_articles" in table_names
        assert "news_article_markets" in table_names
        assert "news_article_events" in table_names
        assert "news_sentiments" in table_names
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_foreign_keys_enforced(tmp_path) -> None:
    db_path = tmp_path / "kalshi_fk.db"
    db = DatabaseManager(db_path)
    try:
        await db.create_tables()

        now = datetime.now(UTC)
        bad_market = Market(
            ticker="MKT-BAD",
            event_ticker="EVT-DOES-NOT-EXIST",
            title="Bad Market",
            status="active",
            open_time=now - timedelta(days=1),
            close_time=now + timedelta(days=1),
            expiration_time=now + timedelta(days=2),
        )

        async with db.session_factory() as session:
            session.add(bad_market)
            with pytest.raises(IntegrityError):
                await session.commit()
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_concurrent_writes_do_not_deadlock(tmp_path) -> None:
    db_path = tmp_path / "kalshi_concurrent.db"
    db = DatabaseManager(db_path)
    try:
        await db.create_tables()

        now = datetime.now(UTC)
        async with db.session_factory() as session:
            session.add(Event(ticker="EVT1", series_ticker="S1", title="Event 1"))
            session.add(
                Market(
                    ticker="MKT1",
                    event_ticker="EVT1",
                    title="Market 1",
                    status="active",
                    open_time=now - timedelta(days=2),
                    close_time=now + timedelta(days=2),
                    expiration_time=now + timedelta(days=3),
                )
            )
            await session.commit()

        async def _writer(task_id: int) -> None:
            async with db.session_factory() as session:
                for i in range(10):
                    session.add(
                        PriceSnapshot(
                            ticker="MKT1",
                            snapshot_time=now - timedelta(minutes=task_id * 100 + i),
                            yes_bid=45,
                            yes_ask=47,
                            no_bid=53,
                            no_ask=55,
                            last_price=46,
                            volume=1000 + i,
                            volume_24h=100,
                            open_interest=500,
                        )
                    )
                await session.commit()

        await asyncio.gather(_writer(1), _writer(2))

        async with db.session_factory() as session:
            result = await session.execute(select(func.count(PriceSnapshot.id)))
            count = result.scalar_one()

        assert count == 20
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_portfolio_fk_integrity(tmp_path) -> None:
    db_path = tmp_path / "kalshi_portfolio_fk.db"
    db = DatabaseManager(db_path)
    try:
        await db.create_tables()

        now = datetime.now(UTC)
        async with db.session_factory() as session:
            position = Position(
                ticker="TICKER1",
                side="yes",
                quantity=10,
                avg_price_cents=45,
                opened_at=now,
                last_synced=now,
            )
            session.add(position)
            await session.commit()
            await session.refresh(position)

        async with db.session_factory() as session:
            session.add(
                Trade(
                    kalshi_trade_id="trade_1",
                    ticker="TICKER1",
                    side="yes",
                    action="buy",
                    quantity=10,
                    price_cents=45,
                    total_cost_cents=450,
                    fee_cents=0,
                    position_id=position.id,
                    executed_at=now,
                    synced_at=now,
                )
            )
            await session.commit()

        async with db.session_factory() as session:
            session.add(
                Trade(
                    kalshi_trade_id="trade_bad",
                    ticker="TICKER1",
                    side="yes",
                    action="buy",
                    quantity=10,
                    price_cents=45,
                    total_cost_cents=450,
                    fee_cents=0,
                    position_id=999999,
                    executed_at=now,
                    synced_at=now,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
    finally:
        await db.close()
