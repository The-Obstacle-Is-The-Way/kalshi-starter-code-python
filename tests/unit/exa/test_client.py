"""
Exa client tests - mock ONLY at HTTP boundary.

These tests use respx to mock HTTP requests. Everything else
(models, parsing, error handling) uses real implementations.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response

from kalshi_research.exa.client import ExaClient
from kalshi_research.exa.config import ExaConfig
from kalshi_research.exa.exceptions import ExaAuthError


def _client() -> ExaClient:
    return ExaClient(ExaConfig(api_key="test-key"))


@pytest.mark.asyncio
@respx.mock
async def test_search_success_includes_api_key_header() -> None:
    route = respx.post("https://api.exa.ai/search").mock(
        return_value=Response(
            200,
            json={
                "requestId": "req_1",
                "searchType": "auto",
                "results": [
                    {
                        "id": "doc_1",
                        "url": "https://example.com/a",
                        "title": "Example",
                        "score": 0.9,
                    }
                ],
            },
        )
    )

    async with _client() as exa:
        resp = await exa.search("hello", num_results=1)

    assert resp.request_id == "req_1"
    assert resp.results[0].url == "https://example.com/a"
    assert route.call_count == 1
    assert route.calls[0].request.headers.get("x-api-key") == "test-key"


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_contents_object_when_requested() -> None:
    route = respx.post("https://api.exa.ai/search").mock(
        return_value=Response(200, json={"requestId": "req_1", "results": []})
    )

    async with _client() as exa:
        await exa.search("hello", text=True, highlights=True, summary=True)

    assert route.call_count == 1
    body = json.loads(route.calls[0].request.content.decode("utf-8"))
    assert "contents" in body
    assert body["contents"]["text"] is True
    assert body["contents"]["highlights"] == {}
    assert body["contents"]["summary"] == {}


@pytest.mark.asyncio
@respx.mock
async def test_search_and_contents_enables_text_and_highlights_by_default() -> None:
    route = respx.post("https://api.exa.ai/search").mock(
        return_value=Response(200, json={"requestId": "req_1", "results": []})
    )

    async with _client() as exa:
        await exa.search_and_contents("hello", num_results=1)

    assert route.call_count == 1
    body = json.loads(route.calls[0].request.content.decode("utf-8"))
    assert body["contents"]["text"] is True
    assert body["contents"]["highlights"] == {}
    assert "summary" not in body["contents"]


@pytest.mark.asyncio
@respx.mock
async def test_search_401_raises_auth_error() -> None:
    respx.post("https://api.exa.ai/search").mock(return_value=Response(401, text="unauthorized"))

    async with _client() as exa:
        with pytest.raises(ExaAuthError):
            await exa.search("hello")


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_retries_with_retry_after_header() -> None:
    route = respx.post("https://api.exa.ai/search")
    route.side_effect = [
        Response(429, headers={"retry-after": "7"}, text="rate limited"),
        Response(200, json={"requestId": "req_1", "results": []}),
    ]

    with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
        async with _client() as exa:
            await exa.search("hello")

    assert route.call_count == 2
    assert any(call.args and call.args[0] == 7.0 for call in mock_sleep.await_args_list)
