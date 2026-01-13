"""
Exa client tests - mock ONLY at HTTP boundary.

These tests use respx to mock HTTP requests. Everything else
(models, parsing, error handling) uses real implementations.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response

from kalshi_research.exa.client import ExaClient
from kalshi_research.exa.config import ExaConfig
from kalshi_research.exa.exceptions import ExaAPIError, ExaAuthError, ExaRateLimitError
from kalshi_research.exa.models.common import (
    ContextOptions,
    HighlightsOptions,
    SummaryOptions,
    TextContentsOptions,
)


def _client() -> ExaClient:
    return ExaClient(ExaConfig(api_key="test-key"))


def _load_golden_exa_fixture(name: str) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    fixture_path = root / "tests" / "fixtures" / "golden" / "exa" / name
    data = json.loads(fixture_path.read_text())
    response = data["response"]
    if not isinstance(response, dict):
        raise TypeError(f"Unexpected Exa golden fixture shape for {name}: expected object response")
    return response


@pytest.mark.asyncio
@respx.mock
async def test_search_success_includes_api_key_header() -> None:
    response_json = _load_golden_exa_fixture("search_response.json")
    route = respx.post("https://api.exa.ai/search").mock(
        return_value=Response(
            200,
            json=response_json,
        )
    )

    async with _client() as exa:
        resp = await exa.search("hello", num_results=1)

    assert resp.request_id == response_json["requestId"]
    assert resp.results[0].url == response_json["results"][0]["url"]
    assert route.call_count == 1
    assert route.calls[0].request.headers.get("x-api-key") == "test-key"


@pytest.mark.asyncio
@respx.mock
async def test_search_sends_contents_object_when_requested() -> None:
    route = respx.post("https://api.exa.ai/search").mock(
        return_value=Response(200, json={"requestId": "req_1", "results": []})
    )

    async with _client() as exa:
        await exa.search("hello", text=True, highlights=True, summary=True, context=True)

    assert route.call_count == 1
    body = json.loads(route.calls[0].request.content.decode("utf-8"))
    assert "contents" in body
    assert body["contents"]["text"] is True
    assert body["contents"]["highlights"] == {}
    assert body["contents"]["summary"] == {}
    assert body["contents"]["context"] is True


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
async def test_search_serializes_datetime_fields() -> None:
    route = respx.post("https://api.exa.ai/search").mock(
        return_value=Response(200, json={"requestId": "req_dt", "results": []})
    )

    start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

    async with _client() as exa:
        await exa.search("hello", start_published_date=start)

    assert route.call_count == 1
    body = json.loads(route.calls[0].request.content.decode("utf-8"))
    assert isinstance(body["startPublishedDate"], str)
    assert body["startPublishedDate"].startswith("2026-01-01T00:00:00")


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
    response_json = _load_golden_exa_fixture("get_contents_response.json")
    route = respx.post("https://api.exa.ai/contents").mock(
        return_value=Response(
            200,
            json=response_json,
        )
    )

    async with _client() as exa:
        resp = await exa.get_contents(["https://example.com/a"], text=True)

    assert resp.request_id == response_json["requestId"]
    assert resp.results[0].text == response_json["results"][0]["text"]
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
async def test_find_similar_omits_contents_when_all_options_disabled() -> None:
    route = respx.post("https://api.exa.ai/findSimilar").mock(
        return_value=Response(200, json={"requestId": "req_similar_2", "results": []})
    )

    async with _client() as exa:
        await exa.find_similar("https://example.com/a", num_results=1)

    assert route.call_count == 1
    body = json.loads(route.calls[0].request.content.decode("utf-8"))
    assert "contents" not in body


@pytest.mark.asyncio
@respx.mock
async def test_answer_success() -> None:
    response_json = _load_golden_exa_fixture("answer_response.json")
    respx.post("https://api.exa.ai/answer").mock(
        return_value=Response(
            200,
            json=response_json,
        )
    )

    async with _client() as exa:
        resp = await exa.answer("meaning of life", text=False)

    assert resp.answer == response_json["answer"]
    assert resp.cost_dollars is not None
    assert resp.cost_dollars.total == response_json["costDollars"]["total"]


@pytest.mark.asyncio
@respx.mock
async def test_search_accepts_option_objects() -> None:
    route = respx.post("https://api.exa.ai/search").mock(
        return_value=Response(200, json={"requestId": "req_opt", "results": []})
    )

    async with _client() as exa:
        await exa.search(
            "hello",
            text=TextContentsOptions(max_characters=100),
            highlights=HighlightsOptions(query="q"),
            summary=SummaryOptions(query="s"),
            context=ContextOptions(max_characters=50),
        )

    assert route.call_count == 1
    body = json.loads(route.calls[0].request.content.decode("utf-8"))
    assert body["contents"]["text"]["maxCharacters"] == 100
    assert body["contents"]["highlights"]["query"] == "q"
    assert body["contents"]["summary"]["query"] == "s"
    assert body["contents"]["context"]["maxCharacters"] == 50


@pytest.mark.asyncio
async def test_client_property_raises_when_not_open() -> None:
    client = _client()
    with pytest.raises(RuntimeError):
        _ = client.client


@pytest.mark.asyncio
async def test_open_and_close_are_idempotent() -> None:
    client = _client()

    await client.open()
    await client.open()

    await client.close()
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_create_research_task_posts_payload() -> None:
    response_json = _load_golden_exa_fixture("research_task_create_response.json")
    route = respx.post("https://api.exa.ai/research/v1").mock(
        return_value=Response(
            200,
            json=response_json,
        )
    )

    async with _client() as exa:
        task = await exa.create_research_task(
            instructions="Do the thing",
            output_schema={"type": "object"},
        )

    assert task.research_id == response_json["researchId"]
    assert route.call_count == 1
    body = json.loads(route.calls[0].request.content.decode("utf-8"))
    assert body["instructions"] == "Do the thing"
    assert body["outputSchema"] == {"type": "object"}


@pytest.mark.asyncio
@respx.mock
async def test_list_research_tasks_success() -> None:
    response_json = _load_golden_exa_fixture("research_task_list_response.json")
    route = respx.get("https://api.exa.ai/research/v1").mock(
        return_value=Response(
            200,
            json=response_json,
        )
    )

    async with _client() as exa:
        resp = await exa.list_research_tasks(limit=1)

    assert route.call_count == 1
    assert route.calls[0].request.url.params.get("limit") == "1"
    assert resp.has_more == response_json["hasMore"]
    assert resp.next_cursor == response_json["nextCursor"]
    assert len(resp.data) == len(response_json["data"])


@pytest.mark.asyncio
@respx.mock
async def test_find_recent_research_task_fetches_full_task() -> None:
    list_json = _load_golden_exa_fixture("research_task_list_response.json")
    assert isinstance(list_json["data"], list)
    assert list_json["data"]
    research_id = list_json["data"][0]["researchId"]

    terminal_json = _load_golden_exa_fixture("research_task_response.json")

    list_route = respx.get("https://api.exa.ai/research/v1").mock(
        return_value=Response(200, json=list_json)
    )
    get_route = respx.get(f"https://api.exa.ai/research/v1/{research_id}").mock(
        return_value=Response(200, json=terminal_json)
    )

    async with _client() as exa:
        task = await exa.find_recent_research_task(
            instructions_prefix="Summarize https://example.com",
            max_pages=1,
        )

    assert list_route.call_count == 1
    assert get_route.call_count == 1
    assert task is not None
    assert task.research_id == research_id


@pytest.mark.asyncio
@respx.mock
async def test_wait_for_research_polls_until_terminal_status() -> None:
    terminal = _load_golden_exa_fixture("research_task_response.json")
    research_id = terminal["researchId"]

    route = respx.get(f"https://api.exa.ai/research/v1/{research_id}")
    route.side_effect = [
        Response(
            200,
            json={
                "researchId": research_id,
                "status": "pending",
                "createdAt": 1,
                "instructions": "x",
            },
        ),
        Response(200, json=terminal),
    ]

    with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
        async with _client() as exa:
            task = await exa.wait_for_research(research_id, poll_interval=0.0, timeout=1.0)

    assert task.status.value == "completed"
    assert task.output is not None
    assert task.output.content == terminal["output"]["content"]
    assert route.call_count == 2
    assert mock_sleep.await_count >= 1


@pytest.mark.asyncio
@respx.mock
async def test_wait_for_research_times_out() -> None:
    respx.get("https://api.exa.ai/research/v1/r2").mock(
        return_value=Response(
            200,
            json={"researchId": "r2", "status": "pending", "createdAt": 1, "instructions": "x"},
        )
    )

    with patch("kalshi_research.exa.client.time.monotonic", side_effect=[0.0, 2.0]):
        async with _client() as exa:
            with pytest.raises(TimeoutError):
                await exa.wait_for_research("r2", poll_interval=0.0, timeout=1.0)


def test_parse_retry_after_supports_http_date() -> None:
    retry_after = "Wed, 21 Oct 2015 07:28:00 GMT"
    response = Response(429, headers={"retry-after": retry_after})
    assert _client()._parse_retry_after(response) == 0


def test_parse_retry_after_ceils_fractional_seconds() -> None:
    response = Response(429, headers={"retry-after": "1.1"})
    assert _client()._parse_retry_after(response) == 2


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_exhaustion_raises_rate_limit_error() -> None:
    route = respx.post("https://api.exa.ai/search")
    route.side_effect = [
        Response(429, headers={"retry-after": "1"}, text="rate limited"),
        Response(429, headers={"retry-after": "1"}, text="rate limited"),
    ]

    with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
        async with ExaClient(ExaConfig(api_key="test-key", max_retries=2)) as exa:
            with pytest.raises(ExaRateLimitError):
                await exa.search("hello")

    assert route.call_count == 2
    assert mock_sleep.await_count >= 1


@pytest.mark.asyncio
@respx.mock
async def test_request_rejects_invalid_json() -> None:
    respx.post("https://api.exa.ai/search").mock(
        return_value=Response(200, text="{not-json", headers={"Content-Type": "application/json"})
    )

    async with _client() as exa:
        with pytest.raises(ExaAPIError):
            await exa.search("hello")
