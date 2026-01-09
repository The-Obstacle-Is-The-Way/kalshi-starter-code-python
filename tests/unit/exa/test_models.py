from __future__ import annotations

from kalshi_research.exa.models.search import SearchResponse


def test_search_response_accepts_resolved_search_type_alias() -> None:
    data = {
        "requestId": "req_123",
        "results": [],
        "resolvedSearchType": "auto",
    }
    parsed = SearchResponse.model_validate(data)
    assert parsed.search_type == "auto"
