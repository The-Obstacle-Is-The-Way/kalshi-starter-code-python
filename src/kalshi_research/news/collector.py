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
from kalshi_research.exa.policy import ExaBudget, ExaPolicy, extract_exa_cost_total

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
        search_type: str = "auto",
        start_published_date: datetime | None = None,
        text: bool = True,
        highlights: bool = True,
        category: str | None = None,
    ) -> SearchResponse:
        """Search Exa with contents enabled (text/highlights)."""
        ...


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
        policy: ExaPolicy | None = None,
    ) -> None:
        self._exa = exa
        self._db = db
        self._sentiment = sentiment_analyzer
        self._lookback_days = lookback_days
        self._max_articles_per_query = max_articles_per_query
        self._policy = policy or ExaPolicy.from_mode()
        self._budget = ExaBudget(limit_usd=self._policy.budget_usd)
        self._budget_exhausted = False

    @property
    def budget(self) -> ExaBudget:
        return self._budget

    @property
    def budget_exhausted(self) -> bool:
        return self._budget_exhausted

    def _url_hash(self, url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _extract_domain(self, url: str) -> str:
        return urlparse(url).netloc.replace("www.", "")

    async def collect_for_tracked_item(self, tracked: TrackedItem) -> int:
        """Collect news for a single tracked market/event and persist new articles."""
        if self._budget_exhausted:
            return 0

        queries = json.loads(tracked.search_queries)
        cutoff = datetime.now(UTC) - timedelta(days=self._lookback_days)

        new_articles = 0
        for query in queries:
            include_text = self._policy.include_full_text
            include_highlights = True
            estimated_cost = self._policy.estimate_search_cost_usd(
                num_results=self._max_articles_per_query,
                include_text=include_text,
                include_highlights=include_highlights,
                search_type=self._policy.exa_search_type,
            )
            if not self._budget.can_spend(estimated_cost):
                self._budget_exhausted = True
                logger.info(
                    "News collection budget exhausted",
                    budget_spent_usd=self._budget.spent_usd,
                    budget_limit_usd=self._budget.limit_usd,
                )
                break

            try:
                response = await self._exa.search_and_contents(
                    query,
                    num_results=self._max_articles_per_query,
                    search_type=self._policy.exa_search_type,
                    text=include_text,
                    highlights=include_highlights,
                    category="news",
                    start_published_date=cutoff,
                )
                self._budget.record_spend(extract_exa_cost_total(response))
            except Exception as exc:
                logger.warning(
                    "Failed to collect news for query",
                    ticker=tracked.ticker,
                    query=query,
                    error=str(exc),
                    exc_info=True,
                )
                continue

            for result in response.results:
                url_hash = self._url_hash(result.url)
                async with self._db.session_factory() as session:
                    try:
                        async with session.begin():
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
                            await session.flush()

                            if tracked.item_type == "event":
                                session.add(
                                    NewsArticleEvent(
                                        article_id=article.id, event_ticker=tracked.ticker
                                    )
                                )
                            else:
                                session.add(
                                    NewsArticleMarket(article_id=article.id, ticker=tracked.ticker)
                                )

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

                            new_articles += 1
                    except IntegrityError:
                        # Duplicate article (race condition) - skip and continue
                        continue

        async with self._db.session_factory() as session, session.begin():
            await session.execute(
                update(TrackedItem)
                .where(TrackedItem.id == tracked.id)
                .values(last_collected_at=datetime.now(UTC))
            )

        logger.info("Collected news", ticker=tracked.ticker, new_articles=new_articles)
        return new_articles

    async def collect_all(self) -> dict[str, int]:
        """Collect news for all active tracked items and return per-ticker insert counts."""
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
            if self._budget_exhausted:
                break
        return results
