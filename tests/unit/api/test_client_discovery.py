"""
Kalshi discovery endpoint tests.

SSOT principle: success-path mocks should use golden fixtures (raw API responses),
and tests should mock only at the HTTP boundary.
"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from kalshi_research.api.client import KalshiPublicClient
from tests.golden_fixtures import load_golden_response


class TestKalshiPublicClientDiscovery:
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_tags_by_categories_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("tags_by_categories_response.json")
        route = respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/search/tags_by_categories"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiPublicClient() as client:
            tags_by_categories = await client.get_tags_by_categories()

        assert route.called
        assert isinstance(tags_by_categories, dict)

        raw_map = response_json.get("tags_by_categories")
        assert isinstance(raw_map, dict)
        first_category = next(iter(raw_map.keys()))
        expected_raw = raw_map.get(first_category)
        expected = expected_raw if isinstance(expected_raw, list) else []
        assert tags_by_categories[first_category] == expected

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_series_list_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("series_list_response.json")
        route = respx.get("https://api.elections.kalshi.com/trade-api/v2/series").mock(
            return_value=Response(200, json=response_json)
        )

        raw_series = response_json.get("series")
        assert isinstance(raw_series, list)
        assert raw_series
        category = raw_series[0]["category"]

        async with KalshiPublicClient() as client:
            series = await client.get_series_list(category=category)

        assert route.called
        assert len(series) == len(response_json["series"])
        assert series[0].ticker == response_json["series"][0]["ticker"]
        assert route.calls[0].request.url.params["category"] == category

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_series_single_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("series_single_response.json")
        series_ticker = response_json["series"]["ticker"]
        route = respx.get(
            f"https://api.elections.kalshi.com/trade-api/v2/series/{series_ticker}"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiPublicClient() as client:
            series = await client.get_series(series_ticker)

        assert route.called
        assert series.ticker == series_ticker

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_event_metadata_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("event_metadata_response.json")
        market_details = response_json.get("market_details")
        assert isinstance(market_details, list) and market_details
        event_ticker = market_details[0]["market_ticker"]

        route = respx.get(
            f"https://api.elections.kalshi.com/trade-api/v2/events/{event_ticker}/metadata"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiPublicClient() as client:
            metadata = await client.get_event_metadata(event_ticker)

        assert route.called
        assert metadata.image_url == response_json["image_url"]
        assert len(metadata.market_details) == len(response_json["market_details"])
        assert len(metadata.settlement_sources) == len(response_json["settlement_sources"])

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_filters_by_sport_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("filters_by_sport_response.json")
        route = respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/search/filters_by_sport"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiPublicClient() as client:
            filters = await client.get_filters_by_sport()

        assert route.called
        assert filters.sport_ordering == response_json["sport_ordering"]
        assert set(filters.filters_by_sports.keys()) == set(
            response_json["filters_by_sports"].keys()
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_event_candlesticks_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("event_candlesticks_response.json")
        series_ticker = "KXELONMARS"
        event_ticker = "KXELONMARS-99"

        route = respx.get(
            f"https://api.elections.kalshi.com/trade-api/v2/series/{series_ticker}/events/{event_ticker}/candlesticks"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiPublicClient() as client:
            candles = await client.get_event_candlesticks(
                series_ticker=series_ticker,
                event_ticker=event_ticker,
                start_ts=1,
                end_ts=2,
                period_interval=1440,
            )

        assert route.called
        assert candles.adjusted_end_ts == response_json["adjusted_end_ts"]
        assert candles.market_tickers == response_json["market_tickers"]
        assert route.calls[0].request.url.params["period_interval"] == "1440"
        assert route.calls[0].request.url.params["start_ts"] == "1"
        assert route.calls[0].request.url.params["end_ts"] == "2"
