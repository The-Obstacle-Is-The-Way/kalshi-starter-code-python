from __future__ import annotations

from datetime import UTC, datetime

from kalshi_research.exa.models.search import SearchResponse
from kalshi_research.research.invalidation import InvalidationDetector, InvalidationSeverity
from kalshi_research.research.thesis import Thesis


def _search_response() -> SearchResponse:
    return SearchResponse.model_validate(
        {
            "requestId": "req_1",
            "results": [
                {
                    "id": "doc_1",
                    "url": "https://example.com/sec",
                    "title": "SEC delays ETF decision",
                    "score": 0.9,
                    "publishedDate": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
                    "highlights": ["SEC delays decision amid concerns"],
                    "text": "The SEC delays the ETF decision, raising concerns about timelines.",
                }
            ],
        }
    )


class StubExa:
    def __init__(self) -> None:
        self.calls = 0

    async def search(self, *args, **kwargs) -> SearchResponse:
        self.calls += 1
        return _search_response()


async def test_invalidation_detector_flags_high_severity() -> None:
    thesis = Thesis(
        id="t1",
        title="Will Bitcoin exceed 100k?",
        market_tickers=["TEST"],
        your_probability=0.65,
        market_probability=0.5,
        confidence=0.7,
        bull_case="Bull",
        bear_case="Bear",
        key_assumptions=["ETF approval"],
        invalidation_criteria=["SEC delays ETF decision"],
    )

    exa = StubExa()
    detector = InvalidationDetector(exa, lookback_hours=48)
    report = await detector.check_thesis(thesis)

    assert exa.calls >= 1
    assert report.has_high_severity
    assert report.signals
    assert report.signals[0].severity == InvalidationSeverity.HIGH
