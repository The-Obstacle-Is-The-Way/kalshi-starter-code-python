"""Tests for PortfolioSyncer."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kalshi_research.portfolio.models import Position, Trade
from kalshi_research.portfolio.syncer import (
    PortfolioSyncer,
    SyncResult,
    compute_fifo_cost_basis,
)


@pytest.mark.asyncio
async def test_sync_positions_with_no_api_positions_returns_zero() -> None:
    client = AsyncMock()
    client.get_positions.return_value = []

    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    session = MagicMock()
    session.execute = AsyncMock(return_value=empty_result)
    session.commit = AsyncMock()

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

    # First call returns existing positions, subsequent calls return empty trades
    positions_result = MagicMock()
    positions_result.scalars.return_value.all.return_value = [existing]

    trades_result = MagicMock()
    trades_result.scalars.return_value.all.return_value = []

    session = MagicMock()
    # First call is positions, subsequent calls are trades
    session.execute = AsyncMock(side_effect=[positions_result, trades_result, trades_result])
    session.commit = AsyncMock()

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
    # avg_price_cents should be 0 since no trades exist
    assert existing.avg_price_cents == 0
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

    result = MagicMock()
    result.scalars.return_value.all.return_value = [existing]
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()

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

    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    session = MagicMock()
    session.execute = AsyncMock(return_value=empty_result)
    session.commit = AsyncMock()

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

    existing_ids_result = MagicMock()
    existing_ids_result.scalars.return_value.all.return_value = ["t1"]
    session = MagicMock()
    session.execute = AsyncMock(return_value=existing_ids_result)
    session.commit = AsyncMock()

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
async def test_sync_trades_uses_no_price_for_no_side() -> None:
    client = AsyncMock()
    client.get_fills.return_value = {
        "fills": [
            {
                "trade_id": "t1",
                "ticker": "TICK",
                "side": "no",
                "action": "buy",
                "yes_price": 60,
                "no_price": 40,
                "count": 2,
                "created_time": "2025-01-01T00:00:00Z",
            }
        ],
        "cursor": None,
    }

    existing_ids_result = MagicMock()
    existing_ids_result.scalars.return_value.all.return_value = []
    session = MagicMock()
    session.execute = AsyncMock(return_value=existing_ids_result)
    session.commit = AsyncMock()

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None

    db = MagicMock()
    db.session_factory.return_value = session_cm

    syncer = PortfolioSyncer(client=client, db=db)

    assert await syncer.sync_trades() == 1

    assert session.add.call_count == 1
    (trade,) = session.add.call_args[0]
    assert trade.side == "no"
    assert trade.action == "buy"
    assert trade.price_cents == 40
    assert trade.total_cost_cents == 80


@pytest.mark.asyncio
async def test_portfolio_syncer_full_sync_returns_sync_result() -> None:
    syncer = PortfolioSyncer(client=MagicMock(), db=MagicMock())
    with (
        patch.object(syncer, "sync_trades", new=AsyncMock(return_value=3)),
        patch.object(syncer, "sync_positions", new=AsyncMock(return_value=2)),
    ):
        result = await syncer.full_sync()

    assert isinstance(result, SyncResult)
    assert result.positions_synced == 2
    assert result.trades_synced == 3
    assert result.errors is None


# ==================== FIFO Cost Basis Tests ====================


def _make_trade(
    side: str,
    action: str,
    quantity: int,
    price_cents: int,
    executed_at: datetime | None = None,
) -> Trade:
    """Helper to create a Trade object for testing."""
    now = executed_at or datetime.now(UTC)
    return Trade(
        kalshi_trade_id=f"t-{now.timestamp()}",
        ticker="TEST",
        side=side,
        action=action,
        quantity=quantity,
        price_cents=price_cents,
        total_cost_cents=price_cents * quantity,
        fee_cents=0,
        executed_at=now,
        synced_at=now,
    )


def test_compute_fifo_cost_basis_no_trades_returns_zero() -> None:
    """No trades should return 0 cost basis."""
    assert compute_fifo_cost_basis([], "yes") == 0


def test_compute_fifo_cost_basis_single_buy() -> None:
    """Single buy should return that price as cost basis."""
    trades = [_make_trade("yes", "buy", 10, 45)]
    assert compute_fifo_cost_basis(trades, "yes") == 45


def test_compute_fifo_cost_basis_multiple_buys_weighted_average() -> None:
    """Multiple buys should return weighted average."""
    now = datetime.now(UTC)
    trades = [
        _make_trade("yes", "buy", 10, 40, now),  # 10 @ 40 = 400
        _make_trade("yes", "buy", 20, 50, now),  # 20 @ 50 = 1000
    ]
    # Total: 30 contracts, total cost 1400
    # Average: 1400 / 30 = 46.67 -> 46 (integer division)
    assert compute_fifo_cost_basis(trades, "yes") == 46


def test_compute_fifo_cost_basis_fifo_sell() -> None:
    """Sells should consume FIFO lots."""
    now = datetime.now(UTC)
    trades = [
        _make_trade("yes", "buy", 10, 40, now),  # Lot 1: 10 @ 40
        _make_trade("yes", "buy", 10, 60, now),  # Lot 2: 10 @ 60
        _make_trade("yes", "sell", 10, 70, now),  # Sell 10 (consumes Lot 1)
    ]
    # Remaining: 10 @ 60
    assert compute_fifo_cost_basis(trades, "yes") == 60


def test_compute_fifo_cost_basis_partial_sell() -> None:
    """Partial sells should partially consume FIFO lots."""
    now = datetime.now(UTC)
    trades = [
        _make_trade("yes", "buy", 10, 40, now),  # Lot 1: 10 @ 40
        _make_trade("yes", "sell", 5, 50, now),  # Sell 5 (partial Lot 1)
    ]
    # Remaining: 5 @ 40
    assert compute_fifo_cost_basis(trades, "yes") == 40


def test_compute_fifo_cost_basis_ignores_wrong_side() -> None:
    """Only trades matching the side should be considered."""
    now = datetime.now(UTC)
    trades = [
        _make_trade("yes", "buy", 10, 40, now),
        _make_trade("no", "buy", 10, 60, now),  # Different side
    ]
    assert compute_fifo_cost_basis(trades, "yes") == 40
    assert compute_fifo_cost_basis(trades, "no") == 60


def test_compute_fifo_cost_basis_sold_out_returns_zero() -> None:
    """Fully sold position should return 0."""
    now = datetime.now(UTC)
    trades = [
        _make_trade("yes", "buy", 10, 40, now),
        _make_trade("yes", "sell", 10, 50, now),  # Sell all
    ]
    assert compute_fifo_cost_basis(trades, "yes") == 0


# ==================== Update Mark Prices Tests ====================


@pytest.mark.asyncio
async def test_update_mark_prices_with_no_open_positions() -> None:
    """No open positions should return 0 updated."""
    client = MagicMock()
    db = MagicMock()

    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    session = MagicMock()
    session.execute = AsyncMock(return_value=empty_result)
    session.commit = AsyncMock()

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    db.session_factory.return_value = session_cm

    syncer = PortfolioSyncer(client=client, db=db)
    public_client = AsyncMock()

    assert await syncer.update_mark_prices(public_client) == 0


@pytest.mark.asyncio
async def test_update_mark_prices_computes_unrealized_pnl() -> None:
    """Mark prices should update and compute unrealized P&L."""
    client = MagicMock()
    db = MagicMock()

    now = datetime.now(UTC)
    position = Position(
        ticker="TEST",
        side="yes",
        quantity=10,
        avg_price_cents=40,
        current_price_cents=None,
        unrealized_pnl_cents=None,
        realized_pnl_cents=0,
        opened_at=now,
        last_synced=now,
    )

    positions_result = MagicMock()
    positions_result.scalars.return_value.all.return_value = [position]

    session = MagicMock()
    session.execute = AsyncMock(return_value=positions_result)
    session.commit = AsyncMock()

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    db.session_factory.return_value = session_cm

    syncer = PortfolioSyncer(client=client, db=db)

    # Mock market data: yes_bid=48, yes_ask=52 -> midpoint=50
    market = MagicMock()
    market.yes_bid_cents = 48
    market.yes_ask_cents = 52
    market.no_bid_cents = 48
    market.no_ask_cents = 52
    market.midpoint = 50.0

    public_client = AsyncMock()
    public_client.get_market = AsyncMock(return_value=market)

    result = await syncer.update_mark_prices(public_client)

    assert result == 1
    assert position.current_price_cents == 50
    # Unrealized P&L = (50 - 40) * 10 = 100
    assert position.unrealized_pnl_cents == 100


@pytest.mark.asyncio
async def test_update_mark_prices_skips_unpriced_markets() -> None:
    """Unpriced markets (0/0) should be skipped."""
    client = MagicMock()
    db = MagicMock()

    now = datetime.now(UTC)
    position = Position(
        ticker="UNPRICED",
        side="yes",
        quantity=10,
        avg_price_cents=40,
        current_price_cents=None,
        unrealized_pnl_cents=None,
        realized_pnl_cents=0,
        opened_at=now,
        last_synced=now,
    )

    positions_result = MagicMock()
    positions_result.scalars.return_value.all.return_value = [position]

    session = MagicMock()
    session.execute = AsyncMock(return_value=positions_result)
    session.commit = AsyncMock()

    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    db.session_factory.return_value = session_cm

    syncer = PortfolioSyncer(client=client, db=db)

    # Mock unpriced market: 0/0
    market = MagicMock()
    market.yes_bid_cents = 0
    market.yes_ask_cents = 0

    public_client = AsyncMock()
    public_client.get_market = AsyncMock(return_value=market)

    result = await syncer.update_mark_prices(public_client)

    # Should skip the unpriced market
    assert result == 0
    assert position.current_price_cents is None
    assert position.unrealized_pnl_cents is None
