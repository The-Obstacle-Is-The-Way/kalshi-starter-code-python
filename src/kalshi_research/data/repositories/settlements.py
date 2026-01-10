"""Settlement repository for data access."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from kalshi_research.data.models import Settlement
from kalshi_research.data.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence


class SettlementRepository(BaseRepository[Settlement]):
    """Repository for Settlement entities."""

    model = Settlement

    async def upsert(self, settlement: Settlement) -> None:
        """Insert or update a settlement using a DB-level upsert (atomic)."""
        stmt = sqlite_insert(Settlement).values(
            ticker=settlement.ticker,
            event_ticker=settlement.event_ticker,
            settled_at=settlement.settled_at,
            result=settlement.result,
            final_yes_price=settlement.final_yes_price,
            final_no_price=settlement.final_no_price,
            yes_payout=settlement.yes_payout,
            no_payout=settlement.no_payout,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[Settlement.ticker],
            set_={
                "event_ticker": stmt.excluded.event_ticker,
                "settled_at": stmt.excluded.settled_at,
                "result": stmt.excluded.result,
                "final_yes_price": stmt.excluded.final_yes_price,
                "final_no_price": stmt.excluded.final_no_price,
                "yes_payout": stmt.excluded.yes_payout,
                "no_payout": stmt.excluded.no_payout,
            },
        )
        await self._session.execute(stmt)

    async def get_by_event(self, event_ticker: str) -> Sequence[Settlement]:
        """Get all settlements for an event."""
        stmt = select(Settlement).where(Settlement.event_ticker == event_ticker)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_settled_after(self, after: datetime) -> Sequence[Settlement]:
        """Get settlements after a given time."""
        stmt = (
            select(Settlement)
            .where(Settlement.settled_at > after)
            .order_by(Settlement.settled_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
