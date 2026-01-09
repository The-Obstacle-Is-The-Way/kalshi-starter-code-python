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


@pytest.mark.asyncio
@respx.mock
async def test_get_contents_success() -> None:
    route = respx.post("https://api.exa.ai/contents").mock(
        return_value=Response(
            200,
            json={
                "requestId": "req_contents",
                "results": [
                    {
                        "id": "doc_1",
                        "url": "https://example.com/a",
                        "title": "Example",
                        "score": 0.9,
                        "text": "hello",
                    }
                ],
                "statuses": [{"id": "doc_1", "status": "success"}],
            },
        )
    )

    async with _client() as exa:
        resp = await exa.get_contents(["https://example.com/a"], text=True)

    assert resp.request_id == "req_contents"
    assert resp.results[0].text == "hello"
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_find_similar_sends_contents_object_when_enabled() -> None:
    route = respx.post("https://api.exa.ai/findSimilar").mock(
        return_value=Response(200, json={"requestId": "req_similar", "results": []})
    )

    async with _client() as exa:
        await exa.find_similar("https://example.com/a", num_results=1, text=True, highlights=True)

    assert route.call_count == 1
    body = json.loads(route.calls[0].request.content.decode("utf-8"))
    assert body["contents"]["text"] is True
    assert body["contents"]["highlights"] == {}


@pytest.mark.asyncio
@respx.mock
async def test_answer_success() -> None:
    respx.post("https://api.exa.ai/answer").mock(
        return_value=Response(
            200,
            json={
                "answer": "42",
                "citations": [],
                "costDollars": {"total": 0.01},
            },
        )
    )

    async with _client() as exa:
        resp = await exa.answer("meaning of life", text=False)

    assert resp.answer == "42"
    assert resp.cost_dollars is not None
    assert resp.cost_dollars.total == 0.01


@pytest.mark.asyncio
@respx.mock
async def test_wait_for_research_polls_until_terminal_status() -> None:
    route = respx.get("https://api.exa.ai/research/v1/r1")
    route.side_effect = [
        Response(
            200,
            json={
                "researchId": "r1",
                "status": "pending",
                "createdAt": 1,
                "instructions": "x",
            },
        ),
        Response(
            200,
            json={
                "researchId": "r1",
                "status": "completed",
                "createdAt": 1,
                "instructions": "x",
                "output": {"content": "done"},
            },
        ),
    ]

    with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
        async with _client() as exa:
            task = await exa.wait_for_research("r1", poll_interval=0.0, timeout=1.0)

    assert task.status.value == "completed"
    assert task.output is not None
    assert task.output.content == "done"
    assert route.call_count == 2
    assert mock_sleep.await_count >= 1
