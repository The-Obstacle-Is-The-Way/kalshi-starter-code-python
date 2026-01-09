"""News collection pipeline using Exa."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urlparse

import structlog
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from kalshi_research.data.models import (
    NewsArticle,
    NewsArticleEvent,
    NewsArticleMarket,
    NewsSentiment,
    TrackedItem,
)

if TYPE_CHECKING:
    from kalshi_research.data.database import DatabaseManager
    from kalshi_research.exa.models.search import SearchResponse
    from kalshi_research.news.sentiment import SentimentAnalyzer

logger = structlog.get_logger()


class ExaNewsClient(Protocol):
    async def search_and_contents(
        self,
        query: str,
        *,
        num_results: int = 10,
        start_published_date: datetime | None = None,
        text: bool = True,
        highlights: bool = True,
        category: str | None = None,
    ) -> SearchResponse: ...


class NewsCollector:
    """Collects news for tracked items and stores it in the database."""

    def __init__(
        self,
        *,
        exa: ExaNewsClient,
        db: DatabaseManager,
        sentiment_analyzer: SentimentAnalyzer | None = None,
        lookback_days: int = 7,
        max_articles_per_query: int = 25,
    ) -> None:
        self._exa = exa
        self._db = db
        self._sentiment = sentiment_analyzer
        self._lookback_days = lookback_days
        self._max_articles_per_query = max_articles_per_query

    def _url_hash(self, url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _extract_domain(self, url: str) -> str:
        return urlparse(url).netloc.replace("www.", "")

    async def collect_for_tracked_item(self, tracked: TrackedItem) -> int:
        queries = json.loads(tracked.search_queries)
        cutoff = datetime.now(UTC) - timedelta(days=self._lookback_days)

        new_articles = 0
        for query in queries:
            try:
                response = await self._exa.search_and_contents(
                    query,
                    num_results=self._max_articles_per_query,
                    text=True,
                    highlights=True,
                    category="news",
                    start_published_date=cutoff,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to collect news for query",
                    ticker=tracked.ticker,
                    query=query,
                    error=str(exc),
                )
                continue

            for result in response.results:
                url_hash = self._url_hash(result.url)
                async with self._db.session_factory() as session:
                    existing = (
                        await session.execute(
                            select(NewsArticle.id).where(NewsArticle.url_hash == url_hash)
                        )
                    ).scalar_one_or_none()
                    if existing is not None:
                        continue

                    article = NewsArticle(
                        url=result.url,
                        url_hash=url_hash,
                        title=result.title,
                        source_domain=self._extract_domain(result.url),
                        published_at=result.published_date,
                        text_snippet=(result.highlights[0] if result.highlights else None),
                        full_text=result.text,
                        exa_request_id=response.request_id,
                    )
                    session.add(article)
                    try:
                        await session.flush()
                    except IntegrityError:
                        await session.rollback()
                        continue

                    if tracked.item_type == "event":
                        session.add(
                            NewsArticleEvent(article_id=article.id, event_ticker=tracked.ticker)
                        )
                    else:
                        session.add(NewsArticleMarket(article_id=article.id, ticker=tracked.ticker))

                    if self._sentiment and result.text:
                        sentiment = self._sentiment.analyze(result.text, result.title)
                        session.add(
                            NewsSentiment(
                                article_id=article.id,
                                score=sentiment.score,
                                label=sentiment.label,
                                confidence=sentiment.confidence,
                                method=sentiment.method,
                                keywords_matched=json.dumps(sentiment.keywords_matched),
                            )
                        )

                    try:
                        await session.commit()
                    except IntegrityError:
                        await session.rollback()
                        continue

                    new_articles += 1

        async with self._db.session_factory() as session:
            await session.execute(
                update(TrackedItem)
                .where(TrackedItem.id == tracked.id)
                .values(last_collected_at=datetime.now(UTC))
            )
            await session.commit()

        logger.info("Collected news", ticker=tracked.ticker, new_articles=new_articles)
        return new_articles

    async def collect_all(self) -> dict[str, int]:
        results: dict[str, int] = {}
        async with self._db.session_factory() as session:
            tracked_items = (
                (
                    await session.execute(
                        select(TrackedItem).where(TrackedItem.is_active == True)  # noqa: E712
                    )
                )
                .scalars()
                .all()
            )

        for tracked in tracked_items:
            results[tracked.ticker] = await self.collect_for_tracked_item(tracked)
        return results
