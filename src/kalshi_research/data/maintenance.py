"""Database maintenance helpers (pruning, retention)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select

from kalshi_research.data.models import (
    NewsArticle,
    NewsArticleEvent,
    NewsArticleMarket,
    NewsSentiment,
    PriceSnapshot,
)

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class PruneCounts:
    """Row counts that would be (or were) pruned."""

    price_snapshots: int = 0
    news_articles: int = 0
    news_article_markets: int = 0
    news_article_events: int = 0
    news_sentiments: int = 0

    @property
    def total_rows(self) -> int:
        return (
            self.price_snapshots
            + self.news_articles
            + self.news_article_markets
            + self.news_article_events
            + self.news_sentiments
        )


async def compute_prune_counts(
    session: AsyncSession,
    *,
    snapshots_before: datetime | None,
    news_before: datetime | None,
) -> PruneCounts:
    """Compute how many rows match the prune criteria."""
    snapshot_count = 0
    if snapshots_before is not None:
        result = await session.execute(
            select(func.count(PriceSnapshot.id)).where(
                PriceSnapshot.snapshot_time < snapshots_before
            )
        )
        snapshot_count = int(result.scalar_one())

    news_article_count = 0
    news_market_count = 0
    news_event_count = 0
    news_sentiment_count = 0
    if news_before is not None:
        old_article_ids = select(NewsArticle.id).where(NewsArticle.collected_at < news_before)

        result = await session.execute(
            select(func.count(NewsArticle.id)).where(NewsArticle.collected_at < news_before)
        )
        news_article_count = int(result.scalar_one())

        result = await session.execute(
            select(func.count(NewsArticleMarket.article_id)).where(
                NewsArticleMarket.article_id.in_(old_article_ids)
            )
        )
        news_market_count = int(result.scalar_one())

        result = await session.execute(
            select(func.count(NewsArticleEvent.article_id)).where(
                NewsArticleEvent.article_id.in_(old_article_ids)
            )
        )
        news_event_count = int(result.scalar_one())

        result = await session.execute(
            select(func.count(NewsSentiment.id)).where(
                NewsSentiment.article_id.in_(old_article_ids)
            )
        )
        news_sentiment_count = int(result.scalar_one())

    return PruneCounts(
        price_snapshots=snapshot_count,
        news_articles=news_article_count,
        news_article_markets=news_market_count,
        news_article_events=news_event_count,
        news_sentiments=news_sentiment_count,
    )


async def apply_prune(
    session: AsyncSession,
    *,
    snapshots_before: datetime | None,
    news_before: datetime | None,
) -> PruneCounts:
    """Apply pruning for the given criteria. Returns counts removed."""
    counts = await compute_prune_counts(
        session,
        snapshots_before=snapshots_before,
        news_before=news_before,
    )

    if snapshots_before is not None and counts.price_snapshots:
        await session.execute(
            delete(PriceSnapshot).where(PriceSnapshot.snapshot_time < snapshots_before)
        )

    if news_before is not None and counts.news_articles:
        old_article_ids = select(NewsArticle.id).where(NewsArticle.collected_at < news_before)

        # FK-safe order: delete dependents first.
        if counts.news_sentiments:
            await session.execute(
                delete(NewsSentiment).where(NewsSentiment.article_id.in_(old_article_ids))
            )
        if counts.news_article_markets:
            await session.execute(
                delete(NewsArticleMarket).where(NewsArticleMarket.article_id.in_(old_article_ids))
            )
        if counts.news_article_events:
            await session.execute(
                delete(NewsArticleEvent).where(NewsArticleEvent.article_id.in_(old_article_ids))
            )

        await session.execute(delete(NewsArticle).where(NewsArticle.collected_at < news_before))

    return counts
