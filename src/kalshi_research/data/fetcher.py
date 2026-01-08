"""Data fetching orchestrator for syncing from Kalshi API."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from kalshi_research.api import KalshiPublicClient
from kalshi_research.api.models.market import MarketFilterStatus
from kalshi_research.data.models import Event as DBEvent
from kalshi_research.data.models import Market as DBMarket
from kalshi_research.data.models import PriceSnapshot
from kalshi_research.data.models import Settlement as DBSettlement
from kalshi_research.data.repositories import (
    EventRepository,
    MarketRepository,
    PriceRepository,
    SettlementRepository,
)

if TYPE_CHECKING:
    from kalshi_research.api.models.event import Event as APIEvent
    from kalshi_research.api.models.market import Market as APIMarket
    from kalshi_research.data.database import DatabaseManager

logger = logging.getLogger(__name__)


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
        exc_tb: object,
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

    def _api_event_to_db(self, api_event: APIEvent) -> DBEvent:
        """Convert API event to database model."""
        return DBEvent(
            ticker=api_event.event_ticker,
            series_ticker=api_event.series_ticker,
            title=api_event.title,
            status=None,  # API doesn't return status for events list
            category=api_event.category,
            mutually_exclusive=False,  # API doesn't return this
        )

    def _api_market_to_db(self, api_market: APIMarket) -> DBMarket:
        """Convert API market to database model."""
        return DBMarket(
            ticker=api_market.ticker,
            event_ticker=api_market.event_ticker,
            series_ticker=api_market.series_ticker,
            title=api_market.title,
            subtitle=api_market.subtitle,
            status=api_market.status.value,
            result=api_market.result,
            open_time=api_market.open_time,
            close_time=api_market.close_time,
            expiration_time=api_market.expiration_time,
            category=None,  # Denormalized from event
            subcategory=None,
        )

    def _api_market_to_snapshot(
        self, api_market: APIMarket, snapshot_time: datetime
    ) -> PriceSnapshot:
        """Convert API market to price snapshot."""
        return PriceSnapshot(
            ticker=api_market.ticker,
            snapshot_time=snapshot_time,
            yes_bid=api_market.yes_bid,
            yes_ask=api_market.yes_ask,
            no_bid=api_market.no_bid,
            no_ask=api_market.no_ask,
            last_price=api_market.last_price,
            volume=api_market.volume,
            volume_24h=api_market.volume_24h,
            open_interest=api_market.open_interest,
            liquidity=api_market.liquidity,
        )

    def _api_market_to_settlement(self, api_market: APIMarket) -> DBSettlement | None:
        """Convert a settled API market to a settlement row.

        Notes:
            Kalshi's public markets endpoint exposes `result` but does not provide a clear
            `settled_at` timestamp. We use `expiration_time` as an explicit proxy for `settled_at`.
        """
        if not api_market.result:
            return None

        return DBSettlement(
            ticker=api_market.ticker,
            event_ticker=api_market.event_ticker,
            settled_at=api_market.expiration_time,
            result=api_market.result,
        )

    async def sync_events(self, *, max_pages: int | None = None) -> int:
        """
        Sync all events from API to database.

        Args:
            max_pages: Optional pagination safety limit. None = iterate until exhausted.

        Returns:
            Number of events synced
        """
        logger.info("Starting event sync")
        count = 0

        async with self._db.session_factory() as session:
            repo = EventRepository(session)

            async for api_event in self.client.get_all_events(limit=200, max_pages=max_pages):
                db_event = self._api_event_to_db(api_event)
                await repo.upsert(db_event)
                count += 1

            await repo.commit()

        logger.info("Synced %d events", count)
        return count

    async def sync_markets(self, status: str | None = None, *, max_pages: int | None = None) -> int:
        """
        Sync markets from API to database.

        Args:
            status: Optional filter for market status (open, closed, etc.)
            max_pages: Optional pagination safety limit. None = iterate until exhausted.

        Returns:
            Number of markets synced
        """
        logger.info("Starting market sync", extra={"status": status})
        count = 0

        async with self._db.session_factory() as session:
            market_repo = MarketRepository(session)
            event_repo = EventRepository(session)

            async for api_market in self.client.get_all_markets(status=status, max_pages=max_pages):
                # Ensure event exists first
                existing_event = await event_repo.get(api_market.event_ticker)
                if existing_event is None:
                    # Create minimal event record
                    event = DBEvent(
                        ticker=api_market.event_ticker,
                        series_ticker=api_market.series_ticker or api_market.event_ticker,
                        title=api_market.event_ticker,  # Placeholder
                    )
                    await event_repo.add(event)

                db_market = self._api_market_to_db(api_market)
                await market_repo.upsert(db_market)
                count += 1

                # Commit in batches to avoid long transactions
                if count % 100 == 0:
                    await session.commit()
                    logger.info("Synced %d markets so far", count)

            await session.commit()

        logger.info("Synced %d total markets", count)
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

        async with self._db.session_factory() as session:
            settlement_repo = SettlementRepository(session)
            market_repo = MarketRepository(session)
            event_repo = EventRepository(session)

            async for api_market in self.client.get_all_markets(
                status=MarketFilterStatus.SETTLED, max_pages=max_pages
            ):
                settlement = self._api_market_to_settlement(api_market)
                if settlement is None:
                    skipped += 1
                    continue

                # Ensure event exists first (FK robustness)
                existing_event = await event_repo.get(api_market.event_ticker)
                if existing_event is None:
                    event = DBEvent(
                        ticker=api_market.event_ticker,
                        series_ticker=api_market.series_ticker or api_market.event_ticker,
                        title=api_market.event_ticker,  # Placeholder
                    )
                    await event_repo.add(event)

                # Ensure market row exists (FK constraint)
                await market_repo.upsert(self._api_market_to_db(api_market))

                await settlement_repo.upsert(settlement)
                count += 1

                # Commit in batches to avoid long transactions
                if count % 100 == 0:
                    await session.commit()
                    logger.info("Synced %d settlements so far", count)

            await session.commit()

        logger.info("Synced %d total settlements (skipped=%d)", count, skipped)
        return count

    async def take_snapshot(
        self, status: str | None = "open", *, max_pages: int | None = None
    ) -> int:
        """
        Take a price snapshot of all markets.

        This method is robust to missing market rows - it will upsert
        minimal Market records before inserting snapshots to satisfy
        foreign key constraints.

        Args:
            status: Optional filter for market status (default: open)
            max_pages: Optional pagination safety limit. None = iterate until exhausted.

        Returns:
            Number of snapshots taken
        """
        snapshot_time = datetime.now(UTC)
        logger.info("Taking price snapshot at %s", snapshot_time.isoformat())
        count = 0

        async with self._db.session_factory() as session:
            price_repo = PriceRepository(session)
            market_repo = MarketRepository(session)
            event_repo = EventRepository(session)

            async for api_market in self.client.get_all_markets(status=status, max_pages=max_pages):
                # Ensure market row exists (FK constraint robustness)
                existing_market = await market_repo.get(api_market.ticker)
                if existing_market is None:
                    # Ensure event exists first
                    existing_event = await event_repo.get(api_market.event_ticker)
                    if existing_event is None:
                        event = DBEvent(
                            ticker=api_market.event_ticker,
                            series_ticker=api_market.series_ticker or api_market.event_ticker,
                            title=api_market.event_ticker,  # Placeholder
                        )
                        await event_repo.add(event)

                    db_market = self._api_market_to_db(api_market)
                    await market_repo.upsert(db_market)

                snapshot = self._api_market_to_snapshot(api_market, snapshot_time)
                await price_repo.add(snapshot)
                count += 1

                # Commit in batches
                if count % 100 == 0:
                    await session.commit()
                    logger.debug("Took %d snapshots so far", count)

            await session.commit()

        logger.info("Took %d price snapshots", count)
        return count

    async def full_sync(self, *, max_pages: int | None = None) -> dict[str, int]:
        """
        Perform a full sync: events, markets, and snapshot.

        Args:
            max_pages: Optional pagination safety limit. None = iterate until exhausted.

        Returns:
            Dictionary with counts for each sync type
        """
        logger.info("Starting full sync")

        events = await self.sync_events(max_pages=max_pages)
        markets = await self.sync_markets(max_pages=max_pages)
        snapshots = await self.take_snapshot(max_pages=max_pages)

        return {
            "events": events,
            "markets": markets,
            "snapshots": snapshots,
        }
