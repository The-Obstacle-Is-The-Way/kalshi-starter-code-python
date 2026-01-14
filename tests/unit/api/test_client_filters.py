"""
API client filter parameter tests - TDD per SPEC-040 Phase 1.

Tests for market filter parameters:
- tickers (comma-separated batch lookup)
- Timestamp filters (min/max_created_ts, min/max_close_ts, min/max_settled_ts)
- Validation of incompatible timestamp family combinations
"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from kalshi_research.api.client import KalshiPublicClient


class TestMarketFilterParameters:
    """Tests for GET /markets filter parameters (SPEC-040 Phase 1)."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_markets_with_tickers_filter(self) -> None:
        """GET /markets with tickers param sends comma-separated list."""
        route = respx.get("https://api.elections.kalshi.com/trade-api/v2/markets").mock(
            return_value=Response(200, json={"markets": [], "cursor": None})
        )

        async with KalshiPublicClient() as client:
            await client.get_markets_page(tickers=["TICKER-A", "TICKER-B"])

        assert route.called
        assert route.calls[0].request.url.params["tickers"] == "TICKER-A,TICKER-B"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_markets_with_single_ticker(self) -> None:
        """GET /markets with single ticker in list."""
        route = respx.get("https://api.elections.kalshi.com/trade-api/v2/markets").mock(
            return_value=Response(200, json={"markets": [], "cursor": None})
        )

        async with KalshiPublicClient() as client:
            await client.get_markets_page(tickers=["SINGLE-TICKER"])

        assert route.called
        assert route.calls[0].request.url.params["tickers"] == "SINGLE-TICKER"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_markets_with_empty_tickers_omits_param(self) -> None:
        """GET /markets with empty tickers list omits the parameter."""
        route = respx.get("https://api.elections.kalshi.com/trade-api/v2/markets").mock(
            return_value=Response(200, json={"markets": [], "cursor": None})
        )

        async with KalshiPublicClient() as client:
            await client.get_markets_page(tickers=[])

        assert route.called
        assert "tickers" not in route.calls[0].request.url.params

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_markets_with_created_ts_filter(self) -> None:
        """GET /markets with min_created_ts/max_created_ts."""
        route = respx.get("https://api.elections.kalshi.com/trade-api/v2/markets").mock(
            return_value=Response(200, json={"markets": [], "cursor": None})
        )

        async with KalshiPublicClient() as client:
            await client.get_markets_page(
                min_created_ts=1700000000,
                max_created_ts=1700100000,
            )

        assert route.called
        params = route.calls[0].request.url.params
        assert params["min_created_ts"] == "1700000000"
        assert params["max_created_ts"] == "1700100000"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_markets_with_close_ts_filter(self) -> None:
        """GET /markets with min_close_ts/max_close_ts."""
        route = respx.get("https://api.elections.kalshi.com/trade-api/v2/markets").mock(
            return_value=Response(200, json={"markets": [], "cursor": None})
        )

        async with KalshiPublicClient() as client:
            await client.get_markets_page(
                min_close_ts=1700000000,
                max_close_ts=1700100000,
            )

        assert route.called
        params = route.calls[0].request.url.params
        assert params["min_close_ts"] == "1700000000"
        assert params["max_close_ts"] == "1700100000"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_markets_with_settled_ts_filter(self) -> None:
        """GET /markets with min_settled_ts/max_settled_ts."""
        route = respx.get("https://api.elections.kalshi.com/trade-api/v2/markets").mock(
            return_value=Response(200, json={"markets": [], "cursor": None})
        )

        async with KalshiPublicClient() as client:
            await client.get_markets_page(
                min_settled_ts=1700000000,
                max_settled_ts=1700100000,
            )

        assert route.called
        params = route.calls[0].request.url.params
        assert params["min_settled_ts"] == "1700000000"
        assert params["max_settled_ts"] == "1700100000"

    @pytest.mark.asyncio
    async def test_get_markets_rejects_mixed_timestamp_families(self) -> None:
        """Cannot mix created_ts and close_ts filters (OpenAPI constraint)."""
        async with KalshiPublicClient() as client:
            with pytest.raises(ValueError, match="Only one timestamp filter family"):
                await client.get_markets_page(
                    min_created_ts=1700000000,
                    min_close_ts=1700100000,  # Invalid: mixing families
                )

    @pytest.mark.asyncio
    async def test_get_markets_rejects_created_and_settled_ts_mix(self) -> None:
        """Cannot mix created_ts and settled_ts filters."""
        async with KalshiPublicClient() as client:
            with pytest.raises(ValueError, match="Only one timestamp filter family"):
                await client.get_markets_page(
                    max_created_ts=1700000000,
                    min_settled_ts=1700100000,  # Invalid: mixing families
                )

    @pytest.mark.asyncio
    async def test_get_markets_rejects_close_and_settled_ts_mix(self) -> None:
        """Cannot mix close_ts and settled_ts filters."""
        async with KalshiPublicClient() as client:
            with pytest.raises(ValueError, match="Only one timestamp filter family"):
                await client.get_markets_page(
                    max_close_ts=1700000000,
                    max_settled_ts=1700100000,  # Invalid: mixing families
                )

    @pytest.mark.asyncio
    async def test_get_markets_rejects_all_three_ts_families(self) -> None:
        """Cannot use all three timestamp families."""
        async with KalshiPublicClient() as client:
            with pytest.raises(ValueError, match="Only one timestamp filter family"):
                await client.get_markets_page(
                    min_created_ts=1700000000,
                    min_close_ts=1700100000,
                    min_settled_ts=1700200000,  # Invalid: all three families
                )

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_markets_allows_tickers_with_timestamp_filter(self) -> None:
        """tickers param can be combined with any timestamp filter family."""
        route = respx.get("https://api.elections.kalshi.com/trade-api/v2/markets").mock(
            return_value=Response(200, json={"markets": [], "cursor": None})
        )

        async with KalshiPublicClient() as client:
            await client.get_markets_page(
                tickers=["TICKER-A", "TICKER-B"],
                min_created_ts=1700000000,
            )

        assert route.called
        params = route.calls[0].request.url.params
        assert params["tickers"] == "TICKER-A,TICKER-B"
        assert params["min_created_ts"] == "1700000000"
