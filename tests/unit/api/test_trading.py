"""Unit tests for trading functionality."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

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
        create_order_response = _load_golden_fixture("create_order_response.json")
        mock_client._client.post.return_value = MagicMock(
            status_code=201,
            json=lambda: create_order_response,
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
    async def test_create_order_normalizes_side_and_action(self, mock_client):
        """Verify create_order normalizes side/action casing for string inputs."""
        create_order_response = _load_golden_fixture("create_order_response.json")
        mock_client._client.post.return_value = MagicMock(
            status_code=201,
            json=lambda: create_order_response,
        )

        await mock_client.create_order(
            ticker="KXTEST",
            side="YES",
            action="BUY",
            count=10,
            price=50,
            client_order_id="cid-case",
        )

        mock_client._client.post.assert_called_once()
        _, kwargs = mock_client._client.post.call_args
        payload = kwargs["json"]

        assert payload["side"] == "yes"
        assert payload["action"] == "buy"
        assert payload["yes_price"] == 50
        assert payload["client_order_id"] == "cid-case"

    @pytest.mark.asyncio
    async def test_create_order_no_side_uses_no_price(self, mock_client):
        """Verify create_order uses no_price for NO-side orders (not yes_price)."""
        create_order_response = _load_golden_fixture("create_order_response.json")
        mock_client._client.post.return_value = MagicMock(
            status_code=201,
            json=lambda: create_order_response,
        )

        await mock_client.create_order(
            ticker="KXTEST", side="no", action="buy", count=10, price=30, client_order_id="cid-no"
        )

        mock_client._client.post.assert_called_once()
        _, kwargs = mock_client._client.post.call_args
        payload = kwargs["json"]

        assert payload["ticker"] == "KXTEST"
        assert payload["side"] == "no"
        assert payload["action"] == "buy"
        assert payload["count"] == 10
        # Critical: NO-side orders must use no_price, not yes_price
        assert "no_price" in payload
        assert payload["no_price"] == 30
        assert "yes_price" not in payload

    @pytest.mark.asyncio
    async def test_create_order_with_reduce_only(self, mock_client):
        """Verify reduce_only is passed to API when provided."""
        create_order_response = _load_golden_fixture("create_order_response.json")
        mock_client._client.post.return_value = MagicMock(
            status_code=201,
            json=lambda: create_order_response,
        )

        await mock_client.create_order(
            ticker="KXTEST",
            side="yes",
            action="buy",
            count=10,
            price=50,
            reduce_only=True,
        )

        _, kwargs = mock_client._client.post.call_args
        assert kwargs["json"]["reduce_only"] is True

    @pytest.mark.asyncio
    async def test_create_order_with_post_only(self, mock_client):
        """Verify post_only is passed to API when provided."""
        create_order_response = _load_golden_fixture("create_order_response.json")
        mock_client._client.post.return_value = MagicMock(
            status_code=201,
            json=lambda: create_order_response,
        )

        await mock_client.create_order(
            ticker="KXTEST",
            side="yes",
            action="buy",
            count=10,
            price=50,
            post_only=True,
        )

        _, kwargs = mock_client._client.post.call_args
        assert kwargs["json"]["post_only"] is True

    @pytest.mark.asyncio
    async def test_create_order_with_time_in_force(self, mock_client):
        """Verify time_in_force is passed to API when provided."""
        create_order_response = _load_golden_fixture("create_order_response.json")
        mock_client._client.post.return_value = MagicMock(
            status_code=201,
            json=lambda: create_order_response,
        )

        await mock_client.create_order(
            ticker="KXTEST",
            side="yes",
            action="buy",
            count=10,
            price=50,
            time_in_force="fill_or_kill",
        )

        _, kwargs = mock_client._client.post.call_args
        assert kwargs["json"]["time_in_force"] == "fill_or_kill"

    @pytest.mark.asyncio
    async def test_create_order_safety_params_not_sent_when_none(self, mock_client):
        """Verify optional safety params are NOT sent when not specified."""
        create_order_response = _load_golden_fixture("create_order_response.json")
        mock_client._client.post.return_value = MagicMock(
            status_code=201,
            json=lambda: create_order_response,
        )

        await mock_client.create_order(
            ticker="KXTEST", side="yes", action="buy", count=10, price=50
        )

        _, kwargs = mock_client._client.post.call_args
        payload = kwargs["json"]

        assert "reduce_only" not in payload
        assert "post_only" not in payload
        assert "time_in_force" not in payload

    @pytest.mark.asyncio
    async def test_create_order_accepts_legacy_order_status(self, mock_client):
        """Verify OrderResponse accepts legacy `order_status` key."""
        mock_client._client.post.return_value = MagicMock(
            status_code=201,
            json=lambda: {"order": {"order_id": "oid-123", "order_status": "resting"}},
        )

        response = await mock_client.create_order(
            ticker="KXTEST", side="yes", action="buy", count=10, price=50, client_order_id="cid-1"
        )

        assert response.order_status == "resting"

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
        cancel_order_response = _load_golden_fixture("cancel_order_response.json")
        mock_client._client.delete.return_value = MagicMock(
            status_code=200,
            json=lambda: cancel_order_response,
        )

        response = await mock_client.cancel_order("oid-123")
        assert response.reduced_by == cancel_order_response["reduced_by"]

        # Check rate limiter call
        mock_client._rate_limiter.acquire.assert_called_with("DELETE", "/portfolio/orders/oid-123")

        # Check HTTP call
        mock_client._client.delete.assert_called_once()
        args, _ = mock_client._client.delete.call_args
        assert args[0] == "/portfolio/orders/oid-123"

    @pytest.mark.asyncio
    async def test_amend_order(self, mock_client):
        """Verify amend_order payload."""
        amend_order_response = _load_golden_fixture("amend_order_response.json")
        mock_client._client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: amend_order_response,
        )

        await mock_client.amend_order(
            order_id="oid-123",
            ticker="KXTEST",
            side="yes",
            action="buy",
            client_order_id="cid-1",
            updated_client_order_id="cid-2",
            price=55,
        )

        mock_client._client.post.assert_called_once()
        args, kwargs = mock_client._client.post.call_args
        assert args[0] == "/portfolio/orders/oid-123/amend"
        assert kwargs["json"] == {
            "ticker": "KXTEST",
            "side": "yes",
            "action": "buy",
            "client_order_id": "cid-1",
            "updated_client_order_id": "cid-2",
            "yes_price": 55,
        }

    @pytest.mark.asyncio
    async def test_amend_order_with_count(self, mock_client):
        """Verify amend_order can include count."""
        amend_order_response = _load_golden_fixture("amend_order_response.json")
        mock_client._client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: amend_order_response,
        )

        await mock_client.amend_order(
            order_id="oid-123",
            ticker="KXTEST",
            side="yes",
            action="buy",
            client_order_id="cid-1",
            updated_client_order_id="cid-2",
            price=55,
            count=20,
        )

        _, kwargs = mock_client._client.post.call_args
        assert kwargs["json"]["count"] == 20

    @pytest.mark.asyncio
    async def test_amend_order_with_price_dollars(self, mock_client):
        """Verify amend_order supports fixed-point dollar price."""
        amend_order_response = _load_golden_fixture("amend_order_response.json")
        mock_client._client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: amend_order_response,
        )

        await mock_client.amend_order(
            order_id="oid-123",
            ticker="KXTEST",
            side="yes",
            action="buy",
            client_order_id="cid-1",
            updated_client_order_id="cid-2",
            price_dollars="0.5500",
        )

        _, kwargs = mock_client._client.post.call_args
        payload = kwargs["json"]
        assert payload["yes_price_dollars"] == "0.5500"
        assert "yes_price" not in payload

    @pytest.mark.asyncio
    async def test_amend_order_no_side_uses_no_price(self, mock_client):
        """Verify NO-side amend_order uses no_price fields."""
        amend_order_response = _load_golden_fixture("amend_order_response.json")
        mock_client._client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: amend_order_response,
        )

        await mock_client.amend_order(
            order_id="oid-123",
            ticker="KXTEST",
            side="no",
            action="buy",
            client_order_id="cid-1",
            updated_client_order_id="cid-2",
            price=55,
        )

        _, kwargs = mock_client._client.post.call_args
        payload = kwargs["json"]
        assert payload["no_price"] == 55
        assert "yes_price" not in payload

    @pytest.mark.asyncio
    async def test_amend_order_rejects_price_and_price_dollars(self, mock_client):
        """Verify amend_order rejects setting both cents and dollars prices."""
        with pytest.raises(ValueError, match="Provide only one of price or price_dollars"):
            await mock_client.amend_order(
                order_id="oid-123",
                ticker="KXTEST",
                side="yes",
                action="buy",
                client_order_id="cid-1",
                updated_client_order_id="cid-2",
                price=55,
                price_dollars="0.5500",
            )

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
