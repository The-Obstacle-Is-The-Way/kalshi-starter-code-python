# SPEC-021: Exa-Powered Market Research

**Status:** ✅ Implemented (2026-01-09)
**Priority:** P1 (Core research enhancement)
**Estimated Complexity:** Medium
**Dependencies:** SPEC-020

---

## 1. Overview

Integrate Exa search directly into market research workflows. When you're analyzing a Kalshi market, automatically find relevant news, research papers, and expert analysis to inform your thesis.

### 1.1 Goals

- Search for news and context related to specific markets or events
- Find similar markets/events from historical coverage
- Extract relevant quotes and highlights for thesis documentation
- CLI commands for interactive research
- Caching to avoid redundant API calls

### 1.2 Non-Goals

- Automated thesis generation (that's SPEC-023)
- Sentiment analysis pipeline (that's SPEC-022)
- Full research agent orchestration (that's SPEC-024)
- Database storage of all search results (only cache)

---

## 2. Use Cases

### 2.1 Market Context Research

```bash
# Research a specific market
uv run kalshi research context KXBTC-26JAN-T100000

# Output:
# Market: Will Bitcoin exceed $100,000 by January 26?
# Current: 45% YES | Volume: 125,000 | Spread: 2¢
#
# 📰 Recent News (5 articles)
# ────────────────────────────
# 1. "Bitcoin ETF Inflows Hit Record $1.2B" (Jan 15)
#    Source: CoinDesk | Relevance: 0.92
#    > "Institutional demand continues to surge..."
#
# 2. "Federal Reserve Signals Rate Stability" (Jan 14)
#    Source: Reuters | Relevance: 0.87
#    > "The Fed's dovish stance typically correlates..."
#
# 📄 Research Papers (2 papers)
# ────────────────────────────
# 1. "Prediction Market Accuracy in Crypto Events" (2024)
#    Source: arXiv | Relevance: 0.78
#
# 🔗 Related Coverage
# ────────────────────────────
# - Polymarket discussion on BTC prices
# - Historical Kalshi BTC market outcomes
```

### 2.2 Event Deep Dive

```bash
# Research an entire event (multiple markets)
uv run kalshi research event INXD-26JAN

# Aggregates research across all markets in the event
```

### 2.3 Topic Research

```bash
# Research a general topic for thesis ideation
uv run kalshi research topic "US inflation CPI January 2026"
```

---

## 3. Technical Specification

### 3.1 Module Structure

```
src/kalshi_research/
├── research/
│   ├── __init__.py
│   ├── thesis.py           # (existing)
│   ├── backtest.py         # (existing)
│   ├── context.py          # NEW: Market context research
│   └── topic.py            # NEW: Topic research utilities
├── exa/
│   ├── ...                 # (from SPEC-020)
│   └── cache.py            # NEW: Simple response caching
```

### 3.2 Market Context Researcher

```python
# src/kalshi_research/research/context.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market
    from kalshi_research.exa.client import ExaClient
    from kalshi_research.exa.models.search import SearchResult

logger = structlog.get_logger()


@dataclass
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

    # Categorized sources
    news: list[ResearchSource] = field(default_factory=list)
    research_papers: list[ResearchSource] = field(default_factory=list)
    related_coverage: list[ResearchSource] = field(default_factory=list)

    # Search metadata
    queries_used: list[str] = field(default_factory=list)
    total_sources_found: int = 0
    exa_cost_dollars: float = 0.0

    def top_sources(self, n: int = 5) -> list[ResearchSource]:
        """Get top N sources by relevance across all categories."""
        all_sources = self.news + self.research_papers + self.related_coverage
        return sorted(all_sources, key=lambda s: s.relevance_score, reverse=True)[:n]


class MarketContextResearcher:
    """
    Research context for Kalshi markets using Exa.

    Generates intelligent search queries based on market metadata,
    categorizes results, and extracts relevant highlights.
    """

    def __init__(
        self,
        exa: ExaClient,
        *,
        max_news_results: int = 10,
        max_paper_results: int = 5,
        news_recency_days: int = 30,
    ) -> None:
        """
        Initialize the researcher.

        Args:
            exa: Initialized ExaClient
            max_news_results: Maximum news articles to fetch
            max_paper_results: Maximum research papers to fetch
            news_recency_days: How far back to search for news
        """
        self.exa = exa
        self.max_news_results = max_news_results
        self.max_paper_results = max_paper_results
        self.news_recency_days = news_recency_days

    def _generate_search_queries(self, market: Market) -> list[str]:
        """
        Generate intelligent search queries from market metadata.

        Strategy:
        1. Use market title directly (cleaned)
        2. Extract key entities (e.g., "Bitcoin", "Trump", "CPI")
        3. Add context terms for prediction markets
        """
        queries = []

        # Clean title - remove Kalshi-specific formatting
        title = market.title
        title = title.replace("Will ", "").replace("?", "")

        # Primary query: the market question itself
        queries.append(title)

        # Secondary: add prediction context
        queries.append(f"{title} prediction forecast")

        # If it's a binary yes/no market, search for both outcomes
        if "exceed" in title.lower() or "above" in title.lower():
            queries.append(f"{title} analysis outlook")

        return queries[:3]  # Limit to 3 queries max

    def _extract_source_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain

    def _result_to_source(
        self,
        result: SearchResult,
        category: str,
        relevance_boost: float = 0.0,
    ) -> ResearchSource:
        """Convert Exa SearchResult to ResearchSource."""
        # Prefer Exa's explicit similarity score when present (0..1). Fall back to a conservative default.
        base_relevance = result.score if result.score is not None else 0.9

        # Extract first highlight or truncate text
        highlight = None
        if result.highlights:
            highlight = result.highlights[0]
        elif result.text:
            highlight = result.text[:300] + "..."

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

    async def research_market(self, market: Market) -> MarketResearch:
        """
        Research a single market comprehensively.

        Performs multiple Exa searches:
        1. Recent news (filtered by date)
        2. Research papers (academic sources)
        3. Related coverage (broader context)

        Args:
            market: Kalshi Market object

        Returns:
            MarketResearch with categorized sources
        """
        research = MarketResearch(
            market_ticker=market.ticker,
            market_title=market.title,
        )

        queries = self._generate_search_queries(market)
        research.queries_used = queries
        total_cost = 0.0

        # 1. Search for recent news
        news_cutoff = datetime.now(UTC) - timedelta(days=self.news_recency_days)

        try:
            news_response = await self.exa.search(
                queries[0],
                num_results=self.max_news_results,
                text=True,
                highlights=True,
                category="news",
                start_published_date=news_cutoff,
            )

            for result in news_response.results:
                source = self._result_to_source(result, "news")
                research.news.append(source)

            if news_response.cost_dollars:
                total_cost += news_response.cost_dollars.total

        except Exception as e:
            logger.warning("News search failed", error=str(e), market=market.ticker)

        # 2. Search for research papers
        try:
            paper_response = await self.exa.search(
                queries[0],
                num_results=self.max_paper_results,
                text=True,
                highlights=True,
                category="research paper",
            )

            for result in paper_response.results:
                source = self._result_to_source(result, "research_paper")
                research.research_papers.append(source)

            if paper_response.cost_dollars:
                total_cost += paper_response.cost_dollars.total

        except Exception as e:
            logger.warning("Paper search failed", error=str(e), market=market.ticker)

        # 3. Search for broader related coverage
        if len(queries) > 1:
            try:
                related_response = await self.exa.search(
                    queries[1],
                    num_results=5,
                    text=True,
                    highlights=True,
                    exclude_domains=["kalshi.com"],  # Avoid self-references
                )

                for result in related_response.results:
                    source = self._result_to_source(result, "article")
                    research.related_coverage.append(source)

                if related_response.cost_dollars:
                    total_cost += related_response.cost_dollars.total

            except Exception as e:
                logger.warning("Related search failed", error=str(e), market=market.ticker)

        research.total_sources_found = (
            len(research.news) + len(research.research_papers) + len(research.related_coverage)
        )
        research.exa_cost_dollars = total_cost

        logger.info(
            "Market research complete",
            market=market.ticker,
            news=len(research.news),
            papers=len(research.research_papers),
            related=len(research.related_coverage),
            cost=total_cost,
        )

        return research
```

### 3.3 Topic Researcher

```python
# src/kalshi_research/research/topic.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from kalshi_research.exa.client import ExaClient
    from kalshi_research.exa.models.answer import AnswerResponse

from kalshi_research.research.context import ResearchSource

logger = structlog.get_logger()


@dataclass
class TopicResearch:
    """Research results for a topic query."""

    topic: str
    researched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Exa Answer output
    summary: str | None = None
    summary_citations: list[ResearchSource] = field(default_factory=list)

    # Additional search results
    articles: list[ResearchSource] = field(default_factory=list)

    # Metadata
    exa_cost_dollars: float = 0.0


class TopicResearcher:
    """
    Research a topic using Exa for thesis ideation.

    Unlike MarketContextResearcher which starts with a market,
    this starts with a topic/question and helps identify relevant markets.
    """

    def __init__(
        self,
        exa: ExaClient,
        *,
        max_results: int = 15,
    ) -> None:
        self.exa = exa
        self.max_results = max_results

    async def research_topic(
        self,
        topic: str,
        *,
        include_answer: bool = True,
    ) -> TopicResearch:
        """
        Research a topic comprehensively.

        Args:
            topic: The topic or question to research
            include_answer: Whether to use Exa Answer for a summary

        Returns:
            TopicResearch with summary and sources
        """
        research = TopicResearch(topic=topic)
        total_cost = 0.0

        # 1. Get an LLM-generated answer with citations
        if include_answer:
            try:
                answer_response = await self.exa.answer(topic, text=True)
                research.summary = answer_response.answer

                for cite in answer_response.citations:
                    source = ResearchSource(
                        url=cite.url,
                        title=cite.title,
                        source_domain=self._extract_domain(cite.url),
                        published_date=None,  # Answer endpoint doesn't always include
                        relevance_score=0.95,  # Citations are highly relevant
                        highlight=cite.text[:300] if cite.text else None,
                        full_text=cite.text,
                        category="citation",
                    )
                    research.summary_citations.append(source)

                if answer_response.cost_dollars:
                    total_cost += answer_response.cost_dollars.total

            except Exception as e:
                logger.warning("Answer generation failed", error=str(e), topic=topic)

        # 2. Broader search for articles
        try:
            search_response = await self.exa.search_and_contents(
                topic,
                num_results=self.max_results,
            )

            for result in search_response.results:
                source = ResearchSource(
                    url=result.url,
                    title=result.title,
                    source_domain=self._extract_domain(result.url),
                    published_date=result.published_date,
                    relevance_score=0.85,
                    highlight=result.highlights[0] if result.highlights else None,
                    full_text=result.text,
                    category="article",
                )
                research.articles.append(source)

            if search_response.cost_dollars:
                total_cost += search_response.cost_dollars.total

        except Exception as e:
            logger.warning("Topic search failed", error=str(e), topic=topic)

        research.exa_cost_dollars = total_cost
        return research

    def _extract_domain(self, url: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
```

### 3.4 Simple Cache

```python
# src/kalshi_research/exa/cache.py
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class CacheEntry:
    """A cached response with metadata."""

    key: str
    data: dict[str, Any]
    created_at: datetime
    expires_at: datetime


class ExaCache:
    """
    Simple file-based cache for Exa responses.

    Caches expensive operations (search, contents) to avoid
    redundant API calls during iterative research.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        default_ttl_hours: int = 24,
    ) -> None:
        """
        Initialize the cache.

        Args:
            cache_dir: Directory for cache files (default: data/exa_cache)
            default_ttl_hours: Default time-to-live for entries
        """
        self.cache_dir = cache_dir or Path("data/exa_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = timedelta(hours=default_ttl_hours)

    def _make_key(self, operation: str, params: dict[str, Any]) -> str:
        """Generate a cache key from operation and params."""
        # Sort params for consistent hashing
        param_str = json.dumps(params, sort_keys=True, default=str)
        content = f"{operation}:{param_str}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_path(self, key: str) -> Path:
        """Get file path for a cache key."""
        return self.cache_dir / f"{key}.json"

    def get(self, operation: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """
        Retrieve a cached response.

        Args:
            operation: The API operation (e.g., "search", "contents")
            params: The request parameters

        Returns:
            Cached response data, or None if not found/expired
        """
        key = self._make_key(operation, params)
        path = self._get_path(key)

        if not path.exists():
            return None

        try:
            with path.open() as f:
                entry = json.load(f)

            expires_at = datetime.fromisoformat(entry["expires_at"])
            if datetime.now(UTC) > expires_at:
                # Expired - remove and return None
                path.unlink(missing_ok=True)
                return None

            logger.debug("Cache hit", operation=operation, key=key)
            return entry["data"]

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Cache read failed", key=key, error=str(e))
            path.unlink(missing_ok=True)
            return None

    def set(
        self,
        operation: str,
        params: dict[str, Any],
        data: dict[str, Any],
        ttl: timedelta | None = None,
    ) -> None:
        """
        Store a response in the cache.

        Args:
            operation: The API operation
            params: The request parameters
            data: The response data to cache
            ttl: Optional custom TTL (defaults to default_ttl_hours)
        """
        key = self._make_key(operation, params)
        path = self._get_path(key)

        ttl = ttl or self.default_ttl
        now = datetime.now(UTC)

        entry = {
            "key": key,
            "operation": operation,
            "params": params,
            "data": data,
            "created_at": now.isoformat(),
            "expires_at": (now + ttl).isoformat(),
        }

        with path.open("w") as f:
            json.dump(entry, f, indent=2, default=str)

        logger.debug("Cache set", operation=operation, key=key, ttl_hours=ttl.total_seconds() / 3600)

    def clear(self) -> int:
        """Clear all cache entries. Returns number of entries cleared."""
        count = 0
        for path in self.cache_dir.glob("*.json"):
            path.unlink()
            count += 1
        return count

    def clear_expired(self) -> int:
        """Clear only expired entries. Returns number of entries cleared."""
        count = 0
        now = datetime.now(UTC)

        for path in self.cache_dir.glob("*.json"):
            try:
                with path.open() as f:
                    entry = json.load(f)
                expires_at = datetime.fromisoformat(entry["expires_at"])
                if now > expires_at:
                    path.unlink()
                    count += 1
            except (json.JSONDecodeError, KeyError):
                path.unlink()
                count += 1

        return count
```

### 3.5 CLI Commands

```python
# src/kalshi_research/cli/research.py (additions)

@app.command("context")
def research_context(
    ticker: Annotated[str, typer.Argument(help="Market ticker to research")],
    max_news: Annotated[int, typer.Option("--max-news", help="Max news articles")] = 10,
    max_papers: Annotated[int, typer.Option("--max-papers", help="Max research papers")] = 5,
    days: Annotated[int, typer.Option("--days", help="News recency in days")] = 30,
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """
    Research context for a specific market using Exa.

    Fetches recent news, research papers, and related coverage
    to help inform your thesis.

    Examples:
        kalshi research context KXBTC-26JAN-T100000
        kalshi research context TRUMP-WIN-2024 --max-news 20
    """
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.exa.client import ExaClient
    from kalshi_research.research.context import MarketContextResearcher

    async def _research() -> None:
        from kalshi_research.api.exceptions import KalshiAPIError

        # Get market details
        try:
            async with KalshiPublicClient() as kalshi:
                market = await kalshi.get_market(ticker)
        except KalshiAPIError:
            console.print(f"[red]Error:[/red] Market not found: {ticker}")
            raise typer.Exit(1) from None

        # Research with Exa
        try:
            async with ExaClient.from_env() as exa:
                researcher = MarketContextResearcher(
                    exa,
                    max_news_results=max_news,
                    max_paper_results=max_papers,
                    news_recency_days=days,
                )
                research = await researcher.research_market(market)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print("[dim]Set EXA_API_KEY in your .env file.[/dim]")
            raise typer.Exit(1)

        if output_json:
            import json
            from dataclasses import asdict
            console.print(json.dumps(asdict(research), indent=2, default=str))
            return

        # Display results
        console.print(f"\n[bold]Market:[/bold] {market.title}")
        yes_prob = (market.yes_bid + market.yes_ask) / 200
        console.print(
            f"[dim]Current: {yes_prob:.0%} YES | "
            f"Volume: {market.volume_24h:,} | "
            f"Spread: {market.yes_ask - market.yes_bid}¢[/dim]\n"
        )

        if research.news:
            console.print("[bold cyan]📰 Recent News[/bold cyan]")
            console.print("─" * 40)
            for i, source in enumerate(research.news[:5], 1):
                date_str = source.published_date.strftime("%b %d") if source.published_date else "N/A"
                console.print(f"{i}. [bold]{source.title}[/bold] ({date_str})")
                console.print(f"   [dim]Source: {source.source_domain}[/dim]")
                if source.highlight:
                    console.print(f"   [italic]> {source.highlight[:150]}...[/italic]")
                console.print()

        if research.research_papers:
            console.print("[bold cyan]📄 Research Papers[/bold cyan]")
            console.print("─" * 40)
            for i, source in enumerate(research.research_papers[:3], 1):
                console.print(f"{i}. [bold]{source.title}[/bold]")
                console.print(f"   [dim]Source: {source.source_domain}[/dim]")
                console.print()

        if research.related_coverage:
            console.print("[bold cyan]🔗 Related Coverage[/bold cyan]")
            console.print("─" * 40)
            for source in research.related_coverage[:3]:
                console.print(f"  • {source.title}")
                console.print(f"    [dim]{source.url}[/dim]")

        console.print(f"\n[dim]Cost: ${research.exa_cost_dollars:.4f}[/dim]")

    asyncio.run(_research())


@app.command("topic")
def research_topic(
    topic: Annotated[str, typer.Argument(help="Topic or question to research")],
    no_summary: Annotated[bool, typer.Option("--no-summary", help="Skip LLM summary")] = False,
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """
    Research a topic for thesis ideation.

    Uses Exa's Answer endpoint for an LLM-generated summary with citations,
    plus additional search results.

    Examples:
        kalshi research topic "US inflation outlook January 2026"
        kalshi research topic "Will SpaceX launch Starship successfully?"
    """
    from kalshi_research.exa.client import ExaClient
    from kalshi_research.research.topic import TopicResearcher

    async def _research() -> None:
        try:
            async with ExaClient.from_env() as exa:
                researcher = TopicResearcher(exa)
                research = await researcher.research_topic(
                    topic,
                    include_answer=not no_summary,
                )
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print("[dim]Set EXA_API_KEY in your .env file.[/dim]")
            raise typer.Exit(1)

        if output_json:
            import json
            from dataclasses import asdict
            console.print(json.dumps(asdict(research), indent=2, default=str))
            return

        console.print(f"\n[bold]Topic:[/bold] {topic}\n")

        if research.summary:
            console.print("[bold cyan]📝 Summary[/bold cyan]")
            console.print("─" * 50)
            console.print(research.summary)
            console.print()

            if research.summary_citations:
                console.print("[bold cyan]📚 Citations[/bold cyan]")
                for cite in research.summary_citations:
                    console.print(f"  • [link={cite.url}]{cite.title}[/link]")
                console.print()

        if research.articles:
            console.print("[bold cyan]📰 Articles[/bold cyan]")
            console.print("─" * 50)
            for i, source in enumerate(research.articles[:10], 1):
                console.print(f"{i}. [bold]{source.title}[/bold]")
                console.print(f"   [dim]{source.source_domain}[/dim]")
                if source.highlight:
                    console.print(f"   [italic]> {source.highlight[:120]}...[/italic]")
                console.print()

        console.print(f"\n[dim]Cost: ${research.exa_cost_dollars:.4f}[/dim]")

    asyncio.run(_research())
```

---

## 4. Testing Strategy

### 4.1 Unit Tests

```python
# tests/unit/research/test_context.py
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from kalshi_research.research.context import MarketContextResearcher, MarketResearch


class TestMarketContextResearcher:
    """Test market context research."""

    def test_generate_search_queries_from_title(self) -> None:
        """Queries are generated from market title."""
        market = MagicMock()
        market.ticker = "KXBTC-26JAN-T100000"
        market.title = "Will Bitcoin exceed $100,000 by January 26?"

        researcher = MarketContextResearcher(MagicMock())
        queries = researcher._generate_search_queries(market)

        assert len(queries) >= 1
        assert "Bitcoin" in queries[0] or "100,000" in queries[0]

    @pytest.mark.asyncio
    async def test_research_market_aggregates_results(self) -> None:
        """Research aggregates news, papers, and related coverage."""
        mock_exa = AsyncMock()
        mock_exa.search = AsyncMock(return_value=MagicMock(
            results=[
                MagicMock(
                    url="https://example.com",
                    title="Test Article",
                    published_date=datetime.now(UTC),
                    highlights=["Test highlight"],
                    text="Full text",
                ),
            ],
            cost_dollars=MagicMock(total=0.005),
        ))

        market = MagicMock()
        market.ticker = "TEST-MARKET"
        market.title = "Test market title?"

        researcher = MarketContextResearcher(mock_exa)
        research = await researcher.research_market(market)

        assert research.market_ticker == "TEST-MARKET"
        assert research.total_sources_found > 0
        assert research.exa_cost_dollars > 0


# tests/unit/research/test_topic.py
class TestTopicResearcher:
    """Test topic research."""

    @pytest.mark.asyncio
    async def test_research_topic_with_summary(self) -> None:
        """Topic research includes summary from Exa Answer."""
        mock_exa = AsyncMock()
        mock_exa.answer = AsyncMock(return_value=MagicMock(
            answer="This is a comprehensive summary...",
            citations=[
                MagicMock(url="https://cite.com", title="Citation", text="Text"),
            ],
            cost_dollars=MagicMock(total=0.01),
        ))
        mock_exa.search_and_contents = AsyncMock(return_value=MagicMock(
            results=[],
            cost_dollars=MagicMock(total=0.005),
        ))

        from kalshi_research.research.topic import TopicResearcher
        researcher = TopicResearcher(mock_exa)
        research = await researcher.research_topic("Test topic")

        assert research.summary is not None
        assert "comprehensive" in research.summary
        assert len(research.summary_citations) == 1
```

### 4.2 Integration Tests (Optional)

```python
# tests/integration/test_exa_research.py
"""
Integration tests that hit real Exa API.

Requires EXA_API_KEY environment variable.
Run with: pytest tests/integration/test_exa_research.py -v
"""
import os

import pytest

from kalshi_research.exa.client import ExaClient
from kalshi_research.research.topic import TopicResearcher


@pytest.mark.skipif(
    not os.environ.get("EXA_API_KEY"),
    reason="EXA_API_KEY not set",
)
class TestExaResearchIntegration:
    """Integration tests with real Exa API."""

    @pytest.mark.asyncio
    async def test_topic_research_real(self) -> None:
        """Test topic research with real API."""
        async with ExaClient.from_env() as exa:
            researcher = TopicResearcher(exa, max_results=5)
            research = await researcher.research_topic(
                "Bitcoin price prediction 2026",
                include_answer=True,
            )

        assert research.summary is not None
        assert len(research.summary) > 100
        assert research.exa_cost_dollars > 0
```

---

## 5. Implementation Tasks

### Phase 1: Core Research Classes

- [x] Create `src/kalshi_research/research/context.py`
- [x] Implement `ResearchSource` and `MarketResearch` dataclasses
- [x] Implement `MarketContextResearcher` with query generation
- [x] Write unit tests for query generation

### Phase 2: Topic Research

- [x] Create `src/kalshi_research/research/topic.py`
- [x] Implement `TopicResearch` dataclass
- [x] Implement `TopicResearcher` with answer integration
- [x] Write unit tests

### Phase 3: Caching

- [x] Create `src/kalshi_research/exa/cache.py`
- [x] Implement file-based cache with TTL
- [x] Integrate cache into researchers (optional layer)
- [x] Write cache tests

### Phase 4: CLI Commands

- [x] Add `research context` command
- [x] Add `research topic` command
- [x] Add JSON output option
- [x] Manual CLI testing

---

## 6. Acceptance Criteria

1. **Context Research**: Can research any Kalshi market and get relevant news/papers
2. **Topic Research**: Can research a topic and get LLM summary with citations
3. **Performance**: Market research completes in <10s
4. **Cost Visibility**: All commands show Exa API cost
5. **Graceful Degradation**: Handles missing API key, network errors gracefully
6. **Test Coverage**: >85% coverage on new modules

---

## 7. CLI Summary

```
kalshi research
├── thesis        # (existing) Thesis management
│   ├── create
│   ├── list
│   ├── show
│   └── resolve
├── backtest      # (existing) Run backtests
├── context       # NEW: Research a specific market
└── topic         # NEW: Research a topic/question
```

---

## 8. See Also

- [SPEC-020: Exa API Client](SPEC-020-exa-api-client.md)
- [SPEC-022: Exa News & Sentiment Pipeline](SPEC-022-exa-news-sentiment.md)
- [SPEC-023: Exa-Thesis Integration](SPEC-023-exa-thesis-integration.md)
