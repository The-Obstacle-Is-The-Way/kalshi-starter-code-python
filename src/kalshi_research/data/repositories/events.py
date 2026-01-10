"""Event repository for data access."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from kalshi_research.data.models import Event, utc_now
from kalshi_research.data.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence


class EventRepository(BaseRepository[Event]):
    """Repository for Event entities."""

    model = Event

    async def get_by_series(self, series_ticker: str) -> Sequence[Event]:
        """Get all events for a series."""
        stmt = select(Event).where(Event.series_ticker == series_ticker)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_category(self, category: str) -> Sequence[Event]:
        """Get all events in a category."""
        stmt = select(Event).where(Event.category == category)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def insert_ignore(self, event: Event) -> None:
        """Insert an event row if it does not exist.

        This is used to create placeholder rows for foreign key robustness without racing other
        writers.
        """
        mutually_exclusive = (
            event.mutually_exclusive if event.mutually_exclusive is not None else False
        )
        stmt = sqlite_insert(Event).values(
            ticker=event.ticker,
            series_ticker=event.series_ticker,
            title=event.title,
            status=event.status,
            category=event.category,
            mutually_exclusive=mutually_exclusive,
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=[Event.ticker])
        await self._session.execute(stmt)

    async def upsert(self, event: Event) -> None:
        """Insert or update an event using a DB-level upsert (atomic)."""
        mutually_exclusive = (
            event.mutually_exclusive if event.mutually_exclusive is not None else False
        )
        stmt = sqlite_insert(Event).values(
            ticker=event.ticker,
            series_ticker=event.series_ticker,
            title=event.title,
            status=event.status,
            category=event.category,
            mutually_exclusive=mutually_exclusive,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[Event.ticker],
            set_={
                "series_ticker": stmt.excluded.series_ticker,
                "title": stmt.excluded.title,
                "status": func.coalesce(stmt.excluded.status, Event.status),
                "category": func.coalesce(stmt.excluded.category, Event.category),
                "mutually_exclusive": stmt.excluded.mutually_exclusive,
                "updated_at": utc_now(),
            },
        )
        await self._session.execute(stmt)
