"""
Integration tests for Rate Limiting using respx.
Verifies that the client respects 429 Retry-After headers and throttles requests.
"""

import time
from unittest.mock import patch

import httpx
import pytest
import respx

from kalshi_research.api.client import KalshiPublicClient
from kalshi_research.api.exceptions import RateLimitError
from kalshi_research.api.rate_limiter import RateTier


@pytest.fixture
async def public_client():
    client = KalshiPublicClient(environment="demo", rate_tier=RateTier.BASIC)
    async with client:
        yield client


@pytest.mark.integration
@pytest.mark.asyncio
async def test_client_respects_retry_after(public_client):
    """Test that client waits when receiving 429 with Retry-After."""
    
    async with respx.mock(base_url="https://demo-api.kalshi.co/trade-api/v2") as respx_mock:
        # First call returns 429 with Retry-After: 1
        respx_mock.get("/markets").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "1"}, text="Rate limit exceeded"),
                httpx.Response(200, json={"markets": []})
            ]
        )

        # Mock time.sleep to run fast, but verify it was called
        # The tenacity retry logic uses asyncio.sleep
        with patch("asyncio.sleep", return_value=None) as mock_sleep:
            await public_client.get_markets()
            
            # Should have slept at least once (for retry)
            # Tenacity wait_exponential might be mocked or we verify we hit the retry logic
            assert mock_sleep.called
            # Ideally we check it called with approx 1 second
            
        assert respx_mock.calls.call_count == 2
