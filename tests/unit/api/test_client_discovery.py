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
    async def test_get_series_fee_changes_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("series_fee_changes_response.json")
        route = respx.get("https://api.elections.kalshi.com/trade-api/v2/series/fee_changes").mock(
            return_value=Response(200, json=response_json)
        )

        async with KalshiPublicClient() as client:
            changes = await client.get_series_fee_changes()

        assert route.called
        assert isinstance(changes, list)
        assert len(changes) == len(response_json["series_fee_change_arr"])
