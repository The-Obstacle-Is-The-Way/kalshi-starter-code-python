"""Aggregate sentiment data from stored news articles."""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from kalshi_research.data.models import (
    NewsArticle,
    NewsArticleEvent,
    NewsArticleMarket,
    NewsSentiment,
)

if TYPE_CHECKING:
    from kalshi_research.data.database import DatabaseManager


@dataclass(frozen=True, slots=True)
class SentimentSummary:
    """Aggregated sentiment summary for a market/event over a time period."""

    ticker: str
    period_start: datetime
    period_end: datetime

    avg_score: float
    median_score: float
    score_std: float

    total_articles: int
    positive_count: int
    negative_count: int
    neutral_count: int

    previous_avg_score: float | None = None
    score_change: float | None = None
    top_keywords: list[tuple[str, int]] = field(default_factory=list)

    @property
    def sentiment_label(self) -> str:
        """Return a human-friendly label derived from `avg_score`."""
        if self.avg_score > 0.2:
            return "Bullish"
        if self.avg_score > 0.05:
            return "Slightly Bullish"
        if self.avg_score < -0.2:
            return "Bearish"
        if self.avg_score < -0.05:
            return "Slightly Bearish"
        return "Neutral"

    @property
    def trend_indicator(self) -> str:
        """Return a trend indicator arrow derived from `score_change`."""
        if self.score_change is None:
            return "—"
        if self.score_change > 0.05:
            return "↑"
        if self.score_change < -0.05:
            return "↓"
        return "→"


class SentimentAggregator:
    """Aggregates sentiment data for reporting and alerting."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def get_market_summary(
        self,
        ticker: str,
        *,
        days: int = 7,
        compare_previous: bool = True,
    ) -> SentimentSummary | None:
        """Aggregate stored sentiment for a market over the last N days."""
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=days)

        async with self._db.session_factory() as session:
            query = (
                select(NewsSentiment.score, NewsSentiment.label, NewsSentiment.keywords_matched)
                .join(NewsArticle, NewsSentiment.article_id == NewsArticle.id)
                .join(NewsArticleMarket, NewsArticle.id == NewsArticleMarket.article_id)
                .where(NewsArticleMarket.ticker == ticker)
                .where(
                    NewsArticle.collected_at >= period_start,
                    NewsArticle.collected_at <= period_end,
                )
            )

            rows = (await session.execute(query)).all()
            if not rows:
                return None

            scores = [float(r.score) for r in rows]
            labels = [str(r.label) for r in rows]

            avg_score = statistics.mean(scores)
            median_score = statistics.median(scores)
            score_std = statistics.stdev(scores) if len(scores) > 1 else 0.0

            positive_count = sum(1 for label in labels if label == "positive")
            negative_count = sum(1 for label in labels if label == "negative")
            neutral_count = sum(1 for label in labels if label == "neutral")

            keyword_counts: dict[str, int] = {}
            for r in rows:
                if not r.keywords_matched:
                    continue
                for kw in json.loads(r.keywords_matched):
                    keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
            top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            summary = SentimentSummary(
                ticker=ticker,
                period_start=period_start,
                period_end=period_end,
                avg_score=avg_score,
                median_score=median_score,
                score_std=score_std,
                total_articles=len(rows),
                positive_count=positive_count,
                negative_count=negative_count,
                neutral_count=neutral_count,
                top_keywords=top_keywords,
            )

            if not compare_previous:
                return summary

            prev_end = period_start
            prev_start = prev_end - timedelta(days=days)
            prev_query = (
                select(func.avg(NewsSentiment.score))
                .join(NewsArticle, NewsSentiment.article_id == NewsArticle.id)
                .join(NewsArticleMarket, NewsArticle.id == NewsArticleMarket.article_id)
                .where(NewsArticleMarket.ticker == ticker)
                .where(
                    NewsArticle.collected_at >= prev_start,
                    NewsArticle.collected_at <= prev_end,
                )
            )
            prev_avg = (await session.execute(prev_query)).scalar()
            if prev_avg is None:
                return summary

            return replace(
                summary,
                previous_avg_score=float(prev_avg),
                score_change=avg_score - float(prev_avg),
            )

    async def get_event_summary(
        self,
        event_ticker: str,
        *,
        days: int = 7,
        compare_previous: bool = True,
    ) -> SentimentSummary | None:
        """Aggregate stored sentiment for an event over the last N days."""
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=days)

        async with self._db.session_factory() as session:
            query = (
                select(NewsSentiment.score, NewsSentiment.label, NewsSentiment.keywords_matched)
                .join(NewsArticle, NewsSentiment.article_id == NewsArticle.id)
                .join(NewsArticleEvent, NewsArticle.id == NewsArticleEvent.article_id)
                .where(NewsArticleEvent.event_ticker == event_ticker)
                .where(
                    NewsArticle.collected_at >= period_start,
                    NewsArticle.collected_at <= period_end,
                )
            )

            rows = (await session.execute(query)).all()
            if not rows:
                return None

            scores = [float(r.score) for r in rows]
            labels = [str(r.label) for r in rows]

            avg_score = statistics.mean(scores)
            median_score = statistics.median(scores)
            score_std = statistics.stdev(scores) if len(scores) > 1 else 0.0

            positive_count = sum(1 for label in labels if label == "positive")
            negative_count = sum(1 for label in labels if label == "negative")
            neutral_count = sum(1 for label in labels if label == "neutral")

            keyword_counts: dict[str, int] = {}
            for r in rows:
                if not r.keywords_matched:
                    continue
                for kw in json.loads(r.keywords_matched):
                    keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
            top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            summary = SentimentSummary(
                ticker=event_ticker,
                period_start=period_start,
                period_end=period_end,
                avg_score=avg_score,
                median_score=median_score,
                score_std=score_std,
                total_articles=len(rows),
                positive_count=positive_count,
                negative_count=negative_count,
                neutral_count=neutral_count,
                top_keywords=top_keywords,
            )

            if not compare_previous:
                return summary

            prev_end = period_start
            prev_start = prev_end - timedelta(days=days)
            prev_query = (
                select(func.avg(NewsSentiment.score))
                .join(NewsArticle, NewsSentiment.article_id == NewsArticle.id)
                .join(NewsArticleEvent, NewsArticle.id == NewsArticleEvent.article_id)
                .where(NewsArticleEvent.event_ticker == event_ticker)
                .where(
                    NewsArticle.collected_at >= prev_start,
                    NewsArticle.collected_at <= prev_end,
                )
            )
            prev_avg = (await session.execute(prev_query)).scalar()
            if prev_avg is None:
                return summary

            return replace(
                summary,
                previous_avg_score=float(prev_avg),
                score_change=avg_score - float(prev_avg),
            )
