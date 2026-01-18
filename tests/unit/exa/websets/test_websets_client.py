"""Test Exa Websets client with respx mocking using golden fixtures."""

import json
from pathlib import Path

import httpx
import pytest
import respx

from kalshi_research.exa.config import ExaConfig
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
        retry_delay_seconds=1.0,
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

    respx.get("https://api.exa.ai/v0/websets/webset_test123/items").mock(
        return_value=httpx.Response(200, json=fixture_data)
    )

    async with websets_client:
        response = await websets_client.list_webset_items("webset_test123", limit=10)

    assert response.object == "list"
    assert len(response.data) == 1
    assert response.data[0].id == "item_test789"
    assert not response.has_more


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
async def test_client_error_handling(websets_client: ExaWebsetsClient):
    """Test client handles API errors appropriately."""
    respx.get("https://api.exa.ai/v0/websets/nonexistent").mock(
        return_value=httpx.Response(404, json={"error": "Webset not found"})
    )

    async with websets_client:
        with pytest.raises(Exception) as exc_info:
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
        with pytest.raises(Exception) as exc_info:
            await websets_client.create_webset(params)

    assert "401" in str(exc_info.value) or "Invalid API key" in str(exc_info.value)
