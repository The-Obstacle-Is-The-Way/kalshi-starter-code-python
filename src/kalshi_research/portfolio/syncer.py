"""Portfolio synchronization service for fetching positions and trades from Kalshi API."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, update

from kalshi_research.portfolio.models import Position, Trade

if TYPE_CHECKING:
    from kalshi_research.api.client import KalshiClient
    from kalshi_research.data.database import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a portfolio sync operation."""

    positions_synced: int
    trades_synced: int
    errors: list[str] | None = None


class PortfolioSyncer:
    """Sync positions and trades from Kalshi API to local database."""

    def __init__(self, client: KalshiClient, db: DatabaseManager):
        """Initialize syncer with authenticated client and database."""
        self.client = client
        self.db = db

    async def sync_positions(self) -> int:
        """
        Fetch current positions from Kalshi API and update database.

        Returns:
            Number of positions synced
        """
        logger.info("Syncing positions...")
        api_positions = await self.client.get_positions()
        synced_count = 0
        now = datetime.now(UTC)

        async with self.db.session_factory() as session:
            # Get existing open positions to handle closures
            result = await session.execute(
                select(Position).where(Position.quantity > 0, Position.closed_at.is_(None))
            )
            existing_open = {p.ticker: p for p in result.scalars().all()}
            seen_tickers = set()

            for pos_data in api_positions:
                # API returns list of market positions
                # Structure: {
                #   "ticker": "KXBTC-24DEC31-100000",
                #   "position": 10,
                #   "market_exposure": 450,
                #   "realized_pnl": 120,
                #   "fees_paid": 5,
                #   ...
                # }
                ticker = pos_data["ticker"]
                quantity = abs(int(pos_data["position"]))
                side = "yes" if pos_data["position"] > 0 else "no"
                seen_tickers.add(ticker)

                # Check if exists
                existing = existing_open.get(ticker)

                if existing:
                    # Update existing
                    existing.quantity = quantity
                    existing.side = side
                    existing.realized_pnl_cents = int(pos_data.get("realized_pnl", 0))
                    existing.last_synced = now
                else:
                    # Create new
                    new_pos = Position(
                        ticker=ticker,
                        side=side,
                        quantity=quantity,
                        avg_price_cents=0,  # TODO: Calculate from trades if possible
                        current_price_cents=None,  # Need market data to fill this
                        realized_pnl_cents=int(pos_data.get("realized_pnl", 0)),
                        opened_at=now,  # Approximation for new sync
                        last_synced=now,
                    )
                    session.add(new_pos)

                synced_count += 1

            # Handle closed positions (in DB but not in API)
            for ticker, pos in existing_open.items():
                if ticker not in seen_tickers:
                    pos.quantity = 0
                    pos.closed_at = now
                    pos.last_synced = now
                    logger.info("Marked position %s as closed", ticker)

            await session.commit()

        logger.info("Synced %d positions", synced_count)
        return synced_count

    async def sync_trades(self, since: datetime | None = None) -> int:
        """
        Fetch trade history from Kalshi API and update database.

        Args:
            since: Only fetch trades after this timestamp

        Returns:
            Number of trades synced
        """
        logger.info("Syncing trades...")
        min_ts = int(since.timestamp()) if since else None
        
        # Paginate through fills
        fills: list[dict[str, Any]] = []
        cursor = None
        
        while True:
            response = await self.client.get_fills(min_ts=min_ts, limit=100, cursor=cursor)
            page_fills = response.get("fills", [])
            if not page_fills:
                break
            
            fills.extend(page_fills)
            cursor = response.get("cursor")
            if not cursor:
                break

        synced_count = 0
        now = datetime.now(UTC)

        async with self.db.session_factory() as session:
            # Check for existing trades to avoid duplicates
            # Using kalshi_trade_id for idempotency
            existing_ids_result = await session.execute(select(Trade.kalshi_trade_id))
            existing_ids = set(existing_ids_result.scalars().all())

            for fill in fills:
                # Structure: {
                #   "trade_id": "834468f7-...",
                #   "ticker": "KXBTC-...",
                #   "yes_price": 45,
                #   "count": 10,
                #   "action": "buy",
                #   "side": "yes",
                #   "created_time": "2023-10-25T..."
                # }
                trade_id = fill["trade_id"]
                if trade_id in existing_ids:
                    continue

                executed_at = datetime.fromisoformat(fill["created_time"].replace("Z", "+00:00"))
                price = int(fill["yes_price"])
                quantity = int(fill["count"])
                
                trade = Trade(
                    kalshi_trade_id=trade_id,
                    ticker=fill["ticker"],
                    side=fill.get("side", "yes"),
                    action=fill.get("action", "buy"),
                    quantity=quantity,
                    price_cents=price,
                    total_cost_cents=price * quantity,
                    fee_cents=0,  # API doesn't always provide per-trade fees in fills
                    executed_at=executed_at,
                    synced_at=now,
                )
                session.add(trade)
                synced_count += 1
                
                # Check 1000 item flush
                if synced_count % 1000 == 0:
                    await session.commit()

            await session.commit()

        logger.info("Synced %d new trades", synced_count)
        return synced_count

    async def full_sync(self) -> SyncResult:
        """
        Perform a full portfolio sync (positions + trades).

        Returns:
            SyncResult with counts of synced items
        """
        trades = await self.sync_trades()
        positions = await self.sync_positions()

        return SyncResult(
            positions_synced=positions,
            trades_synced=trades,
        )