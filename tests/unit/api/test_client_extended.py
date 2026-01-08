"""
Extended API client tests for authenticated endpoints.
"""

from unittest.mock import MagicMock, patch

import pytest
import respx
from httpx import Response

from kalshi_research.api.client import KalshiClient


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
        respx.get("https://api.elections.kalshi.com/trade-api/v2/portfolio/balance").mock(
            return_value=Response(200, json={"balance": 10000})
        )

        async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
            balance = await client.get_balance()

        assert balance["balance"] == 10000

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_positions(self, mock_auth):
        """Test getting positions."""
        respx.get("https://api.elections.kalshi.com/trade-api/v2/portfolio/positions").mock(
            return_value=Response(200, json={"positions": [{"ticker": "TEST", "count": 10}]})
        )

        async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
            positions = await client.get_positions()

        assert len(positions) == 1
        assert positions[0]["ticker"] == "TEST"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_orders(self, mock_auth):
        """Test getting orders."""
        respx.get("https://api.elections.kalshi.com/trade-api/v2/portfolio/orders").mock(
            return_value=Response(200, json={"orders": [{"order_id": "123"}]})
        )

        async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
            orders = await client.get_orders()

        assert len(orders) == 1
        assert orders[0]["order_id"] == "123"

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
