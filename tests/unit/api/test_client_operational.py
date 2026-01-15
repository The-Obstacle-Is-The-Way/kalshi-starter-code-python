"""
Kalshi operational endpoint tests.

SSOT principle: success-path mocks should use golden fixtures (raw API responses),
and tests should mock only at the HTTP boundary.
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import respx
from httpx import Response

from kalshi_research.api.client import KalshiClient, KalshiPublicClient
from tests.golden_fixtures import load_golden_response


def _parse_rfc3339_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_user_data_timestamp_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("user_data_timestamp_response.json")
        route = respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/exchange/user_data_timestamp"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiPublicClient() as client:
            timestamp = await client.get_user_data_timestamp()

        assert route.called
        assert timestamp.as_of_time == _parse_rfc3339_datetime(response_json["as_of_time"])

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_milestones_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("milestones_list_response.json")
        route = respx.get("https://api.elections.kalshi.com/trade-api/v2/milestones").mock(
            return_value=Response(200, json=response_json)
        )

        async with KalshiPublicClient() as client:
            page = await client.get_milestones(limit=5, cursor="cursor")

        assert route.called
        assert len(page.milestones) == len(response_json["milestones"])
        assert page.cursor == response_json["cursor"]
        assert route.calls[0].request.url.params["limit"] == "5"
        assert route.calls[0].request.url.params["cursor"] == "cursor"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_milestones_caps_limit_to_500(self) -> None:
        route = respx.get("https://api.elections.kalshi.com/trade-api/v2/milestones").mock(
            return_value=Response(200, json={"milestones": [], "cursor": None})
        )

        async with KalshiPublicClient() as client:
            await client.get_milestones(limit=999)

        assert route.called
        assert route.calls[0].request.url.params["limit"] == "500"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_milestone_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("milestone_single_response.json")
        milestone_id = response_json["milestone"]["id"]
        route = respx.get(
            f"https://api.elections.kalshi.com/trade-api/v2/milestones/{milestone_id}"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiPublicClient() as client:
            milestone = await client.get_milestone(milestone_id)

        assert route.called
        assert milestone.id == milestone_id

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_milestone_live_data_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("live_data_milestone_response.json")
        live_data_type = response_json["live_data"]["type"]
        milestone_id = response_json["live_data"]["milestone_id"]

        route = respx.get(
            f"https://api.elections.kalshi.com/trade-api/v2/live_data/{live_data_type}/milestone/{milestone_id}"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiPublicClient() as client:
            live_data = await client.get_milestone_live_data(
                live_data_type=live_data_type, milestone_id=milestone_id
            )

        assert route.called
        assert live_data.type == live_data_type
        assert live_data.milestone_id == milestone_id

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_live_data_batch_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("live_data_batch_response.json")
        milestone_id = response_json["live_datas"][0]["milestone_id"]

        route = respx.get("https://api.elections.kalshi.com/trade-api/v2/live_data/batch").mock(
            return_value=Response(200, json=response_json)
        )

        async with KalshiPublicClient() as client:
            live_datas = await client.get_live_data_batch(milestone_ids=[milestone_id])

        assert route.called
        assert len(live_datas) == len(response_json["live_datas"])
        assert route.calls[0].request.url.params["milestone_ids"] == milestone_id

    @pytest.mark.asyncio
    async def test_get_live_data_batch_rejects_more_than_100_ids(self) -> None:
        async with KalshiPublicClient() as client:
            with pytest.raises(ValueError, match="milestone_ids must contain 1-100 items"):
                await client.get_live_data_batch(milestone_ids=["x"] * 101)

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_incentive_programs_uses_ssot_fixture(self) -> None:
        response_json = load_golden_response("incentive_programs_response.json")
        route = respx.get("https://api.elections.kalshi.com/trade-api/v2/incentive_programs").mock(
            return_value=Response(200, json=response_json)
        )

        async with KalshiPublicClient() as client:
            page = await client.get_incentive_programs(
                status="active",
                incentive_type="liquidity",
                limit=5,
                cursor="cursor",
            )

        assert route.called
        assert len(page.incentive_programs) == len(response_json["incentive_programs"])
        assert page.next_cursor == response_json["next_cursor"]
        assert route.calls[0].request.url.params["status"] == "active"
        assert route.calls[0].request.url.params["type"] == "liquidity"
        assert route.calls[0].request.url.params["limit"] == "5"
        assert route.calls[0].request.url.params["cursor"] == "cursor"


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
