"""Price snapshot repository for data access."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from kalshi_research.data.models import PriceSnapshot
from kalshi_research.data.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence


class PriceRepository(BaseRepository[PriceSnapshot]):
    """Repository for PriceSnapshot entities."""

    model = PriceSnapshot

    async def get_for_market(
        self,
        ticker: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> Sequence[PriceSnapshot]:
        """Get price snapshots for a market within a time range."""
        stmt = select(PriceSnapshot).where(PriceSnapshot.ticker == ticker)

        if start_time is not None:
            stmt = stmt.where(PriceSnapshot.snapshot_time >= start_time)
        if end_time is not None:
            stmt = stmt.where(PriceSnapshot.snapshot_time <= end_time)

        stmt = stmt.order_by(PriceSnapshot.snapshot_time.desc())

        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_latest(self, ticker: str) -> PriceSnapshot | None:
        """Get the most recent price snapshot for a market."""
        stmt = (
            select(PriceSnapshot)
            .where(PriceSnapshot.ticker == ticker)
            .order_by(PriceSnapshot.snapshot_time.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_for_market(self, ticker: str) -> int:
        """Count price snapshots for a market."""
        from sqlalchemy import func

        stmt = select(func.count()).where(PriceSnapshot.ticker == ticker)
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count if count is not None else 0
