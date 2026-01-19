"""Test Exa Websets client with respx mocking using golden fixtures."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx

from kalshi_research.exa.config import ExaConfig
from kalshi_research.exa.exceptions import ExaAPIError, ExaAuthError, ExaRateLimitError
from kalshi_research.exa.websets.client import ExaWebsetsClient
from kalshi_research.exa.websets.models import (
    CreateWebsetParameters,
    CreateWebsetSearchParameters,
    PreviewWebsetParameters,
)

GOLDEN_WEBSETS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / "fixtures" / "golden" / "exa_websets"
)


def load_golden_fixture(name: str) -> dict:
    """Load a golden fixture response data."""
    fixture_path = GOLDEN_WEBSETS_DIR / f"{name}_response.json"
    with fixture_path.open() as f:
        data = json.load(f)
    return data["response"]


@pytest.fixture
def websets_client() -> ExaWebsetsClient:
    """Create a test Websets client."""
    config = ExaConfig(
        api_key="test_key",
        base_url="https://api.exa.ai",
        timeout_seconds=30.0,
        max_retries=3,
        retry_delay_seconds=0.0,
    )
    return ExaWebsetsClient(config)


@respx.mock
@pytest.mark.asyncio
async def test_create_webset(websets_client: ExaWebsetsClient):
    """Test creating a Webset using golden fixture."""
    fixture_data = load_golden_fixture("create_webset")

    respx.post("https://api.exa.ai/v0/websets").mock(
        return_value=httpx.Response(200, json=fixture_data)
    )

    async with websets_client:
        params = CreateWebsetParameters(
            search=CreateWebsetSearchParameters(
                query="AI startups in Europe",
                count=10,
            ),
            title="Test Webset",
        )
        webset = await websets_client.create_webset(params)

    assert webset.id == "webset_test123"
    assert webset.status.value == "pending"
    assert len(webset.searches) == 1


@respx.mock
@pytest.mark.asyncio
async def test_preview_webset(websets_client: ExaWebsetsClient):
    """Test previewing a Webset using golden fixture."""
    fixture_data = load_golden_fixture("preview_webset")

    respx.post("https://api.exa.ai/v0/websets/preview").mock(
        return_value=httpx.Response(200, json=fixture_data)
    )

    async with websets_client:
        params = PreviewWebsetParameters(
            search=CreateWebsetSearchParameters(
                query="Tech startups",
                count=5,
            )
        )
        response = await websets_client.preview_webset(params)

    assert response.object == "list"
    assert len(response.data) == 1
    assert response.data[0].entity_type.value == "company"


@respx.mock
@pytest.mark.asyncio
async def test_get_webset(websets_client: ExaWebsetsClient):
    """Test getting a Webset using golden fixture."""
    fixture_data = load_golden_fixture("get_webset")

    respx.get("https://api.exa.ai/v0/websets/webset_test123").mock(
        return_value=httpx.Response(200, json=fixture_data)
    )

    async with websets_client:
        response = await websets_client.get_webset("webset_test123")

    assert response.id == "webset_test123"
    assert response.status.value == "running"
    assert len(response.searches) == 1
    assert response.searches[0].found == 8


@respx.mock
@pytest.mark.asyncio
async def test_list_webset_items(websets_client: ExaWebsetsClient):
    """Test listing Webset items using golden fixture."""
    fixture_data = load_golden_fixture("list_webset_items")

    route = respx.get("https://api.exa.ai/v0/websets/webset_test123/items").mock(
        return_value=httpx.Response(200, json=fixture_data)
    )

    async with websets_client:
        response = await websets_client.list_webset_items(
            "webset_test123", cursor="cursor_1", limit=10
        )

    assert response.object == "list"
    assert len(response.data) == 1
    assert response.data[0].id == "item_test789"
    assert not response.has_more
    assert route.calls[0].request.url.params["cursor"] == "cursor_1"


@respx.mock
@pytest.mark.asyncio
async def test_cancel_webset(websets_client: ExaWebsetsClient):
    """Test canceling a Webset."""
    # Use create fixture as cancel returns the updated Webset
    fixture_data = load_golden_fixture("create_webset")
    # Update status to simulate canceled state
    fixture_data["status"] = "paused"

    respx.post("https://api.exa.ai/v0/websets/webset_test123/cancel").mock(
        return_value=httpx.Response(200, json=fixture_data)
    )

    async with websets_client:
        webset = await websets_client.cancel_webset("webset_test123")

    assert webset.id == "webset_test123"
    assert webset.status.value == "paused"


@respx.mock
@pytest.mark.asyncio
async def test_get_webset_item(websets_client: ExaWebsetsClient) -> None:
    """Test fetching a single Webset item."""
    now = datetime.now(UTC).isoformat()
    fixture_data = {
        "id": "item_123",
        "websetId": "webset_test123",
        "entityType": "company",
        "url": "https://example.com",
        "title": "Example",
        "createdAt": now,
        "updatedAt": now,
    }

    respx.get("https://api.exa.ai/v0/websets/webset_test123/items/item_123").mock(
        return_value=httpx.Response(200, json=fixture_data)
    )

    async with websets_client:
        item = await websets_client.get_webset_item("webset_test123", "item_123")

    assert item.id == "item_123"
    assert item.webset_id == "webset_test123"


@respx.mock
@pytest.mark.asyncio
async def test_webset_search_lifecycle(websets_client: ExaWebsetsClient) -> None:
    """Test create/get/cancel Webset search endpoints."""
    now = datetime.now(UTC).isoformat()
    search = {
        "id": "search_123",
        "status": "running",
        "query": "test query",
        "count": 10,
        "found": 5,
        "createdAt": now,
        "updatedAt": now,
    }

    respx.post("https://api.exa.ai/v0/websets/webset_test123/searches").mock(
        return_value=httpx.Response(200, json=search)
    )
    respx.get("https://api.exa.ai/v0/websets/webset_test123/searches/search_123").mock(
        return_value=httpx.Response(200, json=search)
    )
    canceled = {**search, "status": "canceled", "updatedAt": now}
    respx.post("https://api.exa.ai/v0/websets/webset_test123/searches/search_123/cancel").mock(
        return_value=httpx.Response(200, json=canceled)
    )

    async with websets_client:
        created = await websets_client.create_webset_search(
            "webset_test123",
            CreateWebsetSearchParameters(query="test query", count=10),
        )
        fetched = await websets_client.get_webset_search("webset_test123", "search_123")
        canceled_resp = await websets_client.cancel_webset_search("webset_test123", "search_123")

    assert created.id == "search_123"
    assert fetched.id == "search_123"
    assert canceled_resp.status.value == "canceled"


@pytest.mark.asyncio
async def test_client_property_requires_open(websets_client: ExaWebsetsClient) -> None:
    """Test `.client` property errors if open() has not been called."""
    with pytest.raises(RuntimeError):
        _ = websets_client.client


@pytest.mark.asyncio
async def test_open_close_idempotent(websets_client: ExaWebsetsClient) -> None:
    """Test open/close are idempotent."""
    await websets_client.open()
    client1 = websets_client.client
    await websets_client.open()
    assert websets_client.client is client1

    await websets_client.close()
    await websets_client.close()


@pytest.mark.asyncio
async def test_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test from_env uses ExaConfig.from_env()."""
    monkeypatch.setenv("EXA_API_KEY", "test_key")
    client = ExaWebsetsClient.from_env()
    assert isinstance(client, ExaWebsetsClient)


def test_parse_retry_after(websets_client: ExaWebsetsClient) -> None:
    """Test Retry-After parsing for numeric, missing, and HTTP-date values."""
    response = httpx.Response(429, headers={})
    assert websets_client._parse_retry_after(response) == 0

    response = httpx.Response(429, headers={"retry-after": "2"})
    assert websets_client._parse_retry_after(response) == 2

    # HTTP-date in the past yields a 0-second delay (exercises date parsing branch).
    response = httpx.Response(429, headers={"retry-after": "Wed, 21 Oct 2015 07:28:00 GMT"})
    assert websets_client._parse_retry_after(response) == 0


@respx.mock
@pytest.mark.asyncio
async def test_rate_limit_retry_and_exhaustion(websets_client: ExaWebsetsClient) -> None:
    """Test 429 retry path and ExaRateLimitError when retries exhausted."""
    # Exhausted: max_retries=1 means we raise immediately.
    config = ExaConfig(
        api_key="test_key",
        base_url="https://api.exa.ai",
        timeout_seconds=30.0,
        max_retries=1,
        retry_delay_seconds=0.0,
    )
    exhausted_client = ExaWebsetsClient(config)
    respx.get("https://api.exa.ai/v0/websets/nonexistent").mock(
        return_value=httpx.Response(429, headers={"retry-after": "0"})
    )
    async with exhausted_client:
        with pytest.raises(ExaRateLimitError):
            await exhausted_client.get_webset("nonexistent")

    # Retry then succeed.
    route = respx.get("https://api.exa.ai/v0/websets/webset_test123").mock(
        side_effect=[
            httpx.Response(429, headers={"retry-after": "0"}),
            httpx.Response(200, json=load_golden_fixture("get_webset")),
        ]
    )
    async with websets_client:
        _ = await websets_client.get_webset("webset_test123")
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_server_error_retry_then_succeeds(websets_client: ExaWebsetsClient) -> None:
    """Test 5xx retry path in _request()."""
    route = respx.get("https://api.exa.ai/v0/websets/webset_test123").mock(
        side_effect=[
            httpx.Response(500, text="server error"),
            httpx.Response(200, json=load_golden_fixture("get_webset")),
        ]
    )
    async with websets_client:
        _ = await websets_client.get_webset("webset_test123")
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_json_decode_error_raises_exa_api_error(websets_client: ExaWebsetsClient) -> None:
    """Test invalid JSON responses raise ExaAPIError."""
    respx.get("https://api.exa.ai/v0/websets/webset_test123").mock(
        return_value=httpx.Response(200, text="not json")
    )
    async with websets_client:
        with pytest.raises(ExaAPIError):
            await websets_client.get_webset("webset_test123")


@respx.mock
@pytest.mark.asyncio
async def test_network_error_retry_then_succeeds() -> None:
    """Test network/timeout retry path in _request()."""
    config = ExaConfig(
        api_key="test_key",
        base_url="https://api.exa.ai",
        timeout_seconds=30.0,
        max_retries=2,
        retry_delay_seconds=0.0,
    )
    client = ExaWebsetsClient(config)
    route = respx.get("https://api.exa.ai/v0/websets/webset_test123").mock(
        side_effect=[
            httpx.TimeoutException("timeout"),
            httpx.Response(200, json=load_golden_fixture("get_webset")),
        ]
    )
    async with client:
        _ = await client.get_webset("webset_test123")
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_client_error_handling(websets_client: ExaWebsetsClient):
    """Test client handles API errors appropriately."""
    respx.get("https://api.exa.ai/v0/websets/nonexistent").mock(
        return_value=httpx.Response(404, json={"error": "Webset not found"})
    )

    async with websets_client:
        with pytest.raises(ExaAPIError) as exc_info:
            await websets_client.get_webset("nonexistent")

    assert "404" in str(exc_info.value)


@respx.mock
@pytest.mark.asyncio
async def test_client_auth_error_handling(websets_client: ExaWebsetsClient):
    """Test client handles 401 auth errors."""
    respx.post("https://api.exa.ai/v0/websets").mock(
        return_value=httpx.Response(401, json={"error": "Invalid API key"})
    )

    async with websets_client:
        params = CreateWebsetParameters(
            search=CreateWebsetSearchParameters(
                query="test",
                count=5,
            )
        )
        with pytest.raises(ExaAuthError) as exc_info:
            await websets_client.create_webset(params)

    assert "401" in str(exc_info.value) or "Invalid API key" in str(exc_info.value)
