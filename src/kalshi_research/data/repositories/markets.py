"""Market repository for data access."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from kalshi_research.data.models import Market, utc_now
from kalshi_research.data.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence


class MarketRepository(BaseRepository[Market]):
    """Repository for Market entities."""

    model = Market

    async def get_by_status(self, status: str) -> Sequence[Market]:
        """Get all markets with a specific status."""
        stmt = select(Market).where(Market.status == status)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_event(self, event_ticker: str) -> Sequence[Market]:
        """Get all markets for an event."""
        stmt = select(Market).where(Market.event_ticker == event_ticker)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_active(self) -> Sequence[Market]:
        """Get all active markets."""
        return await self.get_by_status("active")

    async def get_expiring_before(self, before: datetime) -> Sequence[Market]:
        """Get markets expiring before a given time."""
        stmt = (
            select(Market).where(Market.expiration_time < before).where(Market.status == "active")
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def insert_ignore(self, market: Market) -> None:
        """Insert a market row if it does not exist (FK robustness, no updates)."""
        stmt = sqlite_insert(Market).values(
            ticker=market.ticker,
            event_ticker=market.event_ticker,
            series_ticker=market.series_ticker,
            title=market.title,
            subtitle=market.subtitle,
            status=market.status,
            result=market.result,
            open_time=market.open_time,
            close_time=market.close_time,
            expiration_time=market.expiration_time,
            category=market.category,
            subcategory=market.subcategory,
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=[Market.ticker])
        await self._session.execute(stmt)

    async def upsert(self, market: Market) -> None:
        """Insert or update a market using a DB-level upsert (atomic)."""
        stmt = sqlite_insert(Market).values(
            ticker=market.ticker,
            event_ticker=market.event_ticker,
            series_ticker=market.series_ticker,
            title=market.title,
            subtitle=market.subtitle,
            status=market.status,
            result=market.result,
            open_time=market.open_time,
            close_time=market.close_time,
            expiration_time=market.expiration_time,
            category=market.category,
            subcategory=market.subcategory,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[Market.ticker],
            set_={
                "event_ticker": stmt.excluded.event_ticker,
                "series_ticker": stmt.excluded.series_ticker,
                "title": stmt.excluded.title,
                "subtitle": stmt.excluded.subtitle,
                "status": stmt.excluded.status,
                "result": stmt.excluded.result,
                "open_time": stmt.excluded.open_time,
                "close_time": stmt.excluded.close_time,
                "expiration_time": stmt.excluded.expiration_time,
                "category": stmt.excluded.category,
                "subcategory": stmt.excluded.subcategory,
                "updated_at": utc_now(),
            },
        )
        await self._session.execute(stmt)

    async def count_by_status(self) -> dict[str, int]:
        """Count markets by status."""
        from sqlalchemy import func

        stmt = select(Market.status, func.count(Market.ticker)).group_by(Market.status)
        result = await self._session.execute(stmt)
        return {str(row[0]): int(row[1]) for row in result.all()}
