"""Search repository for full-text market and event search."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, and_, cast, column, func, or_, select, table, text

from kalshi_research.data.models import Event, Market, PriceSnapshot
from kalshi_research.data.search_utils import fts_tables_exist, has_fts5_support

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class MarketSearchResult:
    """Result from a market search query."""

    ticker: str
    title: str
    subtitle: str | None
    event_ticker: str
    event_category: str | None
    status: str
    midpoint: float | None
    spread: int | None
    volume_24h: int | None
    close_time: datetime
    expiration_time: datetime


class SearchRepository:
    """Repository for full-text search over markets and events."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with a database session."""
        self._session = session
        self._fts5_checked = False
        self._has_fts5 = False
        self._fts_tables_exist = False

    async def _check_fts5_support(self) -> None:
        """Check FTS5 availability once and cache the result."""
        if self._fts5_checked:
            return
        self._has_fts5 = await has_fts5_support(self._session)
        if self._has_fts5:
            self._fts_tables_exist = await fts_tables_exist(self._session)
        self._fts5_checked = True

    async def search_markets(
        self,
        query: str,
        *,
        status: str | None = None,
        category: str | None = None,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        min_volume: int | None = None,
        max_spread: int | None = None,
        limit: int = 20,
    ) -> Sequence[MarketSearchResult]:
        """Search markets by keyword and filters.

        Args:
            query: Search query (FTS5 syntax if available, otherwise substring match).
            status: Filter by market status (e.g., 'open', 'closed').
            category: Filter by category (case-insensitive substring match).
            event_ticker: Filter by exact event ticker.
            series_ticker: Filter by exact series ticker.
            min_volume: Minimum 24h volume (requires price snapshot).
            max_spread: Maximum spread in cents (requires price snapshot).
            limit: Maximum number of results to return.

        Returns:
            List of matching markets with latest price data.
        """
        await self._check_fts5_support()

        # Build the search query
        if self._has_fts5 and self._fts_tables_exist:
            results = await self._search_markets_fts5(
                query,
                status=status,
                category=category,
                event_ticker=event_ticker,
                series_ticker=series_ticker,
                min_volume=min_volume,
                max_spread=max_spread,
                limit=limit,
            )
        else:
            results = await self._search_markets_like(
                query,
                status=status,
                category=category,
                event_ticker=event_ticker,
                series_ticker=series_ticker,
                min_volume=min_volume,
                max_spread=max_spread,
                limit=limit,
            )

        return results

    async def _search_markets_fts5(
        self,
        query: str,
        *,
        status: str | None = None,
        category: str | None = None,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        min_volume: int | None = None,
        max_spread: int | None = None,
        limit: int = 20,
    ) -> Sequence[MarketSearchResult]:
        """Search using FTS5 virtual tables."""
        # Build latest snapshot CTE
        latest_cte = (
            select(
                PriceSnapshot.ticker,
                func.max(PriceSnapshot.snapshot_time).label("max_time"),
            )
            .group_by(PriceSnapshot.ticker)
            .cte("latest")
        )

        # Create a virtual table reference for the FTS5 table
        market_fts = table(
            "market_fts",
            column("ticker"),
            column("title"),
            column("subtitle"),
            column("event_ticker"),
            column("series_ticker"),
        )

        # Join market_fts with markets, events, and latest snapshots
        stmt = (
            select(
                Market.ticker,
                Market.title,
                Market.subtitle,
                Market.event_ticker,
                Event.category,
                Market.status,
                ((PriceSnapshot.yes_bid + PriceSnapshot.yes_ask) / 2.0).label("midpoint"),
                (PriceSnapshot.yes_ask - PriceSnapshot.yes_bid).label("spread"),
                PriceSnapshot.volume_24h,
                Market.close_time,
                Market.expiration_time,
            )
            .select_from(market_fts)
            .join(Market, market_fts.c.ticker == Market.ticker)
            .join(Event, Market.event_ticker == Event.ticker)
            .outerjoin(latest_cte, Market.ticker == latest_cte.c.ticker)
            .outerjoin(
                PriceSnapshot,
                and_(
                    PriceSnapshot.ticker == Market.ticker,
                    PriceSnapshot.snapshot_time == latest_cte.c.max_time,
                ),
            )
            .where(text("market_fts MATCH :query"))
            .order_by(text("rank"))
        )

        # Apply filters
        conditions = []
        if status:
            conditions.append(Market.status == status)
        if category:
            conditions.append(Event.category.ilike(f"%{category}%"))
        if event_ticker:
            conditions.append(Market.event_ticker == event_ticker)
        if series_ticker:
            conditions.append(Market.series_ticker == series_ticker)
        if min_volume is not None:
            conditions.append(PriceSnapshot.volume_24h >= min_volume)
        if max_spread is not None:
            conditions.append((PriceSnapshot.yes_ask - PriceSnapshot.yes_bid) <= max_spread)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.limit(limit)

        result = await self._session.execute(stmt, {"query": query})
        rows = result.all()

        return [
            MarketSearchResult(
                ticker=row[0],
                title=row[1],
                subtitle=row[2],
                event_ticker=row[3],
                event_category=row[4],
                status=row[5],
                midpoint=row[6],
                spread=row[7],
                volume_24h=row[8],
                close_time=row[9],
                expiration_time=row[10],
            )
            for row in rows
        ]

    async def _search_markets_like(
        self,
        query: str,
        *,
        status: str | None = None,
        category: str | None = None,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        min_volume: int | None = None,
        max_spread: int | None = None,
        limit: int = 20,
    ) -> Sequence[MarketSearchResult]:
        """Search using LIKE fallback (when FTS5 is unavailable)."""
        # Build latest snapshot CTE
        latest_cte = (
            select(
                PriceSnapshot.ticker,
                func.max(PriceSnapshot.snapshot_time).label("max_time"),
            )
            .group_by(PriceSnapshot.ticker)
            .cte("latest")
        )

        # Build the base query
        stmt = (
            select(
                Market.ticker,
                Market.title,
                Market.subtitle,
                Market.event_ticker,
                Event.category,
                Market.status,
                ((PriceSnapshot.yes_bid + PriceSnapshot.yes_ask) / 2.0).label("midpoint"),
                (PriceSnapshot.yes_ask - PriceSnapshot.yes_bid).label("spread"),
                PriceSnapshot.volume_24h,
                Market.close_time,
                Market.expiration_time,
            )
            .select_from(Market)
            .join(Event, Market.event_ticker == Event.ticker)
            .outerjoin(latest_cte, Market.ticker == latest_cte.c.ticker)
            .outerjoin(
                PriceSnapshot,
                and_(
                    PriceSnapshot.ticker == Market.ticker,
                    PriceSnapshot.snapshot_time == latest_cte.c.max_time,
                ),
            )
        )

        # Apply keyword search using LIKE
        # Match against title or subtitle
        like_pattern = f"%{query}%"
        search_conditions = [
            cast(Market.title, String).ilike(like_pattern),
        ]
        if query:  # Also search subtitle if query provided
            search_conditions.append(cast(Market.subtitle, String).ilike(like_pattern))

        stmt = stmt.where(or_(*search_conditions))

        # Apply filters
        conditions = []
        if status:
            conditions.append(Market.status == status)
        if category:
            conditions.append(Event.category.ilike(f"%{category}%"))
        if event_ticker:
            conditions.append(Market.event_ticker == event_ticker)
        if series_ticker:
            conditions.append(Market.series_ticker == series_ticker)
        if min_volume is not None:
            conditions.append(PriceSnapshot.volume_24h >= min_volume)
        if max_spread is not None:
            conditions.append((PriceSnapshot.yes_ask - PriceSnapshot.yes_bid) <= max_spread)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            MarketSearchResult(
                ticker=row[0],
                title=row[1],
                subtitle=row[2],
                event_ticker=row[3],
                event_category=row[4],
                status=row[5],
                midpoint=row[6],
                spread=row[7],
                volume_24h=row[8],
                close_time=row[9],
                expiration_time=row[10],
            )
            for row in rows
        ]
