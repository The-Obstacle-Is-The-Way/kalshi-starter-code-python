from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from kalshi_research.data import DatabaseManager
from kalshi_research.data.maintenance import PruneCounts, apply_prune, compute_prune_counts
from kalshi_research.data.models import (
    Event,
    Market,
    NewsArticle,
    NewsArticleMarket,
    NewsSentiment,
    PriceSnapshot,
)


@pytest.mark.asyncio
async def test_prune_deletes_old_snapshots_and_news(tmp_path) -> None:
    db_path = tmp_path / "maintenance.db"
    db = DatabaseManager(db_path)
    try:
        await db.create_tables()

        now = datetime.now(UTC)
        old_time = now - timedelta(days=10)
        cutoff = now - timedelta(days=5)

        async with db.session_factory() as session, session.begin():
            session.add(Event(ticker="EVT1", series_ticker="S1", title="Event 1"))
            session.add(
                Market(
                    ticker="MKT1",
                    event_ticker="EVT1",
                    title="Market 1",
                    status="active",
                    open_time=now - timedelta(days=30),
                    close_time=now + timedelta(days=30),
                    expiration_time=now + timedelta(days=60),
                )
            )

            session.add(
                PriceSnapshot(
                    ticker="MKT1",
                    snapshot_time=old_time,
                    yes_bid=40,
                    yes_ask=42,
                    no_bid=58,
                    no_ask=60,
                    last_price=41,
                    volume=100,
                    volume_24h=50,
                    open_interest=10,
                )
            )
            session.add(
                PriceSnapshot(
                    ticker="MKT1",
                    snapshot_time=now,
                    yes_bid=45,
                    yes_ask=47,
                    no_bid=53,
                    no_ask=55,
                    last_price=46,
                    volume=200,
                    volume_24h=100,
                    open_interest=20,
                )
            )

            old_article = NewsArticle(
                url="https://example.com/old",
                url_hash="old",
                title="Old",
                source_domain="example.com",
                collected_at=old_time,
            )
            new_article = NewsArticle(
                url="https://example.com/new",
                url_hash="new",
                title="New",
                source_domain="example.com",
                collected_at=now,
            )
            session.add_all([old_article, new_article])
            await session.flush()

            session.add(NewsArticleMarket(article_id=old_article.id, ticker="MKT1"))
            session.add(NewsArticleMarket(article_id=new_article.id, ticker="MKT1"))
            session.add(
                NewsSentiment(
                    article_id=old_article.id,
                    analyzed_at=old_time,
                    score=0.1,
                    label="neutral",
                    confidence=0.5,
                    method="test",
                    keywords_matched="[]",
                )
            )
            session.add(
                NewsSentiment(
                    article_id=new_article.id,
                    analyzed_at=now,
                    score=0.2,
                    label="neutral",
                    confidence=0.6,
                    method="test",
                    keywords_matched="[]",
                )
            )

        async with db.session_factory() as session:
            counts = await compute_prune_counts(
                session,
                snapshots_before=cutoff,
                news_before=cutoff,
            )

        assert counts == PruneCounts(
            price_snapshots=1,
            news_articles=1,
            news_article_markets=1,
            news_article_events=0,
            news_sentiments=1,
        )

        async with db.session_factory() as session, session.begin():
            removed = await apply_prune(
                session,
                snapshots_before=cutoff,
                news_before=cutoff,
            )

        assert removed == counts

        async with db.session_factory() as session:
            snapshot_total = (
                await session.execute(select(func.count(PriceSnapshot.id)))
            ).scalar_one()
            article_total = (await session.execute(select(func.count(NewsArticle.id)))).scalar_one()
            market_join_total = (
                await session.execute(select(func.count(NewsArticleMarket.article_id)))
            ).scalar_one()
            sentiment_total = (
                await session.execute(select(func.count(NewsSentiment.id)))
            ).scalar_one()

        assert snapshot_total == 1
        assert article_total == 1
        assert market_join_total == 1
        assert sentiment_total == 1
    finally:
        await db.close()
