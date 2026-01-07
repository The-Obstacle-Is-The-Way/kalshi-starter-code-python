"""Tests for PortfolioSyncer."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from kalshi_research.portfolio.models import Position
from kalshi_research.portfolio.syncer import PortfolioSyncer, SyncResult


@pytest.mark.asyncio
async def test_sync_positions_with_no_api_positions_returns_zero() -> None:
    client = AsyncMock()
    client.get_positions.return_value = []

    session = AsyncMock()
    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    session.execute.return_value = empty_result

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None

    db = MagicMock()
    db.session_factory.return_value = session_cm

    syncer = PortfolioSyncer(client=client, db=db)

    assert await syncer.sync_positions() == 0
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_positions_updates_existing_and_creates_new_positions() -> None:
    client = AsyncMock()
    client.get_positions.return_value = [
        {"ticker": "TICK1", "position": 3, "realized_pnl": 123},
        {"ticker": "TICK2", "position": -2, "realized_pnl": 0},
    ]

    now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    existing = Position(
        ticker="TICK1",
        side="yes",
        quantity=1,
        avg_price_cents=10,
        current_price_cents=None,
        realized_pnl_cents=0,
        opened_at=now,
        last_synced=now,
    )

    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [existing]
    session.execute.return_value = result

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None

    db = MagicMock()
    db.session_factory.return_value = session_cm

    syncer = PortfolioSyncer(client=client, db=db)

    assert await syncer.sync_positions() == 2
    assert existing.quantity == 3
    assert existing.side == "yes"
    assert existing.realized_pnl_cents == 123
    session.add.assert_called_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_positions_marks_missing_positions_closed() -> None:
    client = AsyncMock()
    client.get_positions.return_value = []

    now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    existing = Position(
        ticker="MISSING",
        side="yes",
        quantity=1,
        avg_price_cents=10,
        current_price_cents=None,
        realized_pnl_cents=0,
        opened_at=now,
        last_synced=now,
    )

    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [existing]
    session.execute.return_value = result

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None

    db = MagicMock()
    db.session_factory.return_value = session_cm

    syncer = PortfolioSyncer(client=client, db=db)

    assert await syncer.sync_positions() == 0
    assert existing.quantity == 0
    assert existing.closed_at is not None
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_trades_with_no_api_fills_returns_zero() -> None:
    client = AsyncMock()
    client.get_fills.return_value = {"fills": []}

    session = AsyncMock()
    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    session.execute.return_value = empty_result

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None

    db = MagicMock()
    db.session_factory.return_value = session_cm

    syncer = PortfolioSyncer(client=client, db=db)

    assert await syncer.sync_trades() == 0
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_trades_paginates_and_skips_existing_trade_ids() -> None:
    client = AsyncMock()
    client.get_fills.side_effect = [
        {
            "fills": [
                {
                    "trade_id": "t1",
                    "ticker": "TICK",
                    "yes_price": 45,
                    "count": 2,
                    "created_time": "2025-01-01T00:00:00Z",
                }
            ],
            "cursor": "next",
        },
        {
            "fills": [
                {
                    "trade_id": "t2",
                    "ticker": "TICK",
                    "yes_price": 46,
                    "count": 1,
                    "created_time": "2025-01-01T00:01:00Z",
                }
            ],
            "cursor": None,
        },
    ]

    session = AsyncMock()
    existing_ids_result = MagicMock()
    existing_ids_result.scalars.return_value.all.return_value = ["t1"]
    session.execute.return_value = existing_ids_result

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None

    db = MagicMock()
    db.session_factory.return_value = session_cm

    syncer = PortfolioSyncer(client=client, db=db)

    assert await syncer.sync_trades() == 1
    session.add.assert_called_once()
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_portfolio_syncer_full_sync_returns_sync_result() -> None:
    syncer = PortfolioSyncer(client=MagicMock(), db=MagicMock())
    syncer.sync_trades = AsyncMock(return_value=3)  # type: ignore[method-assign]
    syncer.sync_positions = AsyncMock(return_value=2)  # type: ignore[method-assign]

    result = await syncer.full_sync()

    assert isinstance(result, SyncResult)
    assert result.positions_synced == 2
    assert result.trades_synced == 3
    assert result.errors is None
