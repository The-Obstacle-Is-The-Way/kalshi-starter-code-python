"""Portfolio synchronization service for fetching positions and trades from Kalshi API.

This module provides the PortfolioSyncer class which orchestrates synchronization
of positions, trades, and settlements from the Kalshi API to the local database.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from kalshi_research.portfolio._mark_prices import update_mark_prices as _update_mark_prices
from kalshi_research.portfolio._sync_helpers import SyncResult, compute_fifo_cost_basis
from kalshi_research.portfolio._sync_positions import sync_positions as _sync_positions
from kalshi_research.portfolio._sync_settlements import sync_settlements as _sync_settlements
from kalshi_research.portfolio._sync_trades import sync_trades as _sync_trades

if TYPE_CHECKING:
    from datetime import datetime

    from kalshi_research.api.client import KalshiClient, KalshiPublicClient
    from kalshi_research.data.database import DatabaseManager

# Re-export for backwards compatibility
__all__ = ["PortfolioSyncer", "SyncResult", "compute_fifo_cost_basis"]


class PortfolioSyncer:
    """Sync positions and trades from Kalshi API to local database."""

    def __init__(self, client: KalshiClient, db: DatabaseManager):
        """Initialize syncer with authenticated client and database."""
        self.client = client
        self.db = db

    async def sync_positions(self) -> int:
        """
        Fetch current positions from Kalshi API and update database.

        Computes cost basis from synced trades using FIFO method.

        Returns:
            Number of positions synced
        """
        return await _sync_positions(self.client, self.db)

    async def sync_trades(self, since: datetime | None = None) -> int:
        """
        Fetch trade history from Kalshi API and update database.

        Args:
            since: Only fetch trades after this timestamp

        Returns:
            Number of trades synced
        """
        return await _sync_trades(self.client, self.db, since)

    async def sync_settlements(self, since: datetime | None = None) -> int:
        """
        Fetch settlement history from Kalshi API and update database.

        Args:
            since: Only fetch settlements after this timestamp

        Returns:
            Number of settlements synced
        """
        return await _sync_settlements(self.client, self.db, since)

    async def full_sync(self) -> SyncResult:
        """
        Perform a full portfolio sync (positions + trades + settlements).

        Returns:
            SyncResult with counts of synced items
        """
        trades = await self.sync_trades()
        settlements = await self.sync_settlements()
        positions = await self.sync_positions()

        return SyncResult(
            positions_synced=positions,
            trades_synced=trades,
            settlements_synced=settlements,
        )

    async def update_mark_prices(self, public_client: KalshiPublicClient) -> int:
        """
        Fetch current market prices and update mark prices + unrealized P&L.

        Uses midpoint of bid/ask as mark price (standard practice for illiquid markets).
        Reference: https://help.margex.com/help-center/leverage-trading-guide/how-leverage-works/pnl-calculation

        Args:
            public_client: Unauthenticated client for fetching market data

        Returns:
            Number of positions updated
        """
        return await _update_mark_prices(self.db, public_client)
