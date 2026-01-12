"""
Extended API client tests for authenticated endpoints.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import respx
from httpx import Response

from kalshi_research.api.client import KalshiClient


def _load_golden_fixture(name: str) -> dict[str, object]:
    root = Path(__file__).resolve().parents[3]
    fixture_path = root / "tests" / "fixtures" / "golden" / name
    data = json.loads(fixture_path.read_text())
    response = data["response"]
    if not isinstance(response, dict):
        raise TypeError(f"Unexpected golden fixture shape for {name}: expected object response")
    return response


@pytest.fixture
def mock_auth():
    with patch("kalshi_research.api.client.KalshiAuth") as MockAuth:
        mock_instance = MagicMock()
        mock_instance.get_headers.return_value = {"Authorization": "Test"}
        MockAuth.return_value = mock_instance
        yield MockAuth


class TestKalshiClientAuthenticated:
    """Tests for authenticated KalshiClient methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_balance(self, mock_auth):
        """Test getting account balance."""
        response_json = _load_golden_fixture("portfolio_balance_response.json")
        respx.get("https://api.elections.kalshi.com/trade-api/v2/portfolio/balance").mock(
            return_value=Response(200, json=response_json)
        )

        async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
            balance = await client.get_balance()

        assert balance.balance == response_json["balance"]
        assert balance.portfolio_value == response_json["portfolio_value"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_positions(self, mock_auth):
        """Test getting positions."""
        response_json = _load_golden_fixture("portfolio_positions_response.json")
        respx.get("https://api.elections.kalshi.com/trade-api/v2/portfolio/positions").mock(
            return_value=Response(200, json=response_json)
        )

        async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
            positions = await client.get_positions()

        market_positions = response_json["market_positions"]
        assert isinstance(market_positions, list)
        assert len(positions) == len(market_positions)
        assert positions[0].ticker == market_positions[0]["ticker"]
        assert positions[0].position == market_positions[0]["position"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_positions_requires_market_positions_key(self, mock_auth):
        """Kalshi OpenAPI spec defines `market_positions` (not legacy `positions`)."""
        # If API returns legacy key only, we return empty (not supported)
        respx.get("https://api.elections.kalshi.com/trade-api/v2/portfolio/positions").mock(
            return_value=Response(200, json={"positions": [{"ticker": "TEST", "position": 10}]})
        )

        async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
            positions = await client.get_positions()

        # Legacy key is not supported - we expect market_positions per OpenAPI spec
        assert len(positions) == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_orders(self, mock_auth):
        """Test getting orders."""
        response_json = _load_golden_fixture("portfolio_orders_response.json")
        respx.get("https://api.elections.kalshi.com/trade-api/v2/portfolio/orders").mock(
            return_value=Response(200, json=response_json)
        )

        async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
            result = await client.get_orders()

        orders = response_json["orders"]
        assert isinstance(orders, list)
        assert len(result.orders) == len(orders)
        assert result.orders[0].order_id == orders[0]["order_id"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_fills_includes_zero_timestamps(self, mock_auth):
        """0-valued timestamps should be sent (avoid truthiness traps)."""
        route = respx.get("https://api.elections.kalshi.com/trade-api/v2/portfolio/fills").mock(
            return_value=Response(200, json={"fills": [], "cursor": None})
        )

        async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
            await client.get_fills(min_ts=0, max_ts=0, limit=500)

        assert route.called
        params = dict(route.calls[0].request.url.params)
        assert params["min_ts"] == "0"
        assert params["max_ts"] == "0"
        assert params["limit"] == "200"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_settlements_includes_zero_timestamps(self, mock_auth):
        """0-valued timestamps should be sent (avoid truthiness traps)."""
        route = respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/portfolio/settlements"
        ).mock(return_value=Response(200, json={"settlements": [], "cursor": None}))

        async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
            await client.get_settlements(min_ts=0, max_ts=0, limit=500)

        assert route.called
        params = dict(route.calls[0].request.url.params)
        assert params["min_ts"] == "0"
        assert params["max_ts"] == "0"
        assert params["limit"] == "200"
