"""Settlement synchronization logic for portfolio syncer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select

from kalshi_research.portfolio.models import PortfolioSettlement

if TYPE_CHECKING:
    from kalshi_research.api.client import KalshiClient
    from kalshi_research.api.models.portfolio import Settlement
    from kalshi_research.data.database import DatabaseManager

logger = structlog.get_logger()


def _normalize_utc(dt: datetime) -> datetime:
    """Normalize datetime to UTC timezone."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


async def sync_settlements(
    client: KalshiClient,
    db: DatabaseManager,
    since: datetime | None = None,
) -> int:
    """
    Fetch settlement history from Kalshi API and update database.

    Args:
        client: Authenticated Kalshi API client.
        db: Database manager for persistence.
        since: Only fetch settlements after this timestamp.

    Returns:
        Number of settlements synced.
    """
    logger.info("Syncing settlements")
    min_ts = int(_normalize_utc(since).timestamp()) if since else None

    # Paginate through settlements
    settlements: list[Settlement] = []
    cursor = None

    while True:
        response = await client.get_settlements(min_ts=min_ts, limit=100, cursor=cursor)
        if not response.settlements:
            break

        settlements.extend(response.settlements)
        cursor = response.cursor
        if not cursor:
            break

    synced_count = 0
    now = datetime.now(UTC)

    async with db.session_factory() as session, session.begin():
        existing_keys_result = await session.execute(
            select(PortfolioSettlement.ticker, PortfolioSettlement.settled_at)
        )
        existing_keys = {(_normalize_utc(row[1]), row[0]) for row in existing_keys_result.all()}

        for settlement in settlements:
            settled_at = datetime.fromisoformat(settlement.settled_time.replace("Z", "+00:00"))
            settled_at_utc = _normalize_utc(settled_at)
            key = (settled_at_utc, settlement.ticker)
            if key in existing_keys:
                continue

            record = PortfolioSettlement(
                ticker=settlement.ticker,
                event_ticker=settlement.event_ticker,
                market_result=settlement.market_result,
                yes_count=settlement.yes_count,
                yes_total_cost=settlement.yes_total_cost,
                no_count=settlement.no_count,
                no_total_cost=settlement.no_total_cost,
                revenue=settlement.revenue,
                fee_cost_dollars=settlement.fee_cost,
                value=settlement.value,
                settled_at=settled_at_utc,
                synced_at=now,
            )
            session.add(record)
            existing_keys.add(key)
            synced_count += 1

            if synced_count % 1000 == 0:
                await session.flush()

    logger.info("Synced new settlements", count=synced_count)
    return synced_count
