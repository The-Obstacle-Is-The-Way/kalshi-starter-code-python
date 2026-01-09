"""Portfolio synchronization service for fetching positions and trades from Kalshi API."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import select

from kalshi_research.portfolio.models import Position, Trade

if TYPE_CHECKING:
    from kalshi_research.api.client import KalshiClient, KalshiPublicClient
    from kalshi_research.data.database import DatabaseManager

logger = structlog.get_logger()


def compute_fifo_cost_basis(trades: list[Trade], side: str) -> int:
    """
    Compute average cost basis for a position using FIFO.

    FIFO (First-In-First-Out) is the IRS default method and the safest choice.
    We track a queue of lots and compute weighted average of remaining shares.

    Args:
        trades: List of Trade records for this ticker, sorted by executed_at
        side: "yes" or "no" - the position side we're computing cost for

    Returns:
        Average cost basis in cents (0 if no position)

    Reference: https://coinledger.io/blog/cryptocurrency-tax-calculations-fifo-and-lifo-costing-methods-explained
    """
    # Queue of lots: (quantity, price_cents)
    lots: deque[tuple[int, int]] = deque()

    for trade in trades:
        # Filter to trades matching the position side
        if trade.side != side:
            continue

        price = trade.price_cents
        qty = trade.quantity

        if trade.action == "buy":
            # Add to position - push lot onto queue
            lots.append((qty, price))
        elif trade.action == "sell":
            # Reduce position - pop FIFO from queue
            remaining = qty
            while remaining > 0 and lots:
                lot_qty, _lot_price = lots[0]
                if lot_qty <= remaining:
                    # Consume entire lot
                    lots.popleft()
                    remaining -= lot_qty
                else:
                    # Partial lot consumption
                    lots[0] = (lot_qty - remaining, _lot_price)
                    remaining = 0

    # Compute weighted average of remaining lots
    if not lots:
        return 0

    total_qty = sum(qty for qty, _ in lots)
    total_cost = sum(qty * price for qty, price in lots)

    if total_qty == 0:
        return 0

    return total_cost // total_qty


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

        Computes cost basis from synced trades using FIFO method.

        Returns:
            Number of positions synced
        """
        logger.info("Syncing positions")
        api_positions = await self.client.get_positions()
        logger.debug("API positions response", count=len(api_positions), positions=api_positions)

        if not api_positions:
            logger.warning(
                "API returned empty positions list. "
                "Note: Kalshi's /portfolio/positions endpoint may not include settled positions or "
                "positions in markets that have closed recently. "
                "The portfolio_value in /portfolio/balance may include pending settlements or "
                "be temporarily out of sync. This is a known Kalshi API behavior."
            )

        synced_count = 0
        now = datetime.now(UTC)

        async with self.db.session_factory() as session, session.begin():
            # Get existing open positions to handle closures
            result = await session.execute(
                select(Position).where(Position.quantity > 0, Position.closed_at.is_(None))
            )
            existing_open = {p.ticker: p for p in result.scalars().all()}
            seen_tickers = set()

            for pos_data in api_positions:
                # API returns position dictionaries with keys like:
                # ticker, position, market_exposure, realized_pnl, fees_paid.
                ticker = pos_data["ticker"]
                quantity = abs(int(pos_data["position"]))
                side = "yes" if pos_data["position"] > 0 else "no"
                seen_tickers.add(ticker)

                # Compute cost basis from trades using FIFO
                trades_result = await session.execute(
                    select(Trade).where(Trade.ticker == ticker).order_by(Trade.executed_at)
                )
                trades = list(trades_result.scalars().all())
                avg_price_cents = compute_fifo_cost_basis(trades, side)

                # Check if exists
                existing = existing_open.get(ticker)

                if existing:
                    # Update existing
                    existing.quantity = quantity
                    existing.side = side
                    existing.avg_price_cents = avg_price_cents
                    existing.realized_pnl_cents = int(pos_data.get("realized_pnl", 0))
                    existing.last_synced = now
                else:
                    # Create new
                    new_pos = Position(
                        ticker=ticker,
                        side=side,
                        quantity=quantity,
                        avg_price_cents=avg_price_cents,
                        current_price_cents=None,  # Updated by update_mark_prices()
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
                    logger.info("Marked position as closed", ticker=ticker)

        logger.info("Synced positions", count=synced_count)
        return synced_count

    async def sync_trades(self, since: datetime | None = None) -> int:
        """
        Fetch trade history from Kalshi API and update database.

        Args:
            since: Only fetch trades after this timestamp

        Returns:
            Number of trades synced
        """
        logger.info("Syncing trades")
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

        async with self.db.session_factory() as session, session.begin():
            # Check for existing trades to avoid duplicates
            # Using kalshi_trade_id for idempotency
            existing_ids_result = await session.execute(select(Trade.kalshi_trade_id))
            existing_ids = set(existing_ids_result.scalars().all())

            for fill in fills:
                # Fill dictionaries contain keys like:
                # trade_id, ticker, yes_price, no_price, count, action, side, created_time.
                trade_id = fill["trade_id"]
                if trade_id in existing_ids:
                    continue

                executed_at = datetime.fromisoformat(fill["created_time"].replace("Z", "+00:00"))
                side_raw = str(fill.get("side", "yes")).lower()
                if side_raw not in {"yes", "no"}:
                    logger.warning(
                        "Unknown fill side; skipping",
                        side=side_raw,
                        trade_id=trade_id,
                    )
                    continue

                action_raw = str(fill.get("action", "buy")).lower()
                if action_raw not in {"buy", "sell"}:
                    logger.warning(
                        "Unknown fill action; skipping",
                        action=action_raw,
                        trade_id=trade_id,
                    )
                    continue

                yes_price = int(fill["yes_price"])
                if side_raw == "yes":
                    price = yes_price
                else:
                    no_price = fill.get("no_price")
                    price = int(no_price) if no_price is not None else 100 - yes_price
                quantity = int(fill["count"])

                trade = Trade(
                    kalshi_trade_id=trade_id,
                    ticker=fill["ticker"],
                    side=side_raw,
                    action=action_raw,
                    quantity=quantity,
                    price_cents=price,
                    total_cost_cents=price * quantity,
                    fee_cents=0,  # API doesn't always provide per-trade fees in fills
                    executed_at=executed_at,
                    synced_at=now,
                )
                session.add(trade)
                synced_count += 1

                # Flush in batches to avoid memory issues (still within transaction)
                if synced_count % 1000 == 0:
                    await session.flush()

        logger.info("Synced new trades", count=synced_count)
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
        logger.info("Updating mark prices")
        updated_count = 0

        async with self.db.session_factory() as session, session.begin():
            # Get all open positions
            result = await session.execute(
                select(Position).where(Position.quantity > 0, Position.closed_at.is_(None))
            )
            open_positions = list(result.scalars().all())

            if not open_positions:
                logger.info("No open positions to update")
                return 0

            # Fetch market data for each position's ticker
            for pos in open_positions:
                try:
                    market = await public_client.get_market(pos.ticker)

                    # Compute mark price as midpoint (in cents)
                    # Handle unpriced markets (0/0 or 0/100) - skip update
                    if market.yes_bid_cents == 0 and market.yes_ask_cents == 0:
                        logger.warning(
                            "Market has no quotes; skipping mark price update",
                            ticker=pos.ticker,
                        )
                        continue
                    if market.yes_bid_cents == 0 and market.yes_ask_cents == 100:
                        logger.warning(
                            "Market has placeholder quotes; skipping mark price update",
                            ticker=pos.ticker,
                        )
                        continue

                    # Mark price = midpoint of bid/ask
                    if pos.side == "yes":
                        mark_price = int(market.midpoint)
                    else:
                        # For NO positions, use NO side midpoint
                        mark_price = (market.no_bid_cents + market.no_ask_cents) // 2

                    pos.current_price_cents = mark_price

                    # Compute unrealized P&L
                    # Unrealized P&L = (mark_price - avg_cost) * quantity
                    if pos.avg_price_cents > 0:
                        pos.unrealized_pnl_cents = (mark_price - pos.avg_price_cents) * pos.quantity
                    else:
                        # No cost basis available, cannot compute unrealized P&L
                        pos.unrealized_pnl_cents = None

                    updated_count += 1

                except Exception as e:
                    logger.warning(
                        "Failed to fetch market data; skipping mark price update",
                        ticker=pos.ticker,
                        error=str(e),
                    )
                    continue

        logger.info("Updated mark prices", count=updated_count)
        return updated_count
