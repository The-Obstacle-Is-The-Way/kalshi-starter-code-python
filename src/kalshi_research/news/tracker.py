"""Track markets/events for ongoing news collection."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from sqlalchemy import select

from kalshi_research.data.models import TrackedItem

if TYPE_CHECKING:
    from kalshi_research.data.database import DatabaseManager


class NewsTracker:
    """Manages tracked markets/events stored in the database."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def track(
        self,
        *,
        ticker: str,
        item_type: str,
        search_queries: list[str],
    ) -> TrackedItem:
        if item_type not in {"market", "event"}:
            raise ValueError("item_type must be 'market' or 'event'")

        normalized_queries = [q.strip() for q in search_queries if q.strip()]
        if not normalized_queries:
            raise ValueError("search_queries cannot be empty")

        async with self._db.session_factory() as session, session.begin():
            existing = (
                await session.execute(select(TrackedItem).where(TrackedItem.ticker == ticker))
            ).scalar_one_or_none()
            if existing is None:
                tracked = TrackedItem(
                    ticker=ticker,
                    item_type=item_type,
                    search_queries=json.dumps(normalized_queries),
                    is_active=True,
                )
                session.add(tracked)
                await session.flush()
                await session.refresh(tracked)
                return tracked

            existing.item_type = item_type
            existing.search_queries = json.dumps(normalized_queries)
            existing.is_active = True
            await session.flush()
            await session.refresh(existing)
            return existing

    async def untrack(self, ticker: str) -> bool:
        async with self._db.session_factory() as session, session.begin():
            tracked = (
                await session.execute(select(TrackedItem).where(TrackedItem.ticker == ticker))
            ).scalar_one_or_none()
            if tracked is None:
                return False
            tracked.is_active = False
            return True

    async def list_tracked(self, *, active_only: bool = True) -> list[TrackedItem]:
        async with self._db.session_factory() as session:
            query = select(TrackedItem)
            if active_only:
                query = query.where(TrackedItem.is_active == True)  # noqa: E712
            return list((await session.execute(query)).scalars().all())
