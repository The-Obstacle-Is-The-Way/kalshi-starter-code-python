from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from kalshi_research.exa.cache import ExaCache
from kalshi_research.exa.models.answer import AnswerResponse
from kalshi_research.exa.models.search import SearchResponse
from kalshi_research.research.topic import TopicResearcher

if TYPE_CHECKING:
    from pathlib import Path


def _answer_response(*, answer: str, cost_total: float) -> AnswerResponse:
    return AnswerResponse.model_validate(
        {
            "answer": answer,
            "citations": [
                {
                    "id": "cite_1",
                    "url": "https://example.com/cite",
                    "title": "Citation",
                    "publishedDate": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
                    "text": "Citation text",
                }
            ],
            "costDollars": {"total": cost_total},
        }
    )


def _search_response(*, request_id: str, cost_total: float) -> SearchResponse:
    return SearchResponse.model_validate(
        {
            "requestId": request_id,
            "results": [
                {
                    "id": f"doc_{request_id}",
                    "url": "https://example.com/a",
                    "title": "Example",
                    "score": 0.9,
                    "publishedDate": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
                    "highlights": ["Example highlight"],
                    "text": "Full text",
                }
            ],
            "costDollars": {"total": cost_total},
        }
    )


class StubExa:
    def __init__(self, *, answer: AnswerResponse, search: SearchResponse) -> None:
        self._answer = answer
        self._search = search
        self.answer_calls = 0
        self.search_calls = 0

    async def answer(self, query: str, *, text: bool = False) -> AnswerResponse:
        self.answer_calls += 1
        return self._answer

    async def search_and_contents(
        self, query: str, *, num_results: int = 10, **kwargs
    ) -> SearchResponse:
        self.search_calls += 1
        return self._search


async def test_research_topic_aggregates_and_caches_results(tmp_path: Path) -> None:
    exa = StubExa(
        answer=_answer_response(answer="This is a comprehensive summary.", cost_total=0.01),
        search=_search_response(request_id="req_1", cost_total=0.02),
    )
    cache = ExaCache(tmp_path)
    researcher = TopicResearcher(exa, cache=cache, max_results=5)

    first = await researcher.research_topic("Test topic", include_answer=True)
    second = await researcher.research_topic("Test topic", include_answer=True)

    assert exa.answer_calls == 1
    assert exa.search_calls == 1
    assert first.summary is not None
    assert len(first.summary_citations) == 1
    assert len(first.articles) == 1
    assert first.exa_cost_dollars == 0.03
    assert second.exa_cost_dollars == 0.03
