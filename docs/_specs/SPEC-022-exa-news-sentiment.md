# SPEC-022: Exa News & Sentiment Pipeline

**Status:** 📋 Planned
**Priority:** P2 (Enhanced analysis)
**Estimated Complexity:** High
**Dependencies:** SPEC-020, SPEC-003

---

## 1. Overview

Build a continuous news monitoring and sentiment analysis pipeline. Automatically track news coverage for markets you care about, store historical news data in the database, and compute sentiment trends over time.

### 1.1 Goals

- Scheduled news collection for tracked markets/events
- Persistent storage of news articles in SQLite
- Simple sentiment scoring (no heavy ML - use keyword/rule-based initially)
- Sentiment trend visualization over time
- Alerts when sentiment shifts significantly
- CLI commands for monitoring setup and reporting

### 1.2 Non-Goals

- Real-time streaming (we use polling intervals)
- Advanced NLP/transformer-based sentiment (too heavy, use Exa's summaries instead)
- Social media monitoring (focus on news sources)
- Automated trading signals based on sentiment

---

## 2. Use Cases

### 2.1 Track Market News

```bash
# Start tracking news for a market
uv run kalshi news track KXBTC-26JAN-T100000

# Track an entire event
uv run kalshi news track --event INXD-26JAN

# List tracked items
uv run kalshi news list-tracked
```

### 2.2 Run News Collection

```bash
# Collect news for all tracked items (run periodically via cron)
uv run kalshi news collect

# Collect for a specific market
uv run kalshi news collect --ticker KXBTC-26JAN-T100000
```

### 2.3 View Sentiment Report

```bash
# Sentiment summary for a market
uv run kalshi news sentiment KXBTC-26JAN-T100000

# Output:
# Market: KXBTC-26JAN-T100000
# Period: Last 7 days
#
# Sentiment Score: +0.35 (Bullish)
# ─────────────────────────────────
# Articles Analyzed: 23
# Positive: 14 (61%)
# Neutral: 6 (26%)
# Negative: 3 (13%)
#
# Trend: ↑ +0.12 from last week
#
# Key Topics:
# • ETF inflows (+)
# • Fed rate decision (+)
# • Regulatory concerns (-)
#
# Recent Headlines:
# [+] "Bitcoin ETF Sees Record Inflows" - CoinDesk
# [+] "Institutional Adoption Accelerates" - Reuters
# [-] "SEC Delays Crypto Regulation" - Bloomberg
```

### 2.4 Sentiment Alerts

```bash
# Alert when sentiment shifts
uv run kalshi alerts add sentiment KXBTC-26JAN-T100000 --shift 0.20

# This triggers when 7-day rolling sentiment changes by ±0.20
```

---

## 3. Technical Specification

### 3.1 Module Structure

```
src/kalshi_research/
├── news/
│   ├── __init__.py
│   ├── collector.py        # NewsCollector - fetches and stores news
│   ├── sentiment.py        # SentimentAnalyzer - scores articles
│   ├── models.py           # Pydantic models for news data
│   └── tracker.py          # Manages tracked markets/events
├── data/
│   ├── models.py           # Add: NewsArticle, NewsSentiment, TrackedItem
│   └── repositories/
│       └── news.py         # NewsRepository
├── alerts/
│   └── conditions.py       # Add: SentimentShiftCondition
└── cli/
    └── news.py             # CLI commands
```

### 3.2 Database Models

```python
# src/kalshi_research/data/models.py (additions)

class TrackedItem(Base):
    """A market or event being tracked for news collection."""

    __tablename__ = "tracked_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    item_type: Mapped[str] = mapped_column(String(20))  # "market" or "event"
    search_queries: Mapped[str] = mapped_column(Text)  # JSON array of queries
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    last_collected_at: Mapped[datetime | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class NewsArticle(Base):
    """A news article related to a tracked item."""

    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(2000), unique=True, index=True)
    url_hash: Mapped[str] = mapped_column(String(64), index=True)  # For dedup
    title: Mapped[str] = mapped_column(String(500))
    source_domain: Mapped[str] = mapped_column(String(200))
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)
    collected_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    # Content
    text_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Exa metadata
    exa_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    sentiments: Mapped[list["NewsSentiment"]] = relationship(back_populates="article")


class NewsArticleMarket(Base):
    """Many-to-many: articles can relate to multiple markets."""

    __tablename__ = "news_article_markets"

    article_id: Mapped[int] = mapped_column(ForeignKey("news_articles.id"), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)


class NewsSentiment(Base):
    """Sentiment analysis result for an article."""

    __tablename__ = "news_sentiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("news_articles.id"), index=True)
    analyzed_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    # Sentiment scores
    score: Mapped[float] = mapped_column()  # -1.0 to +1.0
    label: Mapped[str] = mapped_column(String(20))  # positive, negative, neutral
    confidence: Mapped[float] = mapped_column()  # 0.0 to 1.0

    # Analysis metadata
    method: Mapped[str] = mapped_column(String(50))  # "keyword", "summary", "llm"
    keywords_matched: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    # Relationship
    article: Mapped["NewsArticle"] = relationship(back_populates="sentiments")
```

### 3.3 News Collector

```python
# src/kalshi_research/news/collector.py
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from kalshi_research.data.database import DatabaseManager
    from kalshi_research.exa.client import ExaClient

from kalshi_research.data.models import NewsArticle, NewsArticleMarket, TrackedItem
from kalshi_research.news.sentiment import SentimentAnalyzer

logger = structlog.get_logger()


class NewsCollector:
    """
    Collect news articles for tracked markets using Exa.

    Handles:
    - Fetching news for all tracked items
    - Deduplication by URL
    - Storing in database
    - Triggering sentiment analysis
    """

    def __init__(
        self,
        db: DatabaseManager,
        exa: ExaClient,
        *,
        max_articles_per_query: int = 20,
        lookback_days: int = 7,
        analyze_sentiment: bool = True,
    ) -> None:
        """
        Initialize the collector.

        Args:
            db: Database manager
            exa: Exa API client
            max_articles_per_query: Max articles to fetch per search
            lookback_days: How far back to search for news
            analyze_sentiment: Whether to run sentiment analysis on new articles
        """
        self.db = db
        self.exa = exa
        self.max_articles_per_query = max_articles_per_query
        self.lookback_days = lookback_days
        self.analyze_sentiment = analyze_sentiment
        self.sentiment_analyzer = SentimentAnalyzer() if analyze_sentiment else None

    def _url_hash(self, url: str) -> str:
        """Generate a hash for URL deduplication."""
        return hashlib.sha256(url.encode()).hexdigest()

    async def collect_for_tracked_item(
        self,
        tracked: TrackedItem,
    ) -> int:
        """
        Collect news for a single tracked item.

        Args:
            tracked: The tracked market/event

        Returns:
            Number of new articles collected
        """
        import json
        queries = json.loads(tracked.search_queries)
        cutoff = datetime.now(UTC) - timedelta(days=self.lookback_days)

        new_articles = 0

        for query in queries:
            try:
                response = await self.exa.search(
                    query,
                    num_results=self.max_articles_per_query,
                    text=True,
                    highlights=True,
                    category="news",
                    start_published_date=cutoff,
                )

                for result in response.results:
                    # Check for duplicate
                    url_hash = self._url_hash(result.url)

                    async with self.db.session_factory() as session:
                        from sqlalchemy import select
                        existing = await session.execute(
                            select(NewsArticle).where(NewsArticle.url_hash == url_hash)
                        )
                        if existing.scalar_one_or_none():
                            continue  # Already have this article

                        # Create article
                        article = NewsArticle(
                            url=result.url,
                            url_hash=url_hash,
                            title=result.title,
                            source_domain=self._extract_domain(result.url),
                            published_at=result.published_date,
                            text_snippet=result.highlights[0] if result.highlights else None,
                            full_text=result.text,
                            exa_request_id=response.request_id,
                        )
                        session.add(article)
                        await session.flush()  # Get article.id

                        # Link to market
                        link = NewsArticleMarket(
                            article_id=article.id,
                            ticker=tracked.ticker,
                        )
                        session.add(link)

                        # Analyze sentiment
                        if self.sentiment_analyzer and result.text:
                            sentiment = self.sentiment_analyzer.analyze(result.text, result.title)
                            from kalshi_research.data.models import NewsSentiment
                            sent_record = NewsSentiment(
                                article_id=article.id,
                                score=sentiment.score,
                                label=sentiment.label,
                                confidence=sentiment.confidence,
                                method=sentiment.method,
                                keywords_matched=json.dumps(sentiment.keywords_matched),
                            )
                            session.add(sent_record)

                        await session.commit()
                        new_articles += 1

            except Exception as e:
                logger.error(
                    "Failed to collect news",
                    query=query,
                    ticker=tracked.ticker,
                    error=str(e),
                )

        # Update last collected timestamp
        async with self.db.session_factory() as session:
            from sqlalchemy import update
            await session.execute(
                update(TrackedItem)
                .where(TrackedItem.id == tracked.id)
                .values(last_collected_at=datetime.now(UTC))
            )
            await session.commit()

        logger.info(
            "Collected news",
            ticker=tracked.ticker,
            new_articles=new_articles,
        )

        return new_articles

    async def collect_all(self) -> dict[str, int]:
        """
        Collect news for all active tracked items.

        Returns:
            Dictionary mapping ticker to new article count
        """
        results: dict[str, int] = {}

        async with self.db.session_factory() as session:
            from sqlalchemy import select
            query = select(TrackedItem).where(TrackedItem.is_active == True)
            tracked_items = (await session.execute(query)).scalars().all()

        for tracked in tracked_items:
            count = await self.collect_for_tracked_item(tracked)
            results[tracked.ticker] = count

        return results

    def _extract_domain(self, url: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
```

### 3.4 Sentiment Analyzer

```python
# src/kalshi_research/news/sentiment.py
from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""

    score: float  # -1.0 (negative) to +1.0 (positive)
    label: str  # "positive", "negative", "neutral"
    confidence: float  # 0.0 to 1.0
    method: str  # Analysis method used
    keywords_matched: list[str]  # Which keywords contributed


class SentimentAnalyzer:
    """
    Simple keyword-based sentiment analyzer.

    For production, consider using:
    - Exa's summary feature with sentiment prompt
    - A lightweight model like VADER
    - Claude for nuanced analysis (expensive)

    This implementation uses domain-specific keyword lists
    tuned for financial/prediction market context.
    """

    # Financial positive indicators
    POSITIVE_KEYWORDS = {
        # Market movement
        "surge", "soar", "rally", "bullish", "gains", "climbs", "jumps",
        "rises", "increases", "growth", "expansion", "acceleration",
        # Fundamentals
        "beat", "exceeds", "outperforms", "record", "breakthrough", "milestone",
        "success", "approval", "wins", "victory", "achieves",
        # Sentiment
        "optimism", "confidence", "positive", "favorable", "strong", "robust",
        "momentum", "upside", "opportunity",
        # Prediction specific
        "likely", "probable", "expected to", "poised to", "set to",
    }

    NEGATIVE_KEYWORDS = {
        # Market movement
        "plunge", "crash", "tumble", "bearish", "losses", "falls", "drops",
        "declines", "decreases", "contraction", "slowdown",
        # Fundamentals
        "miss", "fails", "underperforms", "concern", "worry", "risk",
        "threat", "crisis", "collapse", "scandal", "fraud",
        # Sentiment
        "pessimism", "fear", "negative", "unfavorable", "weak", "fragile",
        "downside", "danger", "uncertainty",
        # Prediction specific
        "unlikely", "improbable", "doubtful", "delayed", "postponed",
    }

    INTENSIFIERS = {"very", "extremely", "significantly", "sharply", "dramatically"}
    NEGATORS = {"not", "no", "never", "neither", "hardly", "barely"}

    def __init__(
        self,
        positive_weight: float = 1.0,
        negative_weight: float = 1.0,
        title_weight: float = 2.0,
    ) -> None:
        """
        Initialize the analyzer.

        Args:
            positive_weight: Weight for positive keywords
            negative_weight: Weight for negative keywords
            title_weight: Extra weight for keywords in title
        """
        self.positive_weight = positive_weight
        self.negative_weight = negative_weight
        self.title_weight = title_weight

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization."""
        text = text.lower()
        # Remove punctuation except apostrophes
        text = re.sub(r"[^\w\s']", " ", text)
        return text.split()

    def _count_keywords(
        self,
        tokens: list[str],
        keywords: set[str],
    ) -> tuple[int, list[str]]:
        """Count keyword matches and return matched keywords."""
        matched = []
        count = 0

        for i, token in enumerate(tokens):
            if token in keywords:
                # Check for negation
                if i > 0 and tokens[i - 1] in self.NEGATORS:
                    continue  # Skip negated keywords

                # Check for intensifier
                multiplier = 1.0
                if i > 0 and tokens[i - 1] in self.INTENSIFIERS:
                    multiplier = 1.5

                count += multiplier
                matched.append(token)

        return count, matched

    def analyze(self, text: str, title: str | None = None) -> SentimentResult:
        """
        Analyze sentiment of text.

        Args:
            text: Main text content
            title: Optional title (weighted higher)

        Returns:
            SentimentResult with score, label, and matched keywords
        """
        all_matched: list[str] = []

        # Analyze main text
        text_tokens = self._tokenize(text)
        pos_count, pos_matched = self._count_keywords(text_tokens, self.POSITIVE_KEYWORDS)
        neg_count, neg_matched = self._count_keywords(text_tokens, self.NEGATIVE_KEYWORDS)

        all_matched.extend(pos_matched)
        all_matched.extend(neg_matched)

        # Analyze title with extra weight
        if title:
            title_tokens = self._tokenize(title)
            title_pos, title_pos_matched = self._count_keywords(title_tokens, self.POSITIVE_KEYWORDS)
            title_neg, title_neg_matched = self._count_keywords(title_tokens, self.NEGATIVE_KEYWORDS)

            pos_count += title_pos * self.title_weight
            neg_count += title_neg * self.title_weight
            all_matched.extend(title_pos_matched)
            all_matched.extend(title_neg_matched)

        # Calculate score
        total = pos_count + neg_count
        if total == 0:
            score = 0.0
            confidence = 0.3  # Low confidence for no matches
        else:
            # Score from -1 to +1
            score = (pos_count - neg_count) / total
            # Confidence based on number of matches
            confidence = min(0.5 + (total * 0.1), 0.95)

        # Determine label
        if score > 0.1:
            label = "positive"
        elif score < -0.1:
            label = "negative"
        else:
            label = "neutral"

        return SentimentResult(
            score=score,
            label=label,
            confidence=confidence,
            method="keyword",
            keywords_matched=list(set(all_matched)),
        )


class SummarySentimentAnalyzer:
    """
    Alternative analyzer that uses Exa summaries with sentiment prompts.

    More accurate but requires additional API calls.
    """

    def __init__(self, exa: "ExaClient") -> None:
        self.exa = exa

    async def analyze(self, url: str) -> SentimentResult:
        """
        Analyze sentiment using Exa's summary with custom prompt.

        Args:
            url: URL to analyze

        Returns:
            SentimentResult
        """
        # Use contents endpoint with summary
        response = await self.exa.get_contents(
            urls=[url],
            summary={
                "query": (
                    "Analyze the sentiment of this article. "
                    "Is it positive, negative, or neutral? "
                    "What is the main conclusion?"
                )
            },
        )

        if not response.results:
            return SentimentResult(
                score=0.0,
                label="neutral",
                confidence=0.3,
                method="summary_failed",
                keywords_matched=[],
            )

        summary = response.results[0].summary or ""

        # Parse sentiment from summary
        summary_lower = summary.lower()
        if "positive" in summary_lower or "bullish" in summary_lower:
            return SentimentResult(
                score=0.6,
                label="positive",
                confidence=0.7,
                method="summary",
                keywords_matched=["positive"],
            )
        elif "negative" in summary_lower or "bearish" in summary_lower:
            return SentimentResult(
                score=-0.6,
                label="negative",
                confidence=0.7,
                method="summary",
                keywords_matched=["negative"],
            )
        else:
            return SentimentResult(
                score=0.0,
                label="neutral",
                confidence=0.6,
                method="summary",
                keywords_matched=["neutral"],
            )
```

### 3.5 Sentiment Aggregator

```python
# src/kalshi_research/news/aggregator.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from kalshi_research.data.database import DatabaseManager

logger = structlog.get_logger()


@dataclass
class SentimentSummary:
    """Aggregated sentiment for a market over a time period."""

    ticker: str
    period_start: datetime
    period_end: datetime

    # Aggregate scores
    avg_score: float  # -1.0 to +1.0
    median_score: float
    score_std: float  # Standard deviation

    # Counts
    total_articles: int
    positive_count: int
    negative_count: int
    neutral_count: int

    # Trend
    previous_avg_score: float | None = None  # For comparison
    score_change: float | None = None

    # Top topics (keywords that appeared most)
    top_keywords: list[tuple[str, int]] = field(default_factory=list)

    @property
    def sentiment_label(self) -> str:
        """Human-readable sentiment label."""
        if self.avg_score > 0.2:
            return "Bullish"
        elif self.avg_score > 0.05:
            return "Slightly Bullish"
        elif self.avg_score < -0.2:
            return "Bearish"
        elif self.avg_score < -0.05:
            return "Slightly Bearish"
        else:
            return "Neutral"

    @property
    def trend_indicator(self) -> str:
        """Trend arrow indicator."""
        if self.score_change is None:
            return "—"
        elif self.score_change > 0.05:
            return "↑"
        elif self.score_change < -0.05:
            return "↓"
        else:
            return "→"


class SentimentAggregator:
    """
    Aggregate sentiment data for reporting.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    async def get_summary(
        self,
        ticker: str,
        days: int = 7,
        compare_previous: bool = True,
    ) -> SentimentSummary | None:
        """
        Get sentiment summary for a market.

        Args:
            ticker: Market ticker
            days: Number of days to analyze
            compare_previous: Whether to compare with previous period

        Returns:
            SentimentSummary or None if no data
        """
        from sqlalchemy import func, select

        from kalshi_research.data.models import (
            NewsArticle,
            NewsArticleMarket,
            NewsSentiment,
        )

        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=days)

        async with self.db.session_factory() as session:
            # Get sentiment scores for period
            query = (
                select(
                    NewsSentiment.score,
                    NewsSentiment.label,
                    NewsSentiment.keywords_matched,
                )
                .join(NewsArticle, NewsSentiment.article_id == NewsArticle.id)
                .join(NewsArticleMarket, NewsArticle.id == NewsArticleMarket.article_id)
                .where(
                    NewsArticleMarket.ticker == ticker,
                    NewsArticle.collected_at >= period_start,
                    NewsArticle.collected_at <= period_end,
                )
            )

            results = (await session.execute(query)).all()

            if not results:
                return None

            scores = [r.score for r in results]
            labels = [r.label for r in results]

            import statistics
            avg_score = statistics.mean(scores)
            median_score = statistics.median(scores)
            score_std = statistics.stdev(scores) if len(scores) > 1 else 0.0

            positive_count = sum(1 for l in labels if l == "positive")
            negative_count = sum(1 for l in labels if l == "negative")
            neutral_count = sum(1 for l in labels if l == "neutral")

            # Count keywords
            import json
            keyword_counts: dict[str, int] = {}
            for r in results:
                if r.keywords_matched:
                    keywords = json.loads(r.keywords_matched)
                    for kw in keywords:
                        keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

            top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            summary = SentimentSummary(
                ticker=ticker,
                period_start=period_start,
                period_end=period_end,
                avg_score=avg_score,
                median_score=median_score,
                score_std=score_std,
                total_articles=len(results),
                positive_count=positive_count,
                negative_count=negative_count,
                neutral_count=neutral_count,
                top_keywords=top_keywords,
            )

            # Get previous period for comparison
            if compare_previous:
                prev_end = period_start
                prev_start = prev_end - timedelta(days=days)

                prev_query = (
                    select(func.avg(NewsSentiment.score))
                    .join(NewsArticle, NewsSentiment.article_id == NewsArticle.id)
                    .join(NewsArticleMarket, NewsArticle.id == NewsArticleMarket.article_id)
                    .where(
                        NewsArticleMarket.ticker == ticker,
                        NewsArticle.collected_at >= prev_start,
                        NewsArticle.collected_at <= prev_end,
                    )
                )

                prev_result = (await session.execute(prev_query)).scalar()
                if prev_result is not None:
                    summary.previous_avg_score = prev_result
                    summary.score_change = avg_score - prev_result

            return summary
```

### 3.6 CLI Commands

```python
# src/kalshi_research/cli/news.py
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console
from kalshi_research.paths import DEFAULT_DB_PATH

app = typer.Typer(help="News monitoring and sentiment analysis.")


@app.command("track")
def news_track(
    ticker: Annotated[str, typer.Argument(help="Market or event ticker to track")],
    event: Annotated[bool, typer.Option("--event", "-e", help="Treat as event ticker")] = False,
    queries: Annotated[str | None, typer.Option("--queries", "-q", help="Custom search queries (comma-separated)")] = None,
    db_path: Annotated[Path, typer.Option("--db", "-d", help="Path to database")] = DEFAULT_DB_PATH,
) -> None:
    """
    Start tracking news for a market or event.

    Examples:
        kalshi news track KXBTC-26JAN-T100000
        kalshi news track --event INXD-26JAN
        kalshi news track TRUMP-WIN --queries "Trump election,2024 presidential race"
    """
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.data import DatabaseManager
    from kalshi_research.data.models import TrackedItem

    async def _track() -> None:
        async with DatabaseManager(db_path) as db:
            # Generate queries if not provided
            if queries:
                search_queries = [q.strip() for q in queries.split(",")]
            else:
                # Auto-generate from market/event title
                async with KalshiPublicClient() as kalshi:
                    if event:
                        ev = await kalshi.get_event(ticker)
                        title = ev.title if ev else ticker
                    else:
                        market = await kalshi.get_market(ticker)
                        title = market.title if market else ticker

                search_queries = [title.replace("?", ""), f"{title.replace('?', '')} news"]

            async with db.session_factory() as session:
                tracked = TrackedItem(
                    ticker=ticker,
                    item_type="event" if event else "market",
                    search_queries=json.dumps(search_queries),
                )
                session.add(tracked)
                await session.commit()

            console.print(f"[green]✓[/green] Now tracking: {ticker}")
            console.print(f"[dim]Search queries: {search_queries}[/dim]")

    asyncio.run(_track())


@app.command("list-tracked")
def news_list_tracked(
    db_path: Annotated[Path, typer.Option("--db", "-d", help="Path to database")] = DEFAULT_DB_PATH,
) -> None:
    """List all tracked markets and events."""
    from kalshi_research.data import DatabaseManager
    from kalshi_research.data.models import TrackedItem

    async def _list() -> None:
        async with DatabaseManager(db_path) as db:
            from sqlalchemy import select

            async with db.session_factory() as session:
                result = await session.execute(select(TrackedItem))
                items = result.scalars().all()

            if not items:
                console.print("[yellow]No tracked items.[/yellow]")
                return

            table = Table(title="Tracked Items")
            table.add_column("Ticker", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Active", style="green")
            table.add_column("Last Collected")

            for item in items:
                last_collected = item.last_collected_at.strftime("%Y-%m-%d %H:%M") if item.last_collected_at else "Never"
                table.add_row(
                    item.ticker,
                    item.item_type,
                    "✓" if item.is_active else "✗",
                    last_collected,
                )

            console.print(table)

    asyncio.run(_list())


@app.command("collect")
def news_collect(
    ticker: Annotated[str | None, typer.Option("--ticker", "-t", help="Specific ticker to collect")] = None,
    db_path: Annotated[Path, typer.Option("--db", "-d", help="Path to database")] = DEFAULT_DB_PATH,
) -> None:
    """
    Collect news for tracked items.

    Run periodically (e.g., via cron) to keep news up to date.

    Examples:
        kalshi news collect
        kalshi news collect --ticker KXBTC-26JAN-T100000
    """
    from kalshi_research.data import DatabaseManager
    from kalshi_research.exa.client import ExaClient
    from kalshi_research.news.collector import NewsCollector

    async def _collect() -> None:
        try:
            async with ExaClient.from_env() as exa:
                async with DatabaseManager(db_path) as db:
                    collector = NewsCollector(db, exa)

                    if ticker:
                        from sqlalchemy import select
                        from kalshi_research.data.models import TrackedItem

                        async with db.session_factory() as session:
                            result = await session.execute(
                                select(TrackedItem).where(TrackedItem.ticker == ticker)
                            )
                            tracked = result.scalar_one_or_none()

                        if not tracked:
                            console.print(f"[red]Error:[/red] Not tracking {ticker}")
                            console.print("[dim]Use 'kalshi news track' first.[/dim]")
                            raise typer.Exit(1)

                        count = await collector.collect_for_tracked_item(tracked)
                        console.print(f"[green]✓[/green] Collected {count} new articles for {ticker}")
                    else:
                        results = await collector.collect_all()
                        total = sum(results.values())
                        console.print(f"[green]✓[/green] Collected {total} new articles")
                        for t, c in results.items():
                            if c > 0:
                                console.print(f"  • {t}: {c} articles")

        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print("[dim]Set EXA_API_KEY in your .env file.[/dim]")
            raise typer.Exit(1)

    asyncio.run(_collect())


@app.command("sentiment")
def news_sentiment(
    ticker: Annotated[str, typer.Argument(help="Market ticker to analyze")],
    days: Annotated[int, typer.Option("--days", "-d", help="Days to analyze")] = 7,
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    db_path: Annotated[Path, typer.Option("--db", help="Path to database")] = DEFAULT_DB_PATH,
) -> None:
    """
    Show sentiment analysis for a market.

    Examples:
        kalshi news sentiment KXBTC-26JAN-T100000
        kalshi news sentiment TRUMP-WIN --days 30
    """
    from kalshi_research.data import DatabaseManager
    from kalshi_research.news.aggregator import SentimentAggregator

    async def _sentiment() -> None:
        async with DatabaseManager(db_path) as db:
            aggregator = SentimentAggregator(db)
            summary = await aggregator.get_summary(ticker, days=days)

            if not summary:
                console.print(f"[yellow]No sentiment data for {ticker}[/yellow]")
                console.print("[dim]Run 'kalshi news collect' first.[/dim]")
                return

            if output_json:
                import json
                from dataclasses import asdict
                console.print(json.dumps(asdict(summary), indent=2, default=str))
                return

            # Rich display
            console.print(f"\n[bold]Market:[/bold] {ticker}")
            console.print(f"[dim]Period: Last {days} days[/dim]\n")

            score_color = "green" if summary.avg_score > 0 else "red" if summary.avg_score < 0 else "yellow"
            console.print(f"[bold]Sentiment Score:[/bold] [{score_color}]{summary.avg_score:+.2f}[/{score_color}] ({summary.sentiment_label})")
            console.print("─" * 35)
            console.print(f"Articles Analyzed: {summary.total_articles}")
            console.print(f"[green]Positive:[/green] {summary.positive_count} ({summary.positive_count/summary.total_articles:.0%})")
            console.print(f"[yellow]Neutral:[/yellow] {summary.neutral_count} ({summary.neutral_count/summary.total_articles:.0%})")
            console.print(f"[red]Negative:[/red] {summary.negative_count} ({summary.negative_count/summary.total_articles:.0%})")

            if summary.score_change is not None:
                change_color = "green" if summary.score_change > 0 else "red"
                console.print(f"\n[bold]Trend:[/bold] {summary.trend_indicator} [{change_color}]{summary.score_change:+.2f}[/{change_color}] from previous period")

            if summary.top_keywords:
                console.print("\n[bold]Key Topics:[/bold]")
                for kw, count in summary.top_keywords[:5]:
                    console.print(f"  • {kw} ({count})")

    asyncio.run(_sentiment())
```

---

## 4. Testing Strategy

### 4.1 Sentiment Analyzer Tests

```python
# tests/unit/news/test_sentiment.py
from kalshi_research.news.sentiment import SentimentAnalyzer, SentimentResult


class TestSentimentAnalyzer:
    """Test keyword-based sentiment analysis."""

    def test_positive_text(self) -> None:
        """Positive keywords produce positive score."""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(
            "Bitcoin surges to new highs as institutional adoption accelerates"
        )

        assert result.score > 0.3
        assert result.label == "positive"
        assert "surges" in result.keywords_matched or "accelerates" in result.keywords_matched

    def test_negative_text(self) -> None:
        """Negative keywords produce negative score."""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(
            "Market crashes amid fears of regulatory crackdown"
        )

        assert result.score < -0.3
        assert result.label == "negative"

    def test_neutral_text(self) -> None:
        """Balanced text produces neutral score."""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(
            "The weather today is sunny with a chance of clouds."
        )

        assert -0.1 < result.score < 0.1
        assert result.label == "neutral"

    def test_negation_handling(self) -> None:
        """Negated keywords are skipped."""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(
            "Bitcoin did not surge today"
        )

        assert "surge" not in result.keywords_matched

    def test_title_weighting(self) -> None:
        """Title keywords are weighted higher."""
        analyzer = SentimentAnalyzer(title_weight=2.0)

        # Same keyword in title should produce higher score
        with_title = analyzer.analyze("Article body", title="Bitcoin surges")
        without_title = analyzer.analyze("Bitcoin surges")

        # Title weighting should make a difference
        assert with_title.score != without_title.score
```

### 4.2 Collector Tests

```python
# tests/unit/news/test_collector.py
class TestNewsCollector:
    """Test news collection."""

    async def test_deduplication_by_url(self) -> None:
        """Same URL is not inserted twice."""
        # ... test with mock DB and Exa

    async def test_sentiment_analysis_triggered(self) -> None:
        """Sentiment analysis runs for new articles."""
        # ... test that NewsSentiment records are created
```

---

## 5. Implementation Tasks

### Phase 1: Database Schema

- [ ] Add `TrackedItem`, `NewsArticle`, `NewsArticleMarket`, `NewsSentiment` to models.py
- [ ] Create Alembic migration
- [ ] Write model tests

### Phase 2: Sentiment Analyzer

- [ ] Implement `SentimentAnalyzer` with keyword lists
- [ ] Write comprehensive sentiment tests
- [ ] Tune keyword lists for financial context

### Phase 3: News Collector

- [ ] Implement `NewsCollector`
- [ ] Implement `SentimentAggregator`
- [ ] Write collector tests with mocked Exa

### Phase 4: CLI

- [ ] Implement `news track` command
- [ ] Implement `news collect` command
- [ ] Implement `news sentiment` command
- [ ] Add `news list-tracked` and `news untrack`

### Phase 5: Alerts Integration

- [ ] Add `SentimentShiftCondition` to alerts system
- [ ] Test sentiment-based alerts

---

## 6. Acceptance Criteria

1. **Tracking**: Can track/untrack markets and events
2. **Collection**: News collected and deduplicated correctly
3. **Sentiment**: Scores are reasonable for test cases
4. **Aggregation**: Summary statistics computed correctly
5. **CLI**: All commands work end-to-end
6. **Test Coverage**: >85% on news/ module

---

## 7. CLI Summary

```
kalshi news
├── track           # Start tracking a market/event
├── untrack         # Stop tracking
├── list-tracked    # Show all tracked items
├── collect         # Run news collection
└── sentiment       # Show sentiment report
```

---

## 8. See Also

- [SPEC-020: Exa API Client](SPEC-020-exa-api-client.md)
- [SPEC-021: Exa Market Research](SPEC-021-exa-market-research.md)
- [SPEC-005: Alerts System](../../../_archive/specs/SPEC-005-alerts-notifications.md)
