"""Markets endpoint mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import structlog

from kalshi_research.api.models.candlestick import (
    Candlestick,
    CandlestickResponse,
)
from kalshi_research.api.models.market import Market, MarketFilterStatus
from kalshi_research.api.models.orderbook import Orderbook
from kalshi_research.api.models.trade import Trade
from kalshi_research.constants import DEFAULT_ORDERBOOK_DEPTH

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


logger = structlog.get_logger()


class MarketsMixin:
    """Mixin providing market-related endpoints."""

    # Method signature expected from composing class (not implemented here)
    _get: Any  # Provided by ClientBase

    async def get_markets_page(
        self,
        status: MarketFilterStatus | str | None = None,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        tickers: list[str] | None = None,
        min_created_ts: int | None = None,
        max_created_ts: int | None = None,
        min_close_ts: int | None = None,
        max_close_ts: int | None = None,
        min_settled_ts: int | None = None,
        max_settled_ts: int | None = None,
        limit: int = 100,
        cursor: str | None = None,
        mve_filter: Literal["only", "exclude"] | None = None,
    ) -> tuple[list[Market], str | None]:
        """
        Fetch a single page of markets and return the next cursor (if any).

        Args:
            status: Filter by market status (unopened, open, closed, settled).
            event_ticker: Filter by event ticker.
            series_ticker: Filter by series ticker.
            tickers: Batch lookup by comma-separated market tickers.
            min_created_ts: Markets created after this Unix timestamp.
            max_created_ts: Markets created before this Unix timestamp.
            min_close_ts: Markets closing after this Unix timestamp.
            max_close_ts: Markets closing before this Unix timestamp.
            min_settled_ts: Markets settled after this Unix timestamp.
            max_settled_ts: Markets settled before this Unix timestamp.
            limit: Page size (max 1000).
            cursor: Pagination cursor.
            mve_filter: Filter for multivariate events ("only" or "exclude").

        Returns:
            Tuple of (markets, next_cursor).

        Raises:
            ValueError: If multiple timestamp filter families are used together.

        Note:
            Only one timestamp filter family may be used at a time:
            - created_ts: Compatible with status=unopened, open, or empty
            - close_ts: Compatible with status=closed or empty
            - settled_ts: Compatible with status=settled or empty
        """
        # Validate timestamp filter family exclusivity (OpenAPI constraint)
        ts_families_used = sum(
            [
                min_created_ts is not None or max_created_ts is not None,
                min_close_ts is not None or max_close_ts is not None,
                min_settled_ts is not None or max_settled_ts is not None,
            ]
        )
        if ts_families_used > 1:
            raise ValueError(
                "Only one timestamp filter family allowed at a time "
                "(created_ts OR close_ts OR settled_ts)"
            )

        # 1000 is Kalshi API max limit per page (see docs/_vendor-docs/kalshi-api-reference.md)
        params: dict[str, Any] = {"limit": min(limit, 1000)}
        if status:
            params["status"] = status.value if isinstance(status, MarketFilterStatus) else status
        if event_ticker:
            params["event_ticker"] = event_ticker
        if series_ticker:
            params["series_ticker"] = series_ticker
        if tickers:
            params["tickers"] = ",".join(tickers)
        # Add timestamp filters (consolidated to reduce branch count)
        ts_params = {
            "min_created_ts": min_created_ts,
            "max_created_ts": max_created_ts,
            "min_close_ts": min_close_ts,
            "max_close_ts": max_close_ts,
            "min_settled_ts": min_settled_ts,
            "max_settled_ts": max_settled_ts,
        }
        params.update({k: v for k, v in ts_params.items() if v is not None})
        if cursor:
            params["cursor"] = cursor
        if mve_filter:
            params["mve_filter"] = mve_filter

        data = await self._get("/markets", params)
        markets = [Market.model_validate(m) for m in data.get("markets", [])]
        return markets, data.get("cursor")

    async def get_markets(
        self,
        status: MarketFilterStatus | str | None = None,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        limit: int = 100,
        mve_filter: Literal["only", "exclude"] | None = None,
    ) -> list[Market]:
        """
        Fetch markets with optional filters.

        Note: status filter uses different values than response status field.
        Filter: unopened, open, closed, settled
        Response: active, closed, determined, finalized
        """
        if limit <= 0:
            return []

        markets: list[Market] = []
        cursor: str | None = None
        while len(markets) < limit:
            remaining = limit - len(markets)
            page_markets, cursor = await self.get_markets_page(
                status=status,
                event_ticker=event_ticker,
                series_ticker=series_ticker,
                limit=min(remaining, 1000),
                cursor=cursor,
                mve_filter=mve_filter,
            )
            markets.extend(page_markets)
            if cursor is None or not page_markets:
                break

        return markets

    async def get_all_markets(
        self,
        status: MarketFilterStatus | str | None = None,
        limit: int = 1000,
        max_pages: int | None = None,
        mve_filter: Literal["only", "exclude"] | None = None,
    ) -> AsyncIterator[Market]:
        """
        Iterate through ALL markets with automatic pagination.

        Args:
            status: Filter by market status (open, closed, settled)
            limit: Page size (max 1000)
            max_pages: Optional safety limit. None = iterate until exhausted.
            mve_filter: Filter for multivariate events ("only" or "exclude")

        Yields:
            Market objects

        Warns:
            If max_pages reached but cursor still present (data truncated)
        """
        cursor: str | None = None
        pages = 0
        while True:
            markets, cursor = await self.get_markets_page(
                status=status,
                limit=limit,
                cursor=cursor,
                mve_filter=mve_filter,
            )

            for market in markets:
                yield market

            if not cursor or not markets:
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

    async def get_market(self, ticker: str) -> Market:
        """Fetch single market by ticker."""
        data = await self._get(f"/markets/{ticker}")
        return Market.model_validate(data["market"])

    async def get_orderbook(self, ticker: str, depth: int = DEFAULT_ORDERBOOK_DEPTH) -> Orderbook:
        """
        Fetch current orderbook for a market.

        Note: Orderbook returns yes/no bids only (no asks).
        Each is a list of [price, quantity] tuples, or null if empty.
        """
        data = await self._get(f"/markets/{ticker}/orderbook", params={"depth": depth})
        return Orderbook.model_validate(data["orderbook"])

    async def get_trades(
        self,
        ticker: str | None = None,
        limit: int = 100,
        min_ts: int | None = None,
        max_ts: int | None = None,
    ) -> list[Trade]:
        """Fetch public trade history."""
        # 1000 is Kalshi API max limit per page (see docs/_vendor-docs/kalshi-api-reference.md)
        params: dict[str, Any] = {"limit": min(limit, 1000)}
        if ticker:
            params["ticker"] = ticker
        if min_ts is not None:
            params["min_ts"] = min_ts
        if max_ts is not None:
            params["max_ts"] = max_ts

        data = await self._get("/markets/trades", params)
        return [Trade.model_validate(t) for t in data.get("trades", [])]

    async def get_candlesticks(
        self,
        market_tickers: list[str],
        start_ts: int,
        end_ts: int,
        period_interval: int = 60,
    ) -> list[CandlestickResponse]:
        """
        Fetch OHLC candlestick data for multiple markets (batch endpoint).

        Args:
            market_tickers: List of market tickers (max 100)
            start_ts: Start timestamp (Unix seconds)
            end_ts: End timestamp (Unix seconds)
            period_interval: Candle period in minutes (1, 60, or 1440)

        Returns:
            List of CandlestickResponse, one per market
        """
        if len(market_tickers) > 100:
            raise ValueError("Maximum 100 market tickers per request")

        params: dict[str, Any] = {
            "market_tickers": ",".join(market_tickers),
            "start_ts": start_ts,
            "end_ts": end_ts,
            "period_interval": period_interval,
        }

        data = await self._get("/markets/candlesticks", params)
        return [CandlestickResponse.model_validate(m) for m in data.get("markets", [])]

    async def get_series_candlesticks(
        self,
        series_ticker: str,
        ticker: str,
        start_ts: int | None = None,
        end_ts: int | None = None,
        period_interval: int = 60,
    ) -> list[Candlestick]:
        """
        Fetch OHLC candlestick data for a single market within a series.

        Args:
            series_ticker: The series ticker
            ticker: The market ticker
            start_ts: Optional start timestamp (Unix seconds)
            end_ts: Optional end timestamp (Unix seconds)
            period_interval: Candle period in minutes (1, 60, or 1440)
        """
        params: dict[str, Any] = {"period_interval": period_interval}
        if start_ts is not None:
            params["start_ts"] = start_ts
        if end_ts is not None:
            params["end_ts"] = end_ts

        data = await self._get(f"/series/{series_ticker}/markets/{ticker}/candlesticks", params)
        return [Candlestick.model_validate(c) for c in data.get("candlesticks", [])]
