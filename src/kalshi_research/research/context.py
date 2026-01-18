"""Exa-powered market context research utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import structlog

from kalshi_research.exa.models.search import SearchResponse, SearchResult
from kalshi_research.exa.policy import ExaBudget, ExaPolicy, extract_exa_cost_total

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market
    from kalshi_research.exa.cache import ExaCache
    from kalshi_research.exa.client import ExaClient

logger = structlog.get_logger()


@dataclass(frozen=True)
class ResearchSource:
    """A single research source with relevance scoring."""

    url: str
    title: str
    source_domain: str
    published_date: datetime | None
    relevance_score: float
    highlight: str | None = None
    full_text: str | None = None
    category: str = "article"  # article, research_paper, news, social


@dataclass
class MarketResearch:
    """Research context for a market."""

    market_ticker: str
    market_title: str
    researched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    news: list[ResearchSource] = field(default_factory=list)
    research_papers: list[ResearchSource] = field(default_factory=list)
    related_coverage: list[ResearchSource] = field(default_factory=list)

    queries_used: list[str] = field(default_factory=list)
    total_sources_found: int = 0
    exa_cost_dollars: float = 0.0
    budget_usd: float = 0.0
    budget_spent_usd: float = 0.0
    budget_exhausted: bool = False

    def top_sources(self, n: int = 5) -> list[ResearchSource]:
        """Return top N sources by relevance across all categories."""
        all_sources = self.news + self.research_papers + self.related_coverage
        return sorted(all_sources, key=lambda s: s.relevance_score, reverse=True)[:n]


class MarketContextResearcher:
    """Research context for Kalshi markets using Exa."""

    def __init__(
        self,
        exa: ExaClient,
        *,
        cache: ExaCache | None = None,
        max_news_results: int = 10,
        max_paper_results: int = 5,
        news_recency_days: int = 30,
        policy: ExaPolicy | None = None,
    ) -> None:
        self._exa = exa
        self._cache = cache
        self._max_news_results = max_news_results
        self._max_paper_results = max_paper_results
        self._news_recency_days = news_recency_days
        self._policy = policy or ExaPolicy.from_mode()

    def _generate_search_queries(self, market: Market) -> list[str]:
        """Generate a small set of queries from market metadata."""
        title = market.title.strip()
        if title.lower().startswith("will "):
            title = title[5:]
        title = title.rstrip("?").strip()

        queries = [
            title,
            f"{title} prediction forecast",
            f"{title} analysis outlook",
        ]
        # Keep the output deterministic and cost-bounded.
        return list(dict.fromkeys(q for q in queries if q))[:3]

    def _extract_source_domain(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")

    def _result_to_source(
        self,
        result: SearchResult,
        category: str,
        *,
        relevance_boost: float = 0.0,
    ) -> ResearchSource:
        base_relevance = result.score if result.score is not None else 0.9

        highlight: str | None = None
        if result.highlights:
            highlight = result.highlights[0]
        elif result.text:
            highlight = f"{result.text[:300]}..."

        return ResearchSource(
            url=result.url,
            title=result.title,
            source_domain=self._extract_source_domain(result.url),
            published_date=result.published_date,
            relevance_score=min(base_relevance + relevance_boost, 1.0),
            highlight=highlight,
            full_text=result.text,
            category=category,
        )

    async def _search_with_cache(
        self,
        *,
        params: dict[str, object],
        query: str,
        num_results: int,
        category: str | None = None,
        start_published_date: datetime | None = None,
        exclude_domains: list[str] | None = None,
        budget: ExaBudget,
        include_text: bool,
        include_highlights: bool,
    ) -> tuple[SearchResponse | None, bool]:
        cache_params = self._policy.normalize_cache_params(params)
        cached = self._cache.get("search", cache_params) if self._cache else None
        if cached:
            return (SearchResponse.model_validate(cached), True)

        estimated_cost = self._policy.estimate_search_cost_usd(
            num_results=num_results,
            include_text=include_text,
            include_highlights=include_highlights,
            search_type=self._policy.exa_search_type,
        )
        if not budget.can_spend(estimated_cost):
            return (None, False)

        response = await self._exa.search(
            query,
            search_type=self._policy.exa_search_type,
            num_results=num_results,
            text=include_text,
            highlights=include_highlights,
            category=category,
            start_published_date=start_published_date,
            exclude_domains=exclude_domains,
        )

        if self._cache:
            self._cache.set(
                "search",
                cache_params,
                response.model_dump(mode="json", by_alias=True, exclude_none=True),
            )

        budget.record_spend(extract_exa_cost_total(response))
        return (response, False)

    async def _collect_sources(
        self,
        *,
        market_ticker: str,
        query: str,
        num_results: int,
        source_category: str,
        exa_category: str | None = None,
        start_published_date: datetime | None = None,
        exclude_domains: list[str] | None = None,
        budget: ExaBudget,
    ) -> tuple[list[ResearchSource], float, bool]:
        include_text = self._policy.include_full_text
        include_highlights = True
        params: dict[str, object] = {
            "query": query,
            "search_type": self._policy.exa_search_type,
            "num_results": num_results,
            "text": include_text,
            "highlights": include_highlights,
        }
        if exa_category:
            params["category"] = exa_category
        if start_published_date:
            params["start_published_date"] = start_published_date
        if exclude_domains:
            params["exclude_domains"] = exclude_domains

        try:
            response, cached = await self._search_with_cache(
                params=params,
                query=query,
                num_results=num_results,
                category=exa_category,
                start_published_date=start_published_date,
                exclude_domains=exclude_domains,
                budget=budget,
                include_text=include_text,
                include_highlights=include_highlights,
            )
        except Exception as e:
            logger.warning(
                "Exa search failed",
                market=market_ticker,
                category=source_category,
                error=str(e),
                exc_info=True,
            )
            return ([], 0.0, False)

        if response is None:
            logger.warning(
                "Exa budget exhausted; stopping market context research early",
                market=market_ticker,
                category=source_category,
                budget_limit=budget.limit_usd,
                budget_spent=budget.spent_usd,
            )
            return ([], 0.0, True)

        sources = [self._result_to_source(r, source_category) for r in response.results]
        cost = 0.0
        if not cached and response.cost_dollars:
            cost = response.cost_dollars.total
        return (sources, cost, False)

    async def research_market(self, market: Market) -> MarketResearch:
        """Research a market using Exa with separate news/paper/context searches."""
        research = MarketResearch(market_ticker=market.ticker, market_title=market.title)
        research.budget_usd = self._policy.budget_usd
        budget = ExaBudget(limit_usd=self._policy.budget_usd)

        queries = self._generate_search_queries(market)
        research.queries_used = queries

        total_cost = 0.0

        # Use day-level granularity so cache keys are stable within a day.
        today_utc = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        news_cutoff = today_utc - timedelta(days=self._news_recency_days)

        research.news, news_cost, budget_exhausted = await self._collect_sources(
            market_ticker=market.ticker,
            query=queries[0],
            num_results=self._max_news_results,
            source_category="news",
            exa_category="news",
            start_published_date=news_cutoff,
            budget=budget,
        )
        total_cost += news_cost

        if budget_exhausted:
            research.budget_exhausted = True
            research.budget_spent_usd = budget.spent_usd
            research.exa_cost_dollars = total_cost
            return research

        research.research_papers, paper_cost, budget_exhausted = await self._collect_sources(
            market_ticker=market.ticker,
            query=queries[0],
            num_results=self._max_paper_results,
            source_category="research_paper",
            exa_category="research paper",
            budget=budget,
        )
        total_cost += paper_cost

        if budget_exhausted:
            research.budget_exhausted = True
            research.budget_spent_usd = budget.spent_usd
            research.exa_cost_dollars = total_cost
            return research

        if len(queries) > 1:
            (
                research.related_coverage,
                related_cost,
                budget_exhausted,
            ) = await self._collect_sources(
                market_ticker=market.ticker,
                query=queries[1],
                num_results=5,
                source_category="article",
                exclude_domains=["kalshi.com"],
                budget=budget,
            )
            total_cost += related_cost
            if budget_exhausted:
                research.budget_exhausted = True

        research.total_sources_found = (
            len(research.news) + len(research.research_papers) + len(research.related_coverage)
        )
        research.exa_cost_dollars = total_cost
        research.budget_spent_usd = budget.spent_usd
        if budget.spent_usd > budget.limit_usd:
            research.budget_exhausted = True

        logger.info(
            "Market research complete",
            market=market.ticker,
            news=len(research.news),
            papers=len(research.research_papers),
            related=len(research.related_coverage),
            cost=total_cost,
            budget_limit=budget.limit_usd,
            budget_spent=budget.spent_usd,
            budget_exhausted=research.budget_exhausted,
        )

        return research
