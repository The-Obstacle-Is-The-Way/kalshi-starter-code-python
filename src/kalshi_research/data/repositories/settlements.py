"""Settlement repository for data access."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from kalshi_research.data.models import Settlement
from kalshi_research.data.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence


class SettlementRepository(BaseRepository[Settlement]):
    """Repository for Settlement entities."""

    model = Settlement

    async def upsert(self, settlement: Settlement) -> Settlement:
        """Insert or update a settlement."""
        existing = await self.get(settlement.ticker)
        if existing is not None:
            existing.event_ticker = settlement.event_ticker
            existing.settled_at = settlement.settled_at
            existing.result = settlement.result
            existing.final_yes_price = settlement.final_yes_price
            existing.final_no_price = settlement.final_no_price
            existing.yes_payout = settlement.yes_payout
            existing.no_payout = settlement.no_payout
            await self._session.flush()
            await self._session.refresh(existing)
            return existing
        return await self.add(settlement)

    async def get_by_event(self, event_ticker: str) -> Sequence[Settlement]:
        """Get all settlements for an event."""
        stmt = select(Settlement).where(Settlement.event_ticker == event_ticker)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_result(self, result: str) -> Sequence[Settlement]:
        """Get all settlements with a specific result (yes, no, void)."""
        stmt = select(Settlement).where(Settlement.result == result)
        result_set = await self._session.execute(stmt)
        return result_set.scalars().all()

    async def get_settled_after(self, after: datetime) -> Sequence[Settlement]:
        """Get settlements after a given time."""
        stmt = (
            select(Settlement)
            .where(Settlement.settled_at > after)
            .order_by(Settlement.settled_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_by_result(self) -> dict[str, int]:
        """Count settlements by result."""
        from sqlalchemy import func

        stmt = select(Settlement.result, func.count(Settlement.ticker)).group_by(Settlement.result)
        result = await self._session.execute(stmt)
        return {str(row[0]): int(row[1]) for row in result.all()}
