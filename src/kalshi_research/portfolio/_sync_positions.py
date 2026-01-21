"""Position synchronization logic for portfolio syncer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select

from kalshi_research.portfolio._sync_helpers import compute_fifo_cost_basis
from kalshi_research.portfolio.models import Position, Trade

if TYPE_CHECKING:
    from kalshi_research.api.client import KalshiClient
    from kalshi_research.data.database import DatabaseManager

logger = structlog.get_logger()


async def sync_positions(client: KalshiClient, db: DatabaseManager) -> int:
    """
    Fetch current positions from Kalshi API and update database.

    Computes cost basis from synced trades using FIFO method.

    Args:
        client: Authenticated Kalshi API client.
        db: Database manager for persistence.

    Returns:
        Number of positions synced.
    """
    logger.info("Syncing positions")
    api_positions = await client.get_positions()
    logger.debug("API positions response", count=len(api_positions), positions=api_positions)

    if not api_positions:
        logger.warning(
            "API returned empty market positions list. "
            "If you expect open positions, confirm you're using the correct environment "
            "(demo vs prod). Note: /portfolio/positions returns market-level positions; "
            "/portfolio/balance may reflect pending settlement value."
        )

    synced_count = 0
    now = datetime.now(UTC)

    async with db.session_factory() as session, session.begin():
        # Get existing active positions (closed_at is NULL). Some API responses include
        # closed positions with position=0; historically, this led to rows with
        # quantity=0 and closed_at=NULL. Treat those as closed to avoid "phantom" positions.
        result = await session.execute(select(Position).where(Position.closed_at.is_(None)))
        existing_active = list(result.scalars().all())
        existing_open: dict[str, Position] = {}
        for existing_position in existing_active:
            if existing_position.quantity <= 0:
                existing_position.quantity = 0
                existing_position.closed_at = now
                existing_position.last_synced = now
                continue
            existing_open[existing_position.ticker] = existing_position
        seen_tickers = set()

        for pos_data in api_positions:
            # API returns PortfolioPosition Pydantic models
            ticker = pos_data.ticker
            if pos_data.position == 0:
                # Kalshi may include closed positions (position=0) in /portfolio/positions.
                # Skip creating/updating Position rows for these to avoid duplicates and
                # rely on the closure logic below for any previously-open rows.
                continue
            quantity = abs(int(pos_data.position))
            side = "yes" if pos_data.position > 0 else "no"
            seen_tickers.add(ticker)

            # Compute cost basis from trades using FIFO
            trades_result = await session.execute(
                select(Trade).where(Trade.ticker == ticker).order_by(Trade.executed_at)
            )
            trades = list(trades_result.scalars().all())
            avg_price_cents = compute_fifo_cost_basis(trades, side)

            # Cold start detection: position exists but no trades -> cost basis unreliable
            if quantity > 0 and not trades:
                logger.warning(
                    "Cold start detected: position exists but no local trade history. "
                    "Cost basis will be 0 (inaccurate). Run 'portfolio sync' to backfill "
                    "trades, or manually verify P&L calculations.",
                    ticker=ticker,
                    quantity=quantity,
                    side=side,
                )

            # Check if exists
            existing = existing_open.get(ticker)

            if existing:
                # Update existing
                existing.quantity = quantity
                existing.side = side
                existing.avg_price_cents = avg_price_cents
                existing.realized_pnl_cents = pos_data.realized_pnl or 0
                existing.last_synced = now
            else:
                # Create new
                new_pos = Position(
                    ticker=ticker,
                    side=side,
                    quantity=quantity,
                    avg_price_cents=avg_price_cents,
                    current_price_cents=None,  # Updated by update_mark_prices()
                    realized_pnl_cents=pos_data.realized_pnl or 0,
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
