"""Unit tests for Phase 2 order operations (SPEC-040)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response

from kalshi_research.api.client import KalshiClient
from kalshi_research.api.models.order import CreateOrderRequest, OrderAction, OrderSide
from tests.golden_fixtures import load_golden_response


@pytest.fixture
def mock_auth() -> None:
    with patch("kalshi_research.api.client.KalshiAuth") as MockAuth:
        mock_auth_instance = MockAuth.return_value
        mock_auth_instance.get_headers.return_value = {"X-Signed": "true"}
        yield


class TestOrderOperationsPhase2:
    """Tests for authenticated order operation endpoints."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_order(self, mock_auth: None) -> None:
        response_json = load_golden_response("portfolio_order_single_response.json")
        route = respx.get("https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/oid-123").mock(
            return_value=Response(200, json=response_json)
        )

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            client._rate_limiter = AsyncMock()
            order = await client.get_order("oid-123")

        assert route.called
        client._rate_limiter.acquire.assert_called_with("GET", "/portfolio/orders/oid-123")
        assert order.order_id == response_json["order"]["order_id"]

    @pytest.mark.asyncio
    async def test_batch_create_orders_rejects_more_than_20(self, mock_auth: None) -> None:
        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            orders = [
                CreateOrderRequest(
                    ticker=f"KXEXAMPLE-{i}",
                    side=OrderSide.YES,
                    action=OrderAction.BUY,
                    count=1,
                    yes_price=50,
                    client_order_id=f"cid-{i}",
                )
                for i in range(21)
            ]
            with pytest.raises(ValueError, match="Maximum 20"):
                await client.batch_create_orders(orders, dry_run=True)

    @pytest.mark.asyncio
    @respx.mock
    async def test_batch_create_orders_posts_payload_and_parses(self, mock_auth: None) -> None:
        response_json = load_golden_response("batch_create_orders_response.json")
        route = respx.post("https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/batched").mock(
            return_value=Response(201, json=response_json)
        )

        orders = [
            CreateOrderRequest(
                ticker="KXEXAMPLE-ORDER",
                side=OrderSide.YES,
                action=OrderAction.BUY,
                count=1,
                yes_price=50,
                client_order_id="cid-1",
            ),
            CreateOrderRequest(
                ticker="KXEXAMPLE-ORDER",
                side=OrderSide.NO,
                action=OrderAction.BUY,
                count=1,
                no_price=40,
                client_order_id="cid-2",
            ),
        ]

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            client._rate_limiter = AsyncMock()
            result = await client.batch_create_orders(orders)

        assert route.called
        client._rate_limiter.acquire.assert_called_with(
            "POST", "/portfolio/orders/batched", batch_size=len(orders)
        )

        payload = json.loads(route.calls[0].request.content.decode("utf-8"))
        assert payload["orders"][0]["yes_price"] == 50
        assert payload["orders"][0]["client_order_id"] == "cid-1"
        assert payload["orders"][1]["no_price"] == 40
        assert payload["orders"][1]["client_order_id"] == "cid-2"

        assert len(result.orders) == len(response_json["orders"])
        assert result.orders[0].order is not None
        assert result.orders[1].error is not None

    @pytest.mark.asyncio
    @respx.mock
    async def test_batch_cancel_orders_sends_ids_and_parses(self, mock_auth: None) -> None:
        response_json = load_golden_response("batch_cancel_orders_response.json")
        route = respx.delete(
            "https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/batched"
        ).mock(return_value=Response(200, json=response_json))

        order_ids = ["oid-1", "oid-2"]
        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            client._rate_limiter = AsyncMock()
            result = await client.batch_cancel_orders(order_ids)

        assert route.called
        client._rate_limiter.acquire.assert_called_with(
            "DELETE", "/portfolio/orders/batched", batch_size=len(order_ids)
        )

        payload = json.loads(route.calls[0].request.content.decode("utf-8"))
        assert payload == {"ids": order_ids}

        assert len(result.orders) == len(response_json["orders"])
        assert result.orders[0].order is not None

    @pytest.mark.asyncio
    @respx.mock
    async def test_decrease_order_posts_payload_and_parses(self, mock_auth: None) -> None:
        response_json = load_golden_response("decrease_order_response.json")
        route = respx.post(
            "https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/oid-123/decrease"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            client._rate_limiter = AsyncMock()
            order = await client.decrease_order("oid-123", reduce_by=1)

        assert route.called
        client._rate_limiter.acquire.assert_called_with(
            "POST", "/portfolio/orders/oid-123/decrease"
        )
        payload = json.loads(route.calls[0].request.content.decode("utf-8"))
        assert payload == {"reduce_by": 1}
        assert order.order_id == response_json["order"]["order_id"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_order_queue_position(self, mock_auth: None) -> None:
        response_json = load_golden_response("order_queue_position_response.json")
        route = respx.get(
            "https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/oid-123/queue_position"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            client._rate_limiter = AsyncMock()
            position = await client.get_order_queue_position("oid-123")

        assert route.called
        client._rate_limiter.acquire.assert_called_with(
            "GET", "/portfolio/orders/oid-123/queue_position"
        )
        assert position == response_json["queue_position"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_orders_queue_positions_with_filters(self, mock_auth: None) -> None:
        response_json = load_golden_response("order_queue_positions_response.json")
        route = respx.get(
            "https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/queue_positions"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            client._rate_limiter = AsyncMock()
            results = await client.get_orders_queue_positions(
                market_tickers=["KXEXAMPLE-ORDER", "KXEXAMPLE-ORDER2"],
                event_ticker="EVT-EXAMPLE",
            )

        assert route.called
        client._rate_limiter.acquire.assert_called_with("GET", "/portfolio/orders/queue_positions")
        params = route.calls[0].request.url.params
        assert params["market_tickers"] == "KXEXAMPLE-ORDER,KXEXAMPLE-ORDER2"
        assert params["event_ticker"] == "EVT-EXAMPLE"
        expected_position = response_json["queue_positions"][0]["queue_position"]
        assert results[0].queue_position == expected_position

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_total_resting_order_value(self, mock_auth: None) -> None:
        response_json = load_golden_response("portfolio_total_resting_order_value_response.json")
        route = respx.get(
            "https://demo-api.kalshi.co/trade-api/v2/portfolio/summary/total_resting_order_value"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            client._rate_limiter = AsyncMock()
            total = await client.get_total_resting_order_value()

        assert route.called
        client._rate_limiter.acquire.assert_called_with(
            "GET", "/portfolio/summary/total_resting_order_value"
        )
        assert total == response_json["total_resting_order_value"]
