from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from kalshi_research.data import DatabaseManager
from kalshi_research.data.models import (
    Event,
    Market,
    NewsArticle,
    NewsArticleEvent,
    NewsArticleMarket,
    NewsSentiment,
)
from kalshi_research.exa.models.search import SearchResponse, SearchResult
from kalshi_research.news import NewsCollector, NewsTracker, SentimentAnalyzer

pytestmark = [pytest.mark.unit]


class StubExaClient:
    def __init__(self, response: SearchResponse) -> None:
        self._response = response

    async def search_and_contents(self, *_args, **_kwargs) -> SearchResponse:
        return self._response


@pytest.mark.asyncio
async def test_collector_dedupes_by_url_hash_and_writes_sentiment(tmp_path) -> None:
    now = datetime.now(UTC)
    response = SearchResponse(
        request_id="req-1",
        results=[
            SearchResult(
                id="1",
                url="https://example.com/a",
                title="Markets rally on strong momentum",
                published_date=now - timedelta(hours=1),
                text="Markets rally and surge with strong momentum.",
                highlights=["Markets rally and surge"],
            )
        ],
        search_type="neural",
        auto_date=None,
        context=None,
        cost_dollars=None,
    )

    db_path = tmp_path / "collector.db"
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
            await session.commit()

        tracked = await NewsTracker(db).track(
            ticker="MKT1",
            item_type="market",
            search_queries=["Market 1"],
        )

        collector = NewsCollector(
            exa=StubExaClient(response),
            db=db,
            sentiment_analyzer=SentimentAnalyzer(),
            lookback_days=7,
            max_articles_per_query=5,
        )

        inserted = await collector.collect_for_tracked_item(tracked)
        assert inserted == 1

        inserted_again = await collector.collect_for_tracked_item(tracked)
        assert inserted_again == 0

        async with db.session_factory() as session:
            assert len((await session.execute(select(NewsArticle))).scalars().all()) == 1
            assert len((await session.execute(select(NewsArticleMarket))).scalars().all()) == 1
            sentiments = (await session.execute(select(NewsSentiment))).scalars().all()
            assert len(sentiments) == 1
            assert sentiments[0].label in {"positive", "neutral", "negative"}
            assert sentiments[0].keywords_matched is not None
            json.loads(sentiments[0].keywords_matched)


@pytest.mark.asyncio
async def test_collector_links_event_articles(tmp_path) -> None:
    now = datetime.now(UTC)
    response = SearchResponse(
        request_id="req-2",
        results=[
            SearchResult(
                id="2",
                url="https://example.com/b",
                title="Neutral update",
                published_date=now - timedelta(hours=2),
                text="No material changes reported.",
                highlights=["No material changes"],
            )
        ],
        search_type="neural",
        auto_date=None,
        context=None,
        cost_dollars=None,
    )

    db_path = tmp_path / "collector_event.db"
    async with DatabaseManager(db_path) as db:
        await db.create_tables()

        async with db.session_factory() as session:
            session.add(Event(ticker="EVT2", series_ticker="S2", title="Event 2"))
            await session.commit()

        tracked = await NewsTracker(db).track(
            ticker="EVT2",
            item_type="event",
            search_queries=["Event 2"],
        )

        collector = NewsCollector(
            exa=StubExaClient(response),
            db=db,
            sentiment_analyzer=None,
        )

        inserted = await collector.collect_for_tracked_item(tracked)
        assert inserted == 1

        async with db.session_factory() as session:
            assert len((await session.execute(select(NewsArticleEvent))).scalars().all()) == 1
