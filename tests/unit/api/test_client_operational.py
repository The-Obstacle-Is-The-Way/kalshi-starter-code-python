"""
Kalshi operational endpoint tests.

SSOT principle: success-path mocks should use golden fixtures (raw API responses),
and tests should mock only at the HTTP boundary.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import respx
from httpx import Response

from kalshi_research.api.client import KalshiClient, KalshiPublicClient
from tests.golden_fixtures import load_golden_response


@pytest.fixture
def mock_auth():
    with patch("kalshi_research.api.client.KalshiAuth") as MockAuth:
        mock_instance = MagicMock()
        mock_instance.get_headers.return_value = {"Authorization": "Test"}
        MockAuth.return_value = mock_instance
        yield MockAuth


class TestKalshiPublicClientOperational:
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_exchange_schedule_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("exchange_schedule_response.json")
        route = respx.get("https://api.elections.kalshi.com/trade-api/v2/exchange/schedule").mock(
            return_value=Response(200, json=response_json)
        )

        async with KalshiPublicClient() as client:
            schedule = await client.get_exchange_schedule()

        assert route.called
        assert (
            schedule.schedule.standard_hours[0].thursday[0].open_time
            == response_json["schedule"]["standard_hours"][0]["thursday"][0]["open_time"]
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_exchange_announcements_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("exchange_announcements_response.json")
        route = respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/exchange/announcements"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiPublicClient() as client:
            announcements = await client.get_exchange_announcements()

        assert route.called
        assert len(announcements.announcements) == len(response_json["announcements"])


class TestKalshiClientOrderGroups:
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_order_groups_uses_ssot_fixture(self, mock_auth) -> None:
        response_json = load_golden_response("order_groups_list_response.json")
        route = respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/portfolio/order_groups"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
            groups = await client.get_order_groups()

        assert route.called
        assert len(groups) == len(response_json["order_groups"])

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_order_group_uses_ssot_fixture(self, mock_auth) -> None:
        response_json = load_golden_response("order_group_create_response.json")
        route = respx.post(
            "https://api.elections.kalshi.com/trade-api/v2/portfolio/order_groups/create"
        ).mock(return_value=Response(201, json=response_json))

        async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
            order_group_id = await client.create_order_group(contracts_limit=1)

        assert route.called
        assert order_group_id == response_json["order_group_id"]

        payload = json.loads(route.calls[0].request.content.decode("utf-8"))
        assert payload == {"contracts_limit": 1}

    @pytest.mark.asyncio
    async def test_create_order_group_rejects_invalid_limit(self, mock_auth) -> None:
        async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
            with pytest.raises(ValueError, match="contracts_limit must be positive"):
                await client.create_order_group(contracts_limit=0)

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_order_group_uses_ssot_fixture(self, mock_auth) -> None:
        response_json = load_golden_response("order_group_single_response.json")
        order_group_id = load_golden_response("order_group_create_response.json")["order_group_id"]

        route = respx.get(
            f"https://api.elections.kalshi.com/trade-api/v2/portfolio/order_groups/{order_group_id}"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
            detail = await client.get_order_group(order_group_id)

        assert route.called
        assert detail.is_auto_cancel_enabled == response_json["is_auto_cancel_enabled"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_reset_order_group_uses_ssot_fixture(self, mock_auth) -> None:
        response_json = load_golden_response("order_group_reset_response.json")
        order_group_id = load_golden_response("order_group_create_response.json")["order_group_id"]

        route = respx.put(
            f"https://api.elections.kalshi.com/trade-api/v2/portfolio/order_groups/{order_group_id}/reset"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
            await client.reset_order_group(order_group_id)

        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_order_group_uses_ssot_fixture(self, mock_auth) -> None:
        response_json = load_golden_response("order_group_delete_response.json")
        order_group_id = load_golden_response("order_group_create_response.json")["order_group_id"]

        route = respx.delete(
            f"https://api.elections.kalshi.com/trade-api/v2/portfolio/order_groups/{order_group_id}"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
            await client.delete_order_group(order_group_id)

        assert route.called
