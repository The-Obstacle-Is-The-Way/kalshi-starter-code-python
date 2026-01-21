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

    async with db.session_factory() as session, session.begin():
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

                yes_bid = market.yes_bid_cents
                yes_ask = market.yes_ask_cents
                no_bid = market.no_bid_cents
                no_ask = market.no_ask_cents
                if yes_bid is None or yes_ask is None or no_bid is None or no_ask is None:
                    logger.warning(
                        "Market missing dollar quotes; skipping mark price update",
                        ticker=pos.ticker,
                    )
                    continue

                # Compute mark price as midpoint (in cents)
                # Handle unpriced markets (0/0 or 0/100) - skip update
                if yes_bid == 0 and yes_ask == 0:
                    logger.warning(
                        "Market has no quotes; skipping mark price update",
                        ticker=pos.ticker,
                    )
                    continue
                if yes_bid == 0 and yes_ask == 100:
                    logger.warning(
                        "Market has placeholder quotes; skipping mark price update",
                        ticker=pos.ticker,
                    )
                    continue

                # Mark price = midpoint of bid/ask, stored as integer cents.
                # Midpoints can be half-cent (e.g., 50/51 -> 50.5), so we round half-up
                # to the nearest cent to match this repo's round-to-cent policy (DEBT-025).
                if pos.side == "yes":
                    mark_price = (yes_bid + yes_ask + 1) // 2
                else:
                    # For NO positions, use NO side midpoint
                    mark_price = (no_bid + no_ask + 1) // 2

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
                    exc_info=True,
                )
                continue

    logger.info("Updated mark prices", count=updated_count)
    return updated_count
