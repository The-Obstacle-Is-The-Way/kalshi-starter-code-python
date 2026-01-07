from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from kalshi_research.data.models import Base, Event
from kalshi_research.data.repositories.base import BaseRepository


class _EventRepo(BaseRepository[Event]):
    model = Event


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_add_many_and_get_all_limit(session_factory) -> None:
    async with session_factory() as session:
        repo = _EventRepo(session)
        await repo.add_many(
            [
                Event(ticker="EVT1", series_ticker="S1", title="Event 1"),
                Event(ticker="EVT2", series_ticker="S1", title="Event 2"),
            ]
        )
        await repo.commit()

        all_events = await repo.get_all()
        assert len(all_events) == 2

        limited = await repo.get_all(limit=1)
        assert len(limited) == 1


@pytest.mark.asyncio
async def test_delete_and_rollback(session_factory) -> None:
    async with session_factory() as session:
        repo = _EventRepo(session)
        await repo.add(Event(ticker="EVT1", series_ticker="S1", title="Event 1"))
        await repo.commit()

        fetched = await repo.get("EVT1")
        assert fetched is not None

        await repo.delete(fetched)
        await repo.commit()
        assert await repo.get("EVT1") is None

    async with session_factory() as session:
        repo = _EventRepo(session)
        await repo.add(Event(ticker="EVT3", series_ticker="S1", title="Event 3"))
        await repo.rollback()

    async with session_factory() as session:
        repo = _EventRepo(session)
        assert await repo.get("EVT3") is None
