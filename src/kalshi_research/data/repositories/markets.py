"""Market repository for data access."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from kalshi_research.data.models import Market
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

    async def upsert(self, market: Market) -> Market:
        """Insert or update a market."""
        existing = await self.get(market.ticker)
        if existing is not None:
            # Update existing market
            existing.event_ticker = market.event_ticker
            existing.series_ticker = market.series_ticker
            existing.title = market.title
            existing.subtitle = market.subtitle
            existing.status = market.status
            existing.result = market.result
            existing.open_time = market.open_time
            existing.close_time = market.close_time
            existing.expiration_time = market.expiration_time
            existing.category = market.category
            existing.subcategory = market.subcategory
            await self._session.flush()
            await self._session.refresh(existing)
            return existing
        return await self.add(market)

    async def count_by_status(self) -> dict[str, int]:
        """Count markets by status."""
        from sqlalchemy import func

        stmt = select(Market.status, func.count(Market.ticker)).group_by(Market.status)
        result = await self._session.execute(stmt)
        return {str(row[0]): int(row[1]) for row in result.all()}
