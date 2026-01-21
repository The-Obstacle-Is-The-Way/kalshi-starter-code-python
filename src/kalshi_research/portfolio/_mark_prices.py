"""Mark price update logic for portfolio syncer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select

from kalshi_research.portfolio.models import Position

if TYPE_CHECKING:
    from kalshi_research.api.client import KalshiPublicClient
    from kalshi_research.data.database import DatabaseManager

logger = structlog.get_logger()


async def update_mark_prices(
    db: DatabaseManager,
    public_client: KalshiPublicClient,
) -> int:
    """
    Fetch current market prices and update mark prices + unrealized P&L.

    Uses midpoint of bid/ask as mark price (standard practice for illiquid markets).
    Reference: https://help.margex.com/help-center/leverage-trading-guide/how-leverage-works/pnl-calculation

    Args:
        db: Database manager for persistence.
        public_client: Unauthenticated client for fetching market data.

    Returns:
        Number of positions updated.
    """
    logger.info("Updating mark prices")
    updated_count = 0

    async with db.session_factory() as session:
        async with session.begin():
            result = await session.execute(
                select(Position).where(Position.quantity > 0, Position.closed_at.is_(None))
            )
            open_positions = list(result.scalars().all())

        if not open_positions:
            logger.info("No open positions to update")
            return 0

        # Fetch market data outside the DB transaction to avoid holding SQLite locks across I/O.
        updates: list[tuple[Position, int, int | None]] = []
        for pos in open_positions:
            try:
                market = await public_client.get_market(pos.ticker)

                if pos.side == "yes":
                    bid = market.yes_bid_cents
                    ask = market.yes_ask_cents
                else:
                    bid = market.no_bid_cents
                    ask = market.no_ask_cents

                if bid is None or ask is None:
                    logger.warning(
                        "Market missing dollar quotes; skipping mark price update",
                        ticker=pos.ticker,
                    )
                    continue

                # Handle unpriced/placeholder markets (0/0 or 0/100) - skip update
                if bid == 0 and ask in {0, 100}:
                    logger.warning(
                        "Market has placeholder quotes; skipping mark price update",
                        ticker=pos.ticker,
                    )
                    continue

                # Mark price = midpoint of bid/ask, stored as integer cents.
                # Midpoints can be half-cent (e.g., 50/51 -> 50.5), so we round half-up
                # to the nearest cent to match this repo's round-to-cent policy (DEBT-025).
                mark_price = (bid + ask + 1) // 2

                # Unrealized P&L = (mark_price - avg_cost) * quantity
                unrealized_pnl_cents = (
                    (mark_price - pos.avg_price_cents) * pos.quantity
                    if pos.avg_price_cents > 0
                    else None
                )

                updates.append((pos, mark_price, unrealized_pnl_cents))

            except Exception as e:
                logger.warning(
                    "Failed to fetch market data; skipping mark price update",
                    ticker=pos.ticker,
                    error=str(e),
                    exc_info=True,
                )
                continue

        if not updates:
            logger.info("No mark prices updated")
            return 0

        async with session.begin():
            for pos, mark_price, unrealized_pnl_cents in updates:
                pos.current_price_cents = mark_price
                pos.unrealized_pnl_cents = unrealized_pnl_cents
                updated_count += 1

    logger.info("Updated mark prices", count=updated_count)
    return updated_count
