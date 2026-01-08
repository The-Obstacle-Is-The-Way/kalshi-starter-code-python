"""
Integration tests for Trading API flow using respx.
Verifies the full stack from Client -> Auth -> Network (mocked).
"""


import httpx
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from kalshi_research.api.client import KalshiClient


@pytest.fixture
def temp_private_key(tmp_path):
    """Generate a temporary RSA private key file."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    key_path = tmp_path / "test_key.pem"
    key_path.write_bytes(pem)
    return str(key_path)


@pytest.fixture
async def authenticated_client(temp_private_key):
    """Create a client with real auth logic but dummy credentials."""
    client = KalshiClient(
        key_id="test-key-uuid",
        private_key_path=temp_private_key,
        environment="demo",
    )
    async with client:
        yield client


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_order_flow(authenticated_client):
    """Test full create order flow including auth header generation."""

    # Mock the API endpoint
    async with respx.mock(base_url="https://demo-api.kalshi.co/trade-api/v2") as respx_mock:
        create_route = respx_mock.post("/portfolio/orders").mock(
            return_value=httpx.Response(
                201,
                json={
                    "order": {
                        "order_id": "8a7c8a8a-...",
                        "order_status": "resting"
                    }
                }
            )
        )

        # Execute
        response = await authenticated_client.create_order(
            ticker="KXBTC-25JAN-50000",
            side="yes",
            action="buy",
            count=10,
            price=50
        )

        # Assertions
        assert response.order_id == "8a7c8a8a-..."
        assert response.order_status == "resting"

        # Verify Request
        assert create_route.called
        request = create_route.calls.last.request

        # 1. Check Body
        import json
        body = json.loads(request.content)
        assert body["ticker"] == "KXBTC-25JAN-50000"
        assert body["side"] == "yes"
        assert body["action"] == "buy"
        assert body["count"] == 10
        assert body["yes_price"] == 50
        assert body["type"] == "limit"

        # 2. Check Auth Headers (Critical Security Check)
        assert "KALSHI-ACCESS-KEY" in request.headers
        assert request.headers["KALSHI-ACCESS-KEY"] == "test-key-uuid"
        assert "KALSHI-ACCESS-SIGNATURE" in request.headers
        assert "KALSHI-ACCESS-TIMESTAMP" in request.headers

        # Verify signature is not empty (we can't verify content easily without public key)
        assert len(request.headers["KALSHI-ACCESS-SIGNATURE"]) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cancel_order_flow(authenticated_client):
    """Test cancel order flow."""

    async with respx.mock(base_url="https://demo-api.kalshi.co/trade-api/v2") as respx_mock:
        cancel_route = respx_mock.delete("/portfolio/orders/oid-123").mock(
            return_value=httpx.Response(200, json={"order": {"status": "canceled"}})
        )

        await authenticated_client.cancel_order("oid-123")

        assert cancel_route.called
        request = cancel_route.calls.last.request
        assert request.method == "DELETE"
        assert request.url.path == "/trade-api/v2/portfolio/orders/oid-123"
        assert "KALSHI-ACCESS-SIGNATURE" in request.headers


@pytest.mark.integration
@pytest.mark.asyncio
async def test_amend_order_flow(authenticated_client):
    """Test amend order flow."""

    async with respx.mock(base_url="https://demo-api.kalshi.co/trade-api/v2") as respx_mock:
        amend_route = respx_mock.post("/portfolio/orders/oid-123/amend").mock(
            return_value=httpx.Response(
                200,
                json={"order": {"order_id": "oid-123", "order_status": "executed"}}
            )
        )

        response = await authenticated_client.amend_order("oid-123", price=55)

        assert response.order_status == "executed"

        assert amend_route.called
        request = amend_route.calls.last.request
        import json
        body = json.loads(request.content)
        assert body["yes_price"] == 55
        assert "count" not in body
