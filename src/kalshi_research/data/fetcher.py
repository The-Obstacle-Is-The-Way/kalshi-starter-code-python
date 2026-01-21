"""Data fetching orchestrator for syncing from Kalshi API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

import structlog
from sqlalchemy import select, update

from kalshi_research.api import KalshiPublicClient
from kalshi_research.api.models.market import MarketFilterStatus
from kalshi_research.constants import DEFAULT_PAGINATION_LIMIT
from kalshi_research.data._converters import (
    api_event_to_db,
    api_market_to_db,
    api_market_to_settlement,
    api_market_to_snapshot,
)
from kalshi_research.data.models import Event as DBEvent
from kalshi_research.data.models import Market as DBMarket
from kalshi_research.data.repositories import (
    EventRepository,
    MarketRepository,
    PriceRepository,
    SettlementRepository,
)

if TYPE_CHECKING:
    from types import TracebackType

    from kalshi_research.data.database import DatabaseManager

logger = structlog.get_logger()


class DataFetcher:
    """
    Orchestrates data fetching from Kalshi API and persistence to database.

    This class handles syncing markets, events, and taking price snapshots.
    """

    def __init__(
        self,
        db: DatabaseManager,
        client: KalshiPublicClient | None = None,
    ) -> None:
        """
        Initialize the data fetcher.

        Args:
            db: Database manager for persistence
            client: Optional API client (creates one if not provided)
        """
        self._db = db
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> DataFetcher:
        """Enter async context manager."""
        if self._client is None:
            self._client = KalshiPublicClient()
            await self._client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        if self._owns_client and self._client is not None:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)

    @property
    def client(self) -> KalshiPublicClient:
        """Get the API client."""
        if self._client is None:
            raise RuntimeError("DataFetcher not initialized - use async with")
        return self._client

    async def sync_events(
        self,
        *,
        max_pages: int | None = None,
        include_multivariate: bool = False,
    ) -> int:
        """
        Sync all events from API to database.

        Args:
            max_pages: Optional pagination safety limit. None = iterate until exhausted.
            include_multivariate: When true, also sync events from `GET /events/multivariate`.

        Returns:
            Number of events synced
        """
        logger.info("Starting event sync")
        count = 0

        async with self._db.session_factory() as session, session.begin():
            repo = EventRepository(session)

            async for api_event in self.client.get_all_events(
                limit=DEFAULT_PAGINATION_LIMIT, max_pages=max_pages
            ):
                db_event = api_event_to_db(api_event)
                await repo.upsert(db_event)
                count += 1

                if count % 100 == 0:
                    await session.flush()
                    logger.info("Synced events so far", count=count)

            if include_multivariate:
                async for api_event in self.client.get_all_multivariate_events(
                    limit=DEFAULT_PAGINATION_LIMIT,
                    max_pages=max_pages,
                ):
                    db_event = api_event_to_db(api_event)
                    await repo.upsert(db_event)
                    count += 1

                    if count % 100 == 0:
                        await session.flush()
                        logger.info("Synced events so far", count=count)

            logger.info("Synced events", count=count)
        return count

    async def sync_markets(
        self,
        status: str | None = None,
        *,
        max_pages: int | None = None,
        mve_filter: Literal["only", "exclude"] | None = None,
    ) -> int:
        """
        Sync markets from API to database.

        Args:
            status: Optional filter for market status (open, closed, etc.)
            max_pages: Optional pagination safety limit. None = iterate until exhausted.
            mve_filter: Filter for multivariate events ("only" or "exclude").

        Returns:
            Number of markets synced
        """
        logger.info("Starting market sync", status=status, mve_filter=mve_filter)
        count = 0

        async with self._db.session_factory() as session, session.begin():
            market_repo = MarketRepository(session)
            event_repo = EventRepository(session)

            async for api_market in self.client.get_all_markets(
                status=status, max_pages=max_pages, mve_filter=mve_filter
            ):
                # Ensure event exists first (FK robustness) without racing other writers.
                await event_repo.insert_ignore(
                    DBEvent(
                        ticker=api_market.event_ticker,
                        series_ticker=api_market.series_ticker or api_market.event_ticker,
                        title=api_market.event_ticker,  # Placeholder
                        mutually_exclusive=False,
                    )
                )

                db_market = api_market_to_db(api_market)
                await market_repo.upsert(db_market)
                count += 1

                # Flush in batches to avoid memory issues (still within transaction)
                if count % 100 == 0:
                    await session.flush()
                    logger.info("Synced markets so far", count=count)

            # Denormalize event categories onto markets for offline filtering. Market responses no
            # longer include category data, so we derive it from the parent event when available.
            await session.execute(
                update(DBMarket)
                .where(DBMarket.category.is_(None))
                .values(
                    category=select(DBEvent.category)
                    .where(DBEvent.ticker == DBMarket.event_ticker)
                    .scalar_subquery()
                )
            )

        logger.info("Synced total markets", count=count)
        return count

    async def sync_settlements(self, *, max_pages: int | None = None) -> int:
        """
        Sync settled market outcomes from API to database.

        This uses the public markets endpoint with the `settled` filter and materializes rows in the
        `settlements` table for backtesting and analysis.

        Args:
            max_pages: Optional pagination safety limit. None = iterate until exhausted.

        Returns:
            Number of settlements synced
        """
        logger.info("Starting settlement sync")
        count = 0
        skipped = 0

        async with self._db.session_factory() as session, session.begin():
            settlement_repo = SettlementRepository(session)
            market_repo = MarketRepository(session)
            event_repo = EventRepository(session)

            async for api_market in self.client.get_all_markets(
                status=MarketFilterStatus.SETTLED, max_pages=max_pages
            ):
                settlement = api_market_to_settlement(api_market)
                if settlement is None:
                    skipped += 1
                    continue

                # Ensure event exists first (FK robustness) without racing other writers.
                await event_repo.insert_ignore(
                    DBEvent(
                        ticker=api_market.event_ticker,
                        series_ticker=api_market.series_ticker or api_market.event_ticker,
                        title=api_market.event_ticker,  # Placeholder
                        mutually_exclusive=False,
                    )
                )

                # Ensure market row exists (FK constraint)
                await market_repo.upsert(api_market_to_db(api_market))

                await settlement_repo.upsert(settlement)
                count += 1

                # Flush in batches to avoid memory issues (still within transaction)
                if count % 100 == 0:
                    await session.flush()
                    logger.info("Synced settlements so far", count=count)

        logger.info("Synced total settlements", count=count, skipped=skipped)
        return count

    async def take_snapshot(
        self, status: str | None = "open", *, max_pages: int | None = None
    ) -> int:
        """
        Take a price snapshot of all markets.

        Notes:
            - Robust to missing market rows: upserts minimal Market records before inserting
              snapshots to satisfy foreign key constraints.
            - Markets missing required `*_dollars` quotes are skipped (logged) to avoid inserting
              NULL quote values into the database.

        Args:
            status: Optional filter for market status (default: open)
            max_pages: Optional pagination safety limit. None = iterate until exhausted.

        Returns:
            Number of snapshots taken
        """
        snapshot_time = datetime.now(UTC)
        logger.info("Taking price snapshot", snapshot_time=snapshot_time.isoformat())
        count = 0
        skipped_missing_quotes = 0

        async with self._db.session_factory() as session, session.begin():
            price_repo = PriceRepository(session)
            market_repo = MarketRepository(session)
            event_repo = EventRepository(session)

            async for api_market in self.client.get_all_markets(status=status, max_pages=max_pages):
                # Ensure event + market exist (FK robustness) without racing other writers.
                await event_repo.insert_ignore(
                    DBEvent(
                        ticker=api_market.event_ticker,
                        series_ticker=api_market.series_ticker or api_market.event_ticker,
                        title=api_market.event_ticker,  # Placeholder
                        mutually_exclusive=False,
                    )
                )
                await market_repo.insert_ignore(api_market_to_db(api_market))

                try:
                    snapshot = api_market_to_snapshot(api_market, snapshot_time)
                except ValueError as exc:
                    skipped_missing_quotes += 1
                    logger.warning(
                        "Skipping market snapshot due to invalid/missing dollar quotes",
                        ticker=api_market.ticker,
                        error=str(exc),
                    )
                    continue
                await price_repo.add(snapshot, flush=False)
                count += 1

                # Flush in batches to avoid memory issues (still within transaction)
                if count % 100 == 0:
                    await session.flush()
                    logger.debug("Took snapshots so far", count=count)

        logger.info(
            "Took price snapshots",
            count=count,
            skipped_missing_quotes=skipped_missing_quotes,
        )
        return count

    async def full_sync(
        self,
        *,
        max_pages: int | None = None,
        include_multivariate: bool = False,
    ) -> dict[str, int]:
        """
        Perform a full sync: events, markets, and snapshot.

        Args:
            max_pages: Optional pagination safety limit. None = iterate until exhausted.
            include_multivariate: When true, also sync events from `GET /events/multivariate`.

        Returns:
            Dictionary with counts for each sync type
        """
        logger.info("Starting full sync")

        events = await self.sync_events(
            max_pages=max_pages,
            include_multivariate=include_multivariate,
        )
        markets = await self.sync_markets(max_pages=max_pages)
        snapshots = await self.take_snapshot(max_pages=max_pages)

        return {
            "events": events,
            "markets": markets,
            "snapshots": snapshots,
        }
