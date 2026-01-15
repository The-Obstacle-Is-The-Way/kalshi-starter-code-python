"""Unit tests for Phase 2 order operations (SPEC-040)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response

from kalshi_research.api.client import KalshiClient
from kalshi_research.api.exceptions import KalshiAPIError, RateLimitError
from kalshi_research.api.models.order import CreateOrderRequest, OrderAction, OrderSide, OrderType
from tests.golden_fixtures import load_golden_response


@pytest.fixture
def mock_auth() -> None:
    with patch("kalshi_research.api.client.KalshiAuth") as MockAuth:
        mock_auth_instance = MockAuth.return_value
        mock_auth_instance.get_headers.return_value = {"X-Signed": "true"}
        yield


class TestCreateOrderRequestValidation:
    """Tests for CreateOrderRequest validation rules."""

    def test_limit_order_requires_price(self) -> None:
        with pytest.raises(ValueError, match="Limit orders must provide"):
            CreateOrderRequest(
                ticker="KXEXAMPLE-ORDER",
                side=OrderSide.YES,
                action=OrderAction.BUY,
                count=1,
            )

    def test_market_order_allows_missing_price(self) -> None:
        order = CreateOrderRequest(
            ticker="KXEXAMPLE-ORDER",
            side=OrderSide.YES,
            action=OrderAction.BUY,
            count=1,
            type=OrderType.MARKET,
        )
        assert order.type == OrderType.MARKET


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
    async def test_batch_create_orders_rejects_empty(self, mock_auth: None) -> None:
        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            with pytest.raises(ValueError, match="orders must be non-empty"):
                await client.batch_create_orders([], dry_run=True)

    @pytest.mark.asyncio
    async def test_batch_create_orders_dry_run_returns_empty(self, mock_auth: None) -> None:
        orders = [
            CreateOrderRequest(
                ticker="KXEXAMPLE-ORDER",
                side=OrderSide.YES,
                action=OrderAction.BUY,
                count=1,
                yes_price=50,
                client_order_id="cid-1",
            )
        ]

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            client._rate_limiter = AsyncMock()
            result = await client.batch_create_orders(orders, dry_run=True)

        client._rate_limiter.acquire.assert_not_called()
        assert result.orders == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_batch_create_orders_429_raises_rate_limit_error(self, mock_auth: None) -> None:
        route = respx.post("https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/batched").mock(
            return_value=Response(429, text="rate limit", headers={"Retry-After": "2"})
        )

        orders = [
            CreateOrderRequest(
                ticker="KXEXAMPLE-ORDER",
                side=OrderSide.YES,
                action=OrderAction.BUY,
                count=1,
                yes_price=50,
                client_order_id="cid-1",
            )
        ]

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo", max_retries=1
        ) as client:
            client._rate_limiter = AsyncMock()
            with pytest.raises(RateLimitError) as exc_info:
                await client.batch_create_orders(orders)

        assert route.called
        assert exc_info.value.retry_after == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_batch_create_orders_500_raises(self, mock_auth: None) -> None:
        route = respx.post("https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/batched").mock(
            return_value=Response(500, text="internal error")
        )

        orders = [
            CreateOrderRequest(
                ticker="KXEXAMPLE-ORDER",
                side=OrderSide.YES,
                action=OrderAction.BUY,
                count=1,
                yes_price=50,
                client_order_id="cid-1",
            )
        ]

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo", max_retries=1
        ) as client:
            client._rate_limiter = AsyncMock()
            with pytest.raises(KalshiAPIError) as exc_info:
                await client.batch_create_orders(orders)

        assert route.called
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    @respx.mock
    async def test_batch_create_orders_unexpected_shape_raises(self, mock_auth: None) -> None:
        route = respx.post("https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/batched").mock(
            return_value=Response(201, json=[])
        )

        orders = [
            CreateOrderRequest(
                ticker="KXEXAMPLE-ORDER",
                side=OrderSide.YES,
                action=OrderAction.BUY,
                count=1,
                yes_price=50,
                client_order_id="cid-1",
            )
        ]

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo", max_retries=1
        ) as client:
            client._rate_limiter = AsyncMock()
            with pytest.raises(KalshiAPIError, match="Unexpected batch create response shape"):
                await client.batch_create_orders(orders)

        assert route.called

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
        assert result.orders[1].order is not None
        assert result.orders[0].error is None
        assert result.orders[1].error is None

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
    async def test_batch_cancel_orders_rejects_empty(self, mock_auth: None) -> None:
        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            with pytest.raises(ValueError, match="order_ids must be non-empty"):
                await client.batch_cancel_orders([], dry_run=True)

    @pytest.mark.asyncio
    async def test_batch_cancel_orders_rejects_more_than_20(self, mock_auth: None) -> None:
        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            order_ids = [f"oid-{i}" for i in range(21)]
            with pytest.raises(ValueError, match="Maximum 20"):
                await client.batch_cancel_orders(order_ids, dry_run=True)

    @pytest.mark.asyncio
    async def test_batch_cancel_orders_dry_run_returns_empty(self, mock_auth: None) -> None:
        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            client._rate_limiter = AsyncMock()
            result = await client.batch_cancel_orders(["oid-1"], dry_run=True)

        client._rate_limiter.acquire.assert_not_called()
        assert result.orders == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_batch_cancel_orders_429_raises_rate_limit_error(self, mock_auth: None) -> None:
        route = respx.delete(
            "https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/batched"
        ).mock(return_value=Response(429, text="rate limit", headers={"Retry-After": "5"}))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo", max_retries=1
        ) as client:
            client._rate_limiter = AsyncMock()
            with pytest.raises(RateLimitError) as exc_info:
                await client.batch_cancel_orders(["oid-1"])

        assert route.called
        assert exc_info.value.retry_after == 5

    @pytest.mark.asyncio
    @respx.mock
    async def test_batch_cancel_orders_500_raises(self, mock_auth: None) -> None:
        route = respx.delete(
            "https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/batched"
        ).mock(return_value=Response(500, text="internal error"))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo", max_retries=1
        ) as client:
            client._rate_limiter = AsyncMock()
            with pytest.raises(KalshiAPIError) as exc_info:
                await client.batch_cancel_orders(["oid-1"])

        assert route.called
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    @respx.mock
    async def test_batch_cancel_orders_unexpected_shape_raises(self, mock_auth: None) -> None:
        route = respx.delete(
            "https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/batched"
        ).mock(return_value=Response(200, json=[]))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo", max_retries=1
        ) as client:
            client._rate_limiter = AsyncMock()
            with pytest.raises(KalshiAPIError, match="Unexpected batch cancel response shape"):
                await client.batch_cancel_orders(["oid-1"])

        assert route.called

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("kwargs", "match"),
        [
            ({}, "Must provide reduce_by or reduce_to"),
            ({"reduce_by": 1, "reduce_to": 2}, "Provide only one of reduce_by or reduce_to"),
            ({"reduce_by": 0}, "reduce_by must be positive"),
            ({"reduce_to": -1}, "reduce_to must be non-negative"),
        ],
    )
    async def test_decrease_order_rejects_invalid_args(
        self, kwargs: dict[str, int], match: str, mock_auth: None
    ) -> None:
        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            with pytest.raises(ValueError, match=match):
                await client.decrease_order("oid-123", **kwargs)

    @pytest.mark.asyncio
    @respx.mock
    async def test_decrease_order_dry_run_returns_get_order(self, mock_auth: None) -> None:
        response_json = load_golden_response("portfolio_order_single_response.json")
        get_route = respx.get(
            "https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/oid-123"
        ).mock(return_value=Response(200, json=response_json))
        post_route = respx.post(
            "https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/oid-123/decrease"
        ).mock(return_value=Response(500, text="unexpected post"))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            client._rate_limiter = AsyncMock()
            order = await client.decrease_order("oid-123", reduce_by=1, dry_run=True)

        assert get_route.called
        assert not post_route.called
        assert order.order_id == response_json["order"]["order_id"]

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
    async def test_decrease_order_accepts_reduce_to(self, mock_auth: None) -> None:
        response_json = load_golden_response("decrease_order_response.json")
        route = respx.post(
            "https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/oid-123/decrease"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            client._rate_limiter = AsyncMock()
            await client.decrease_order("oid-123", reduce_to=0)

        assert route.called
        payload = json.loads(route.calls[0].request.content.decode("utf-8"))
        assert payload == {"reduce_to": 0}

    @pytest.mark.asyncio
    @respx.mock
    async def test_decrease_order_429_raises_rate_limit_error(self, mock_auth: None) -> None:
        route = respx.post(
            "https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/oid-123/decrease"
        ).mock(return_value=Response(429, text="rate limit", headers={"Retry-After": "7"}))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo", max_retries=1
        ) as client:
            client._rate_limiter = AsyncMock()
            with pytest.raises(RateLimitError) as exc_info:
                await client.decrease_order("oid-123", reduce_by=1)

        assert route.called
        assert exc_info.value.retry_after == 7

    @pytest.mark.asyncio
    @respx.mock
    async def test_decrease_order_400_raises(self, mock_auth: None) -> None:
        route = respx.post(
            "https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/oid-123/decrease"
        ).mock(return_value=Response(400, text="bad request"))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo", max_retries=1
        ) as client:
            client._rate_limiter = AsyncMock()
            with pytest.raises(KalshiAPIError) as exc_info:
                await client.decrease_order("oid-123", reduce_by=1)

        assert route.called
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @respx.mock
    async def test_decrease_order_unexpected_shape_raises(self, mock_auth: None) -> None:
        route = respx.post(
            "https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/oid-123/decrease"
        ).mock(return_value=Response(200, json=[]))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo", max_retries=1
        ) as client:
            client._rate_limiter = AsyncMock()
            with pytest.raises(KalshiAPIError, match="Unexpected decrease response shape"):
                await client.decrease_order("oid-123", reduce_by=1)

        assert route.called

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
    async def test_get_orders_queue_positions_without_filters(self, mock_auth: None) -> None:
        response_json = load_golden_response("order_queue_positions_response.json")
        route = respx.get(
            "https://demo-api.kalshi.co/trade-api/v2/portfolio/orders/queue_positions"
        ).mock(return_value=Response(200, json=response_json))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            client._rate_limiter = AsyncMock()
            await client.get_orders_queue_positions()

        assert route.called
        client._rate_limiter.acquire.assert_called_with("GET", "/portfolio/orders/queue_positions")
        assert dict(route.calls[0].request.url.params) == {}

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_total_resting_order_value_parses_success(self, mock_auth: None) -> None:
        response_json = {"total_resting_order_value": 12345}
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

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_total_resting_order_value_403_raises(self, mock_auth: None) -> None:
        response_json = load_golden_response("portfolio_total_resting_order_value_response.json")
        route = respx.get(
            "https://demo-api.kalshi.co/trade-api/v2/portfolio/summary/total_resting_order_value"
        ).mock(return_value=Response(403, json=response_json))

        async with KalshiClient(
            key_id="test-key", private_key_b64="fake", environment="demo"
        ) as client:
            client._rate_limiter = AsyncMock()
            with pytest.raises(KalshiAPIError):
                await client.get_total_resting_order_value()

        assert route.called
