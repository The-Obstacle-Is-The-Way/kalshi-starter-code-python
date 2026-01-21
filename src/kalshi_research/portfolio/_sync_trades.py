"""Trade synchronization logic for portfolio syncer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import select

from kalshi_research.portfolio.models import Trade

if TYPE_CHECKING:
    from kalshi_research.api.client import KalshiClient
    from kalshi_research.data.database import DatabaseManager

logger = structlog.get_logger()


async def sync_trades(
    client: KalshiClient,
    db: DatabaseManager,
    since: datetime | None = None,
) -> int:
    """
    Fetch trade history from Kalshi API and update database.

    Args:
        client: Authenticated Kalshi API client.
        db: Database manager for persistence.
        since: Only fetch trades after this timestamp.

    Returns:
        Number of trades synced.
    """
    logger.info("Syncing trades")
    min_ts = int(since.timestamp()) if since else None

    # Paginate through fills
    fills: list[Any] = []
    cursor = None

    while True:
        response = await client.get_fills(min_ts=min_ts, limit=100, cursor=cursor)
        if not response.fills:
            break

        fills.extend(response.fills)
        cursor = response.cursor
        if not cursor:
            break

    synced_count = 0
    now = datetime.now(UTC)

    async with db.session_factory() as session, session.begin():
        # Check for existing trades to avoid duplicates
        # Using kalshi_trade_id for idempotency
        existing_ids_result = await session.execute(select(Trade.kalshi_trade_id))
        existing_ids = set(existing_ids_result.scalars().all())

        for fill in fills:
            # Fill is now a Pydantic model with typed fields
            trade_id = fill.trade_id
            if trade_id in existing_ids:
                continue

            executed_at = datetime.fromisoformat(fill.created_time.replace("Z", "+00:00"))
            side_raw = (fill.side or "yes").lower()
            if side_raw not in {"yes", "no"}:
                logger.warning(
                    "Unknown fill side; skipping",
                    side=side_raw,
                    trade_id=trade_id,
                )
                continue

            action_raw = (fill.action or "buy").lower()
            if action_raw not in {"buy", "sell"}:
                logger.warning(
                    "Unknown fill action; skipping",
                    action=action_raw,
                    trade_id=trade_id,
                )
                continue

            yes_price = fill.yes_price
            if side_raw == "yes":
                price = yes_price
            else:
                no_price = fill.no_price
                price = no_price if no_price is not None else 100 - yes_price
            quantity = fill.count

            trade = Trade(
                kalshi_trade_id=trade_id,
                ticker=fill.ticker,
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
