from __future__ import annotations

import pytest

from kalshi_research.data import DatabaseManager
from kalshi_research.news import NewsTracker

pytestmark = [pytest.mark.unit]


@pytest.mark.asyncio
async def test_track_list_untrack_roundtrip(tmp_path) -> None:
    db_path = tmp_path / "news_tracker.db"
    async with DatabaseManager(db_path) as db:
        await db.create_tables()
        tracker = NewsTracker(db)

        tracked = await tracker.track(
            ticker="TEST-MARKET",
            item_type="market",
            search_queries=["Test Market", "Test Market news"],
        )
        assert tracked.ticker == "TEST-MARKET"
        assert tracked.item_type == "market"
        assert tracked.is_active is True

        tracked_items = await tracker.list_tracked()
        assert [t.ticker for t in tracked_items] == ["TEST-MARKET"]

        updated = await tracker.track(
            ticker="TEST-MARKET",
            item_type="market",
            search_queries=["Updated query"],
        )
        assert updated.ticker == "TEST-MARKET"

        removed = await tracker.untrack("TEST-MARKET")
        assert removed is True

        active_items = await tracker.list_tracked()
        assert active_items == []

        all_items = await tracker.list_tracked(active_only=False)
        assert len(all_items) == 1
        assert all_items[0].is_active is False
