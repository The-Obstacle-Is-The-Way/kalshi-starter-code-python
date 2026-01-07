from __future__ import annotations

import httpx
import pytest
import respx
from httpx import Response

from kalshi_research.api.client import KalshiPublicClient
from kalshi_research.api.exceptions import KalshiAPIError, RateLimitError

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
@respx.mock
async def test_http_400_raises_kalshi_api_error() -> None:
    respx.get("https://api.elections.kalshi.com/trade-api/v2/exchange/status").mock(
        return_value=Response(400, json={"error": "bad request"})
    )

    async with KalshiPublicClient(timeout=1, max_retries=1) as client:
        with pytest.raises(KalshiAPIError) as exc_info:
            await client.get_exchange_status()

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
@respx.mock
async def test_http_401_raises_kalshi_api_error() -> None:
    respx.get("https://api.elections.kalshi.com/trade-api/v2/exchange/status").mock(
        return_value=Response(401, json={"error": "unauthorized"})
    )

    async with KalshiPublicClient(timeout=1, max_retries=1) as client:
        with pytest.raises(KalshiAPIError) as exc_info:
            await client.get_exchange_status()

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
@respx.mock
async def test_http_500_raises_kalshi_api_error_without_retry() -> None:
    route = respx.get("https://api.elections.kalshi.com/trade-api/v2/exchange/status")
    route.mock(return_value=Response(500, json={"error": "server error"}))

    async with KalshiPublicClient(timeout=1, max_retries=3) as client:
        with pytest.raises(KalshiAPIError) as exc_info:
            await client.get_exchange_status()

    assert exc_info.value.status_code == 500
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_http_429_retries_and_succeeds() -> None:
    route = respx.get("https://api.elections.kalshi.com/trade-api/v2/exchange/status")
    route.side_effect = [
        Response(429, json={"error": "rate limited"}),
        Response(200, json={"exchange_active": True, "trading_active": True}),
    ]

    async with KalshiPublicClient(timeout=1, max_retries=2) as client:
        status = await client.get_exchange_status()

    assert status["exchange_active"] is True
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_timeout_retries_and_succeeds() -> None:
    route = respx.get("https://api.elections.kalshi.com/trade-api/v2/exchange/status")
    route.side_effect = [
        httpx.TimeoutException("timeout"),
        Response(200, json={"exchange_active": True, "trading_active": True}),
    ]

    async with KalshiPublicClient(timeout=1, max_retries=2) as client:
        status = await client.get_exchange_status()

    assert status["trading_active"] is True
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_timeout_exhausts_retries_and_raises() -> None:
    route = respx.get("https://api.elections.kalshi.com/trade-api/v2/exchange/status")
    route.side_effect = [httpx.TimeoutException("timeout"), httpx.TimeoutException("timeout")]

    async with KalshiPublicClient(timeout=1, max_retries=2) as client:
        with pytest.raises(httpx.TimeoutException):
            await client.get_exchange_status()

    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_exhausts_retries_and_raises_rate_limit_error() -> None:
    route = respx.get("https://api.elections.kalshi.com/trade-api/v2/exchange/status")
    route.side_effect = [Response(429, json={"error": "rate limited"})] * 2

    async with KalshiPublicClient(timeout=1, max_retries=2) as client:
        with pytest.raises(RateLimitError):
            await client.get_exchange_status()

    assert route.call_count == 2
