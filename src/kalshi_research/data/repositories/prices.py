"""Price snapshot repository for data access."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, cast

from sqlalchemy import select
from sqlalchemy.engine import CursorResult

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

    async def get_latest_batch(self, tickers: list[str]) -> dict[str, PriceSnapshot]:
        """Get the most recent price snapshot for multiple markets."""
        # Use a subquery to get the latest snapshot time for each ticker
        from sqlalchemy import func

        subq = (
            select(
                PriceSnapshot.ticker,
                func.max(PriceSnapshot.snapshot_time).label("max_time"),
            )
            .where(PriceSnapshot.ticker.in_(tickers))
            .group_by(PriceSnapshot.ticker)
            .subquery()
        )

        stmt = select(PriceSnapshot).join(
            subq,
            (PriceSnapshot.ticker == subq.c.ticker)
            & (PriceSnapshot.snapshot_time == subq.c.max_time),
        )

        result = await self._session.execute(stmt)
        snapshots = result.scalars().all()
        return {s.ticker: s for s in snapshots}

    async def count_for_market(self, ticker: str) -> int:
        """Count price snapshots for a market."""
        from sqlalchemy import func

        stmt = select(func.count()).where(PriceSnapshot.ticker == ticker)
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count if count is not None else 0

    async def delete_older_than(self, before: datetime) -> int:
        """Delete snapshots older than a given time. Returns count deleted."""
        from sqlalchemy import delete

        stmt = delete(PriceSnapshot).where(PriceSnapshot.snapshot_time < before)
        result = await self._session.execute(stmt)
        await self._session.flush()
        cursor_result = cast(CursorResult[object], result)
        return int(cursor_result.rowcount)
