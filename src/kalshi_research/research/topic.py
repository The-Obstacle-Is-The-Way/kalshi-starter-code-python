"""Exa-powered topic research for thesis ideation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import structlog

from kalshi_research.exa.models.answer import AnswerResponse
from kalshi_research.exa.models.search import SearchResponse
from kalshi_research.exa.policy import ExaBudget, ExaPolicy, extract_exa_cost_total
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
    budget_usd: float = 0.0
    budget_spent_usd: float = 0.0
    budget_exhausted: bool = False


class TopicResearcher:
    """Research a topic using Exa Answer + Search."""

    def __init__(
        self,
        exa: ExaClient,
        *,
        cache: ExaCache | None = None,
        max_results: int = 15,
        policy: ExaPolicy | None = None,
    ) -> None:
        self._exa = exa
        self._cache = cache
        self._max_results = max_results
        self._policy = policy or ExaPolicy.from_mode()

    async def _get_answer(
        self, topic: str, *, budget: ExaBudget
    ) -> tuple[AnswerResponse | None, bool]:
        params: dict[str, object] = {"query": topic, "text": True}
        cache_params = self._policy.normalize_cache_params(params)
        cached = self._cache.get("answer", cache_params) if self._cache else None
        if cached:
            return (AnswerResponse.model_validate(cached), False)

        estimated_cost = self._policy.estimate_answer_cost_usd(include_text=True)
        if not budget.can_spend(estimated_cost):
            return (None, True)

        try:
            response = await self._exa.answer(topic, text=True)
        except Exception as e:
            logger.warning("Answer generation failed", topic=topic, error=str(e), exc_info=True)
            return (None, False)

        if self._cache:
            self._cache.set(
                "answer",
                cache_params,
                response.model_dump(mode="json", by_alias=True, exclude_none=True),
            )
        budget.record_spend(extract_exa_cost_total(response))
        return (response, False)

    async def _get_search(
        self, topic: str, *, budget: ExaBudget
    ) -> tuple[SearchResponse | None, bool]:
        include_text = self._policy.include_full_text
        include_highlights = True
        params: dict[str, object] = {
            "query": topic,
            "search_type": self._policy.exa_search_type,
            "num_results": self._max_results,
            "text": include_text,
            "highlights": include_highlights,
        }
        cache_params = self._policy.normalize_cache_params(params)
        cached = self._cache.get("search", cache_params) if self._cache else None
        if cached:
            return (SearchResponse.model_validate(cached), False)

        estimated_cost = self._policy.estimate_search_cost_usd(
            num_results=self._max_results,
            include_text=include_text,
            include_highlights=include_highlights,
            search_type=self._policy.exa_search_type,
        )
        if not budget.can_spend(estimated_cost):
            return (None, True)

        try:
            response = await self._exa.search_and_contents(
                topic,
                num_results=self._max_results,
                search_type=self._policy.exa_search_type,
                text=include_text,
                highlights=include_highlights,
            )
        except Exception as e:
            logger.warning("Topic search failed", topic=topic, error=str(e), exc_info=True)
            return (None, False)

        if self._cache:
            self._cache.set(
                "search",
                cache_params,
                response.model_dump(mode="json", by_alias=True, exclude_none=True),
            )
        budget.record_spend(extract_exa_cost_total(response))
        return (response, False)

    async def research_topic(self, topic: str, *, include_answer: bool = True) -> TopicResearch:
        """Research a topic using Exa Answer + Search (optionally cached)."""
        research = TopicResearch(topic=topic)
        research.budget_usd = self._policy.budget_usd
        budget = ExaBudget(limit_usd=self._policy.budget_usd)
        total_cost = 0.0

        if include_answer and self._policy.include_answer:
            answer, budget_exhausted = await self._get_answer(topic, budget=budget)
            if budget_exhausted:
                research.budget_exhausted = True
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

        search, budget_exhausted = await self._get_search(topic, budget=budget)
        if budget_exhausted:
            research.budget_exhausted = True
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
        research.budget_spent_usd = budget.spent_usd
        return research

    def _extract_domain(self, url: str) -> str:
        return urlparse(url).netloc.replace("www.", "")
