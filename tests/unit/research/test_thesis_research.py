from __future__ import annotations

from datetime import UTC, datetime

from kalshi_research.api.models.market import Market
from kalshi_research.exa.models.answer import AnswerResponse
from kalshi_research.exa.models.search import SearchResponse
from kalshi_research.research.thesis_research import ThesisResearcher


def _search_response(*, cost_total: float) -> SearchResponse:
    return SearchResponse.model_validate(
        {
            "requestId": "req_1",
            "results": [
                {
                    "id": "doc_pos",
                    "url": "https://example.com/pos",
                    "title": "ETF approval surge",
                    "score": 0.9,
                    "publishedDate": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
                    "highlights": ["Institutional inflows surge as ETF approval nears"],
                    "text": "Markets rally as regulators approve key filings.",
                },
                {
                    "id": "doc_neg",
                    "url": "https://example.com/neg",
                    "title": "SEC delays decision concerns",
                    "score": 0.8,
                    "publishedDate": datetime(2026, 1, 2, tzinfo=UTC).isoformat(),
                    "highlights": ["SEC delays decision amid regulatory concerns"],
                    "text": "Delays and risks increase as agencies reject timelines.",
                },
            ],
            "costDollars": {"total": cost_total},
        }
    )


def _answer_response(*, cost_total: float) -> AnswerResponse:
    return AnswerResponse.model_validate(
        {
            "answer": "Outlook summary.",
            "citations": [],
            "costDollars": {"total": cost_total},
        }
    )


class StubExa:
    def __init__(self) -> None:
        self.search_calls = 0
        self.answer_calls = 0

    async def search(self, *args, **kwargs) -> SearchResponse:
        self.search_calls += 1
        return _search_response(cost_total=0.01)

    async def answer(self, *args, **kwargs) -> AnswerResponse:
        self.answer_calls += 1
        return _answer_response(cost_total=0.02)


async def test_thesis_researcher_classifies_evidence(make_market) -> None:
    market = Market.model_validate(make_market(ticker="TEST-MARKET", title="Will BTC exceed 100k?"))
    exa = StubExa()
    researcher = ThesisResearcher(exa, max_sources=4, recent_days=7)

    data = await researcher.research_for_thesis(market, thesis_direction="yes")

    assert exa.search_calls == 2
    assert exa.answer_calls == 1
    assert data.exa_cost_dollars == 0.04
    assert data.summary
    assert len(data.bull_evidence) >= 1
    assert len(data.bear_evidence) >= 1
    assert "•" in data.suggested_bull_case
    assert "•" in data.suggested_bear_case
