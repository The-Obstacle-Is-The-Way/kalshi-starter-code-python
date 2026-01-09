from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from kalshi_research.data import DatabaseManager
from kalshi_research.data.models import (
    Event,
    Market,
    NewsArticle,
    NewsArticleEvent,
    NewsArticleMarket,
    NewsSentiment,
)
from kalshi_research.news import SentimentAggregator
from kalshi_research.news.aggregator import SentimentSummary

pytestmark = [pytest.mark.unit]


def test_sentiment_summary_label_and_trend_properties() -> None:
    now = datetime.now(UTC)
    summary = SentimentSummary(
        ticker="TICK",
        period_start=now - timedelta(days=7),
        period_end=now,
        avg_score=0.3,
        median_score=0.3,
        score_std=0.0,
        total_articles=1,
        positive_count=1,
        negative_count=0,
        neutral_count=0,
    )
    assert summary.sentiment_label == "Bullish"
    assert summary.trend_indicator == "—"

    assert replace(summary, avg_score=-0.3).sentiment_label == "Bearish"
    assert replace(summary, avg_score=0.0).sentiment_label == "Neutral"

    assert replace(summary, score_change=0.1).trend_indicator == "↑"
    assert replace(summary, score_change=-0.1).trend_indicator == "↓"
    assert replace(summary, score_change=0.01).trend_indicator == "→"


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


@pytest.mark.asyncio
async def test_aggregator_market_summary_without_previous_period(tmp_path) -> None:
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

            cur_article = NewsArticle(
                url="https://example.com/cur-only",
                url_hash="cur-only",
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
                    score=0.1,
                    label="neutral",
                    confidence=0.8,
                    method="keyword",
                    keywords_matched=None,
                )
            )
            await session.commit()

        summary = await SentimentAggregator(db).get_market_summary(
            "MKT1", days=7, compare_previous=True
        )
        assert summary is not None
        assert summary.previous_avg_score is None
        assert summary.score_change is None


@pytest.mark.asyncio
async def test_aggregator_event_summary(tmp_path) -> None:
    now = datetime.now(UTC)
    db_path = tmp_path / "agg-event.db"

    async with DatabaseManager(db_path) as db:
        await db.create_tables()

        async with db.session_factory() as session:
            session.add(Event(ticker="EVT1", series_ticker="S1", title="Event 1"))

            prev_article = NewsArticle(
                url="https://example.com/prev",
                url_hash="prev-e",
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
            session.add(NewsArticleEvent(article_id=prev_article.id, event_ticker="EVT1"))
            session.add(
                NewsSentiment(
                    article_id=prev_article.id,
                    analyzed_at=now - timedelta(days=8),
                    score=-0.2,
                    label="negative",
                    confidence=0.8,
                    method="keyword",
                    keywords_matched=json.dumps(["risk"]),
                )
            )

            cur_article = NewsArticle(
                url="https://example.com/cur",
                url_hash="cur-e",
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
            session.add(NewsArticleEvent(article_id=cur_article.id, event_ticker="EVT1"))
            session.add(
                NewsSentiment(
                    article_id=cur_article.id,
                    analyzed_at=now - timedelta(days=1),
                    score=0.4,
                    label="positive",
                    confidence=0.8,
                    method="keyword",
                    keywords_matched=json.dumps(["rally"]),
                )
            )
            await session.commit()

        summary = await SentimentAggregator(db).get_event_summary(
            "EVT1", days=7, compare_previous=True
        )
        assert summary is not None
        assert summary.total_articles == 1
        assert summary.avg_score == 0.4
        assert summary.score_change is not None
        assert summary.score_change == pytest.approx(0.6)
