"""Data fetching orchestrator for syncing from Kalshi API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

import structlog
from sqlalchemy import select, update

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
        """Convert API market to price snapshot.

        Uses computed properties that prefer new dollar fields over legacy cent fields.
        Database stores cents (integers) for precision - avoids floating-point rounding issues.
        """
        return PriceSnapshot(
            ticker=api_market.ticker,
            snapshot_time=snapshot_time,
            yes_bid=api_market.yes_bid_cents,
            yes_ask=api_market.yes_ask_cents,
            no_bid=api_market.no_bid_cents,
            no_ask=api_market.no_ask_cents,
            last_price=api_market.last_price_cents,
            volume=api_market.volume,
            volume_24h=api_market.volume_24h,
            open_interest=api_market.open_interest,
        )

    def _api_market_to_settlement(self, api_market: APIMarket) -> DBSettlement | None:
        """Convert a settled API market to a settlement row.

        Notes:
            Prefer `settlement_ts` (added Dec 19, 2025) when available. Fall back to
            `expiration_time` for historical data or older synced markets.
        """
        if not api_market.result:
            return None

        settled_at = api_market.settlement_ts or api_market.expiration_time
        return DBSettlement(
            ticker=api_market.ticker,
            event_ticker=api_market.event_ticker,
            settled_at=settled_at,
            result=api_market.result,
        )

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

            async for api_event in self.client.get_all_events(limit=200, max_pages=max_pages):
                db_event = self._api_event_to_db(api_event)
                await repo.upsert(db_event)
                count += 1

                if count % 100 == 0:
                    await session.flush()
                    logger.info("Synced events so far", count=count)

            if include_multivariate:
                async for api_event in self.client.get_all_multivariate_events(
                    limit=200,
                    max_pages=max_pages,
                ):
                    db_event = self._api_event_to_db(api_event)
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

                db_market = self._api_market_to_db(api_market)
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
                settlement = self._api_market_to_settlement(api_market)
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
                await market_repo.upsert(self._api_market_to_db(api_market))

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
        logger.info("Taking price snapshot", snapshot_time=snapshot_time.isoformat())
        count = 0

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
                await market_repo.insert_ignore(self._api_market_to_db(api_market))

                snapshot = self._api_market_to_snapshot(api_market, snapshot_time)
                await price_repo.add(snapshot, flush=False)
                count += 1

                # Flush in batches to avoid memory issues (still within transaction)
                if count % 100 == 0:
                    await session.flush()
                    logger.debug("Took snapshots so far", count=count)

        logger.info("Took price snapshots", count=count)
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
