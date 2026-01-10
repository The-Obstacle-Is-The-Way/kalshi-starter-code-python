from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from kalshi_research.cli.db import open_db_session
from kalshi_research.data.models import Event

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.asyncio
async def test_open_db_session_creates_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "kalshi.db"

    async with open_db_session(db_path) as session:
        session.add(Event(ticker="EVT-1", series_ticker="S1", title="Event 1", category="Test"))
        await session.commit()

        result = await session.execute(select(Event))
        events = list(result.scalars().all())

    assert len(events) == 1
    assert events[0].ticker == "EVT-1"
