from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from kalshi_research.api.models.market import Market
from kalshi_research.exa.cache import ExaCache
from kalshi_research.exa.models.search import SearchResponse
from kalshi_research.research.context import MarketContextResearcher

if TYPE_CHECKING:
    from pathlib import Path


def _search_response(*, request_id: str, title: str, cost_total: float) -> SearchResponse:
    return SearchResponse.model_validate(
        {
            "requestId": request_id,
            "results": [
                {
                    "id": f"doc_{request_id}",
                    "url": "https://example.com/a",
                    "title": title,
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
    def __init__(self, responses: list[SearchResponse]) -> None:
        self._responses = responses
        self.search_calls = 0

    async def search(self, *args, **kwargs) -> SearchResponse:
        response = self._responses[self.search_calls]
        self.search_calls += 1
        return response


def test_generate_search_queries_from_title(make_market) -> None:
    market = Market.model_validate(
        make_market(
            ticker="KXBTC-26JAN-T100000",
            title="Will Bitcoin exceed $100,000 by January 26?",
        )
    )

    researcher = MarketContextResearcher(object())
    queries = researcher._generate_search_queries(market)

    assert len(queries) >= 1
    assert not queries[0].lower().startswith("will ")
    assert not queries[0].endswith("?")
    assert "Bitcoin" in queries[0] or "bitcoin" in queries[0]


async def test_research_market_aggregates_and_caches_results(tmp_path: Path, make_market) -> None:
    responses = [
        _search_response(request_id="news", title="News", cost_total=0.01),
        _search_response(request_id="paper", title="Paper", cost_total=0.02),
        _search_response(request_id="related", title="Related", cost_total=0.03),
    ]
    exa = StubExa(responses)
    cache = ExaCache(tmp_path)

    market = Market.model_validate(
        make_market(
            ticker="TEST-MARKET",
            title="Will Something happen?",
        )
    )

    researcher = MarketContextResearcher(
        exa,
        cache=cache,
        max_news_results=1,
        max_paper_results=1,
        news_recency_days=30,
    )

    first = await researcher.research_market(market)
    second = await researcher.research_market(market)

    assert exa.search_calls == 3
    assert first.total_sources_found == 3
    assert second.total_sources_found == 3
    assert first.exa_cost_dollars == 0.06
    assert second.exa_cost_dollars == 0.0
