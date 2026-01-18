"""Test that golden fixtures parse correctly with Websets models."""

import json
from pathlib import Path

from kalshi_research.exa.websets.models import (
    GetWebsetResponse,
    ListWebsetItemResponse,
    PreviewWebsetResponse,
    Webset,
)

GOLDEN_WEBSETS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / "fixtures" / "golden" / "exa_websets"
)


def load_golden_fixture(name: str) -> dict:
    """Load a golden fixture by name."""
    fixture_path = GOLDEN_WEBSETS_DIR / f"{name}_response.json"
    with fixture_path.open() as f:
        data = json.load(f)
    return data["response"]


def test_create_webset_fixture_parses():
    """Test that create_webset golden fixture parses as Webset model."""
    data = load_golden_fixture("create_webset")
    webset = Webset.model_validate(data)

    assert webset.id == "webset_test123"
    assert webset.object == "webset"
    assert webset.status.value == "pending"
    assert webset.title == "Test Webset"
    assert len(webset.searches) == 1
    assert webset.searches[0].id == "search_test456"
    assert webset.searches[0].query == "AI startups in Europe"


def test_get_webset_fixture_parses():
    """Test that get_webset golden fixture parses as GetWebsetResponse model."""
    data = load_golden_fixture("get_webset")
    response = GetWebsetResponse.model_validate(data)

    assert response.id == "webset_test123"
    assert response.object == "webset"
    assert response.status.value == "running"
    assert len(response.searches) == 1
    assert response.searches[0].status.value == "completed"
    assert response.searches[0].found == 8


def test_list_webset_items_fixture_parses():
    """Test that list_webset_items golden fixture parses as ListWebsetItemResponse model."""
    data = load_golden_fixture("list_webset_items")
    response = ListWebsetItemResponse.model_validate(data)

    assert response.object == "list"
    assert len(response.data) == 1
    assert response.data[0].id == "item_test789"
    assert response.data[0].webset_id == "webset_test123"
    assert response.data[0].entity_type.value == "company"
    assert response.data[0].url == "https://example.com/ai-startup-1"
    assert not response.has_more
    assert response.next_cursor is None


def test_preview_webset_fixture_parses():
    """Test that preview_webset golden fixture parses as PreviewWebsetResponse model."""
    data = load_golden_fixture("preview_webset")
    response = PreviewWebsetResponse.model_validate(data)

    assert response.object == "list"
    assert len(response.data) == 1
    assert response.data[0].url == "https://example.com/ai-startup-preview"
    assert response.data[0].title == "AI Startup Preview"
    assert response.data[0].entity_type.value == "company"


def test_all_golden_fixtures_exist():
    """Verify all expected golden fixtures exist."""
    summary_path = GOLDEN_WEBSETS_DIR / "_recording_summary.json"
    assert summary_path.exists(), "Recording summary not found"

    with summary_path.open() as f:
        summary = json.load(f)

    for fixture_name in summary["fixtures"]:
        fixture_path = GOLDEN_WEBSETS_DIR / fixture_name
        assert fixture_path.exists(), f"Missing fixture: {fixture_name}"
