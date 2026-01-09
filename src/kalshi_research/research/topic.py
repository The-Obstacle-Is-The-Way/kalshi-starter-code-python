"""Exa-powered topic research for thesis ideation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import structlog

from kalshi_research.exa.models.answer import AnswerResponse
from kalshi_research.exa.models.search import SearchResponse
from kalshi_research.research.context import ResearchSource

if TYPE_CHECKING:
    from kalshi_research.exa.cache import ExaCache
    from kalshi_research.exa.client import ExaClient

logger = structlog.get_logger()


@dataclass
class TopicResearch:
    """Research results for a topic query."""

    topic: str
    researched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    summary: str | None = None
    summary_citations: list[ResearchSource] = field(default_factory=list)
    articles: list[ResearchSource] = field(default_factory=list)

    exa_cost_dollars: float = 0.0


class TopicResearcher:
    """Research a topic using Exa Answer + Search."""

    def __init__(
        self,
        exa: ExaClient,
        *,
        cache: ExaCache | None = None,
        max_results: int = 15,
    ) -> None:
        self._exa = exa
        self._cache = cache
        self._max_results = max_results

    async def _get_answer(self, topic: str) -> AnswerResponse | None:
        params: dict[str, object] = {"query": topic, "text": True}
        cached = self._cache.get("answer", params) if self._cache else None
        if cached:
            return AnswerResponse.model_validate(cached)

        try:
            response = await self._exa.answer(topic, text=True)
        except Exception as e:
            logger.warning("Answer generation failed", topic=topic, error=str(e))
            return None

        if self._cache:
            self._cache.set(
                "answer",
                params,
                response.model_dump(mode="json", by_alias=True, exclude_none=True),
            )
        return response

    async def _get_search(self, topic: str) -> SearchResponse | None:
        params: dict[str, object] = {
            "query": topic,
            "num_results": self._max_results,
            "text": True,
            "highlights": True,
        }
        cached = self._cache.get("search", params) if self._cache else None
        if cached:
            return SearchResponse.model_validate(cached)

        try:
            response = await self._exa.search_and_contents(topic, num_results=self._max_results)
        except Exception as e:
            logger.warning("Topic search failed", topic=topic, error=str(e))
            return None

        if self._cache:
            self._cache.set(
                "search",
                params,
                response.model_dump(mode="json", by_alias=True, exclude_none=True),
            )
        return response

    async def research_topic(self, topic: str, *, include_answer: bool = True) -> TopicResearch:
        research = TopicResearch(topic=topic)
        total_cost = 0.0

        if include_answer:
            answer = await self._get_answer(topic)
            if answer:
                research.summary = answer.answer
                for cite in answer.citations:
                    research.summary_citations.append(
                        ResearchSource(
                            url=cite.url,
                            title=cite.title,
                            source_domain=self._extract_domain(cite.url),
                            published_date=cite.published_date,
                            relevance_score=0.95,
                            highlight=(f"{cite.text[:300]}..." if cite.text else None),
                            full_text=cite.text,
                            category="citation",
                        )
                    )
                if answer.cost_dollars:
                    total_cost += answer.cost_dollars.total

        search = await self._get_search(topic)
        if search:
            for result in search.results:
                research.articles.append(
                    ResearchSource(
                        url=result.url,
                        title=result.title,
                        source_domain=self._extract_domain(result.url),
                        published_date=result.published_date,
                        relevance_score=(result.score if result.score is not None else 0.85),
                        highlight=(result.highlights[0] if result.highlights else None),
                        full_text=result.text,
                        category="article",
                    )
                )
            if search.cost_dollars:
                total_cost += search.cost_dollars.total

        research.exa_cost_dollars = total_cost
        return research

    def _extract_domain(self, url: str) -> str:
        return urlparse(url).netloc.replace("www.", "")
