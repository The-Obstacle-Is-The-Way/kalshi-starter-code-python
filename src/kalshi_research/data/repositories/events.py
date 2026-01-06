"""Event repository for data access."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from kalshi_research.data.models import Event
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

    async def upsert(self, event: Event) -> Event:
        """Insert or update an event."""
        existing = await self.get(event.ticker)
        if existing is not None:
            # Update existing event - only update non-None values
            existing.series_ticker = event.series_ticker
            existing.title = event.title
            if event.status is not None:
                existing.status = event.status
            if event.category is not None:
                existing.category = event.category
            # mutually_exclusive has a default of False, only update if explicitly set
            existing.mutually_exclusive = event.mutually_exclusive
            await self._session.flush()
            await self._session.refresh(existing)
            return existing
        return await self.add(event)
