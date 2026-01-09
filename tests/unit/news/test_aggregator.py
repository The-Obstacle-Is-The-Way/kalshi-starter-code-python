from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from kalshi_research.data import DatabaseManager
from kalshi_research.data.models import (
    Event,
    Market,
    NewsArticle,
    NewsArticleMarket,
    NewsSentiment,
)
from kalshi_research.news import SentimentAggregator

pytestmark = [pytest.mark.unit]


@pytest.mark.asyncio
async def test_aggregator_computes_summary_and_change(tmp_path) -> None:
    now = datetime.now(UTC)
    db_path = tmp_path / "agg.db"

    async with DatabaseManager(db_path) as db:
        await db.create_tables()

        async with db.session_factory() as session:
            session.add(Event(ticker="EVT1", series_ticker="S1", title="Event 1"))
            session.add(
                Market(
                    ticker="MKT1",
                    event_ticker="EVT1",
                    series_ticker="S1",
                    title="Market 1",
                    subtitle="",
                    status="active",
                    result="",
                    open_time=now - timedelta(days=1),
                    close_time=now + timedelta(days=1),
                    expiration_time=now + timedelta(days=2),
                    category=None,
                    subcategory=None,
                )
            )

            # Previous period article (~8 days ago)
            prev_article = NewsArticle(
                url="https://example.com/prev",
                url_hash="prev",
                title="Prev",
                source_domain="example.com",
                published_at=now - timedelta(days=8),
                collected_at=now - timedelta(days=8),
                text_snippet="prev",
                full_text="prev",
                exa_request_id=None,
            )
            session.add(prev_article)
            await session.flush()
            session.add(NewsArticleMarket(article_id=prev_article.id, ticker="MKT1"))
            session.add(
                NewsSentiment(
                    article_id=prev_article.id,
                    analyzed_at=now - timedelta(days=8),
                    score=-0.5,
                    label="negative",
                    confidence=0.8,
                    method="keyword",
                    keywords_matched=json.dumps(["risk"]),
                )
            )

            # Current period article (~1 day ago)
            cur_article = NewsArticle(
                url="https://example.com/cur",
                url_hash="cur",
                title="Cur",
                source_domain="example.com",
                published_at=now - timedelta(days=1),
                collected_at=now - timedelta(days=1),
                text_snippet="cur",
                full_text="cur",
                exa_request_id=None,
            )
            session.add(cur_article)
            await session.flush()
            session.add(NewsArticleMarket(article_id=cur_article.id, ticker="MKT1"))
            session.add(
                NewsSentiment(
                    article_id=cur_article.id,
                    analyzed_at=now - timedelta(days=1),
                    score=0.5,
                    label="positive",
                    confidence=0.8,
                    method="keyword",
                    keywords_matched=json.dumps(["rally"]),
                )
            )

            await session.commit()

        summary = await SentimentAggregator(db).get_market_summary(
            "MKT1", days=7, compare_previous=True
        )
        assert summary is not None
        assert summary.total_articles == 1
        assert summary.avg_score == 0.5
        assert summary.score_change is not None
        # current (0.5) - previous (-0.5) = 1.0
        assert summary.score_change == pytest.approx(1.0)
        assert summary.top_keywords
