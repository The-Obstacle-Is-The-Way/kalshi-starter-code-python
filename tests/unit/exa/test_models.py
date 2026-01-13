from __future__ import annotations

from kalshi_research.exa.models.answer import AnswerResponse
from kalshi_research.exa.models.search import SearchResponse


def test_search_response_accepts_resolved_search_type_alias() -> None:
    data = {
        "requestId": "req_123",
        "results": [],
        "resolvedSearchType": "auto",
    }
    parsed = SearchResponse.model_validate(data)
    assert parsed.search_type == "auto"


def test_search_response_coerces_empty_published_date_to_none() -> None:
    data = {
        "requestId": "req_123",
        "results": [
            {
                "id": "https://example.com/article",
                "url": "https://example.com/article",
                "title": "Example",
                "publishedDate": "",
            }
        ],
    }

    parsed = SearchResponse.model_validate(data)
    assert parsed.results[0].published_date is None


def test_answer_response_coerces_empty_published_date_to_none() -> None:
    data = {
        "answer": "Example answer",
        "citations": [
            {
                "id": "https://example.com/article",
                "url": "https://example.com/article",
                "title": "Example",
                "publishedDate": "",
            }
        ],
    }

    parsed = AnswerResponse.model_validate(data)
    assert parsed.citations[0].published_date is None
