"""Tests for PortfolioSyncer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kalshi_research.portfolio.syncer import PortfolioSyncer, SyncResult


@pytest.mark.asyncio
async def test_portfolio_syncer_returns_zero_for_stubs() -> None:
    syncer = PortfolioSyncer(client=MagicMock(), db=MagicMock())

    assert await syncer.sync_positions() == 0
    assert await syncer.sync_trades() == 0


@pytest.mark.asyncio
async def test_portfolio_syncer_full_sync() -> None:
    syncer = PortfolioSyncer(client=MagicMock(), db=MagicMock())

    result = await syncer.full_sync()

    assert isinstance(result, SyncResult)
    assert result.positions_synced == 0
    assert result.trades_synced == 0
    assert result.errors is None
