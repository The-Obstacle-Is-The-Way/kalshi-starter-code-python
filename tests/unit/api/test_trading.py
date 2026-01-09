"""Unit tests for trading functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from kalshi_research.api.client import KalshiClient


@pytest.fixture
def mock_client():
    with patch("kalshi_research.api.client.KalshiAuth") as MockAuth:
        # Configure the mock instance that will be returned by KalshiAuth()
        mock_auth_instance = MockAuth.return_value
        mock_auth_instance.get_headers.return_value = {"X-Signed": "true"}

        client = KalshiClient(key_id="test-key", private_key_b64="fake", environment="demo")
        # Mock internal http client
        client._client = AsyncMock(spec=httpx.AsyncClient)
        # Mock rate limiter
        client._rate_limiter = AsyncMock()

        # Ensure the client uses our configured mock auth
        client._auth = mock_auth_instance
        return client


class TestTrading:
    @pytest.mark.asyncio
    async def test_create_order_payload(self, mock_client):
        """Verify create_order sends correct payload."""
        mock_client._client.post.return_value = MagicMock(
            status_code=201,
            json=lambda: {"order": {"order_id": "oid-123", "order_status": "resting"}},
        )

        await mock_client.create_order(
            ticker="KXTEST", side="yes", action="buy", count=10, price=50, client_order_id="cid-1"
        )

        mock_client._client.post.assert_called_once()
        _, kwargs = mock_client._client.post.call_args
        payload = kwargs["json"]

        assert payload["ticker"] == "KXTEST"
        assert payload["side"] == "yes"
        assert payload["action"] == "buy"
        assert payload["count"] == 10
        assert payload["yes_price"] == 50
        assert payload["type"] == "limit"
        assert payload["client_order_id"] == "cid-1"

    @pytest.mark.asyncio
    async def test_create_order_validation(self, mock_client):
        """Verify input validation for create_order."""
        with pytest.raises(ValueError, match="Price must be between"):
            await mock_client.create_order("KX", "yes", "buy", 1, 150)

        with pytest.raises(ValueError, match="Count must be positive"):
            await mock_client.create_order("KX", "yes", "buy", 0, 50)

    @pytest.mark.asyncio
    async def test_cancel_order_rate_limit(self, mock_client):
        """Verify cancel_order uses DELETE and rate limiter."""
        mock_client._client.delete.return_value = MagicMock(
            status_code=200, json=lambda: {"order_id": "oid-123", "status": "canceled"}
        )

        await mock_client.cancel_order("oid-123")

        # Check rate limiter call
        mock_client._rate_limiter.acquire.assert_called_with("DELETE", "/portfolio/orders/oid-123")

        # Check HTTP call
        mock_client._client.delete.assert_called_once()
        args, _ = mock_client._client.delete.call_args
        assert args[0] == "/portfolio/orders/oid-123"

    @pytest.mark.asyncio
    async def test_amend_order(self, mock_client):
        """Verify amend_order payload."""
        mock_client._client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"order": {"order_id": "oid-123", "order_status": "executed"}},
        )

        await mock_client.amend_order("oid-123", price=55)

        mock_client._client.post.assert_called_once()
        args, kwargs = mock_client._client.post.call_args
        assert args[0] == "/portfolio/orders/oid-123/amend"
        assert kwargs["json"] == {"order_id": "oid-123", "yes_price": 55}

    @pytest.mark.asyncio
    async def test_create_order_dry_run(self, mock_client):
        """Verify dry_run mode does not execute order."""
        response = await mock_client.create_order(
            ticker="KXTEST",
            side="yes",
            action="buy",
            count=10,
            price=50,
            client_order_id="cid-dry",
            dry_run=True,
        )

        # Verify no HTTP request was made
        mock_client._client.post.assert_not_called()

        # Verify no rate limit was acquired
        mock_client._rate_limiter.acquire.assert_not_called()

        # Verify simulated response
        assert response.order_id == "dry-run-cid-dry"
        assert response.order_status == "simulated"
