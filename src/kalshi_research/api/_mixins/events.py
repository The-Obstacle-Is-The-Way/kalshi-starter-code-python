"""Events endpoint mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from kalshi_research.api.models.candlestick import EventCandlesticksResponse
from kalshi_research.api.models.event import Event, EventMetadataResponse
from kalshi_research.api.models.market import MarketFilterStatus

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


logger = structlog.get_logger()


class EventsMixin:
    """Mixin providing event-related endpoints."""

    if TYPE_CHECKING:
        # Implemented by ClientBase
        async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]: ...

    async def get_events_page(
        self,
        status: MarketFilterStatus | str | None = None,
        series_ticker: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
        *,
        with_nested_markets: bool = False,
    ) -> tuple[list[Event], str | None]:
        """Fetch a single page of events and return the next cursor (if any)."""
        # Events endpoint max limit is 200 (not 1000 like markets)
        params: dict[str, Any] = {"limit": max(1, min(limit, 200))}
        if status:
            params["status"] = status.value if isinstance(status, MarketFilterStatus) else status
        if series_ticker:
            params["series_ticker"] = series_ticker
        if cursor:
            params["cursor"] = cursor
        if with_nested_markets:
            params["with_nested_markets"] = True

        data = await self._get("/events", params)
        events = [Event.model_validate(e) for e in data.get("events", [])]
        return events, data.get("cursor")

    async def get_events(
        self,
        status: MarketFilterStatus | str | None = None,
        series_ticker: str | None = None,
        limit: int = 100,
        *,
        with_nested_markets: bool = False,
    ) -> list[Event]:
        """Fetch events with optional filters."""
        events, _ = await self.get_events_page(
            status=status,
            series_ticker=series_ticker,
            limit=limit,
            with_nested_markets=with_nested_markets,
        )
        return events

    async def get_all_events(
        self,
        status: MarketFilterStatus | str | None = None,
        series_ticker: str | None = None,
        limit: int = 200,
        max_pages: int | None = None,
        *,
        with_nested_markets: bool = False,
    ) -> AsyncIterator[Event]:
        """
        Iterate through ALL events with automatic pagination.

        Args:
            status: Filter by event status
            series_ticker: Filter by series
            limit: Page size (max 200 for events endpoint)
            max_pages: Optional safety limit. None = iterate until exhausted.

        Yields:
            Event objects

        Warns:
            If max_pages reached but cursor still present (data truncated)
        """
        cursor: str | None = None
        pages = 0
        while True:
            events, cursor = await self.get_events_page(
                status=status,
                series_ticker=series_ticker,
                limit=limit,
                cursor=cursor,
                with_nested_markets=with_nested_markets,
            )

            for event in events:
                yield event

            if not cursor or not events:
                break

            pages += 1

            # Safety limit check with warning
            if max_pages is not None and pages >= max_pages:
                logger.warning(
                    "Pagination truncated: reached max_pages but cursor still present. "
                    "Data may be incomplete. Set max_pages=None for full iteration.",
                    max_pages=max_pages,
                )
                break

    async def get_event(self, event_ticker: str) -> Event:
        """Fetch single event by ticker."""
        data = await self._get(f"/events/{event_ticker}")
        return Event.model_validate(data["event"])

    async def get_event_metadata(self, event_ticker: str) -> EventMetadataResponse:
        """Fetch event metadata for richer event context."""
        data = await self._get(f"/events/{event_ticker}/metadata")
        return EventMetadataResponse.model_validate(data)

    async def get_event_candlesticks(
        self,
        *,
        series_ticker: str,
        event_ticker: str,
        start_ts: int | None = None,
        end_ts: int | None = None,
        period_interval: int = 60,
    ) -> EventCandlesticksResponse:
        """
        Fetch event-level candlestick data (multiple markets aligned by index).

        Args:
            series_ticker: Parent series ticker.
            event_ticker: Event ticker.
            start_ts: Optional start timestamp (Unix seconds).
            end_ts: Optional end timestamp (Unix seconds).
            period_interval: Candle period in minutes (1, 60, or 1440).
        """
        params: dict[str, Any] = {"period_interval": period_interval}
        if start_ts is not None:
            params["start_ts"] = start_ts
        if end_ts is not None:
            params["end_ts"] = end_ts

        data = await self._get(
            f"/series/{series_ticker}/events/{event_ticker}/candlesticks",
            params,
        )
        return EventCandlesticksResponse.model_validate(data)

    async def get_multivariate_events_page(
        self,
        limit: int = 200,
        cursor: str | None = None,
    ) -> tuple[list[Event], str | None]:
        """
        Fetch a single page of multivariate events and return the next cursor (if any).

        Notes:
            Kalshi excludes MVEs from `GET /events`; use `GET /events/multivariate` for MVEs.
            See: docs/_vendor-docs/kalshi-api-reference.md
        """
        params: dict[str, Any] = {"limit": min(limit, 200)}
        if cursor:
            params["cursor"] = cursor

        data = await self._get("/events/multivariate", params)
        events = [Event.model_validate(e) for e in data.get("events", [])]
        return events, data.get("cursor")

    async def get_multivariate_events(self, limit: int = 200) -> list[Event]:
        """Fetch multivariate events (MVEs)."""
        events, _ = await self.get_multivariate_events_page(limit=limit)
        return events

    async def get_all_multivariate_events(
        self,
        limit: int = 200,
        max_pages: int | None = None,
    ) -> AsyncIterator[Event]:
        """
        Iterate through ALL multivariate events with automatic pagination.

        Args:
            limit: Page size (max 200 for events/multivariate endpoint)
            max_pages: Optional safety limit. None = iterate until exhausted.

        Yields:
            Event objects
        """
        cursor: str | None = None
        pages = 0
        while True:
            events, cursor = await self.get_multivariate_events_page(
                limit=limit,
                cursor=cursor,
            )

            for event in events:
                yield event

            if not cursor or not events:
                break

            pages += 1

            if max_pages is not None and pages >= max_pages:
                logger.warning(
                    "Pagination truncated: reached max_pages but cursor still present. "
                    "Data may be incomplete. Set max_pages=None for full iteration.",
                    max_pages=max_pages,
                )
                break
