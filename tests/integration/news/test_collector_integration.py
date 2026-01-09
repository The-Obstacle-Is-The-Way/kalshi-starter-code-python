"""
Integration test: NewsCollector should work end-to-end with ExaClient.

This specifically guards against datetime serialization regressions (BUG-046).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
import respx
from httpx import Response
from sqlalchemy import select

from kalshi_research.data.database import DatabaseManager
from kalshi_research.data.models import Event, Market, NewsArticle, NewsArticleMarket, TrackedItem
from kalshi_research.exa.client import ExaClient
from kalshi_research.exa.config import ExaConfig
from kalshi_research.news.collector import NewsCollector

pytestmark = [pytest.mark.integration]


@respx.mock
async def test_collect_for_tracked_market_inserts_articles_and_links(tmp_path) -> None:
    db_path = tmp_path / "news.db"
    now = datetime.now(UTC)

    async with DatabaseManager(db_path) as db, ExaClient(ExaConfig(api_key="test-key")) as exa:
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
                    open_time=now,
                    close_time=now,
                    expiration_time=now,
                    category=None,
                    subcategory=None,
                )
            )
            tracked = TrackedItem(
                ticker="MKT1",
                item_type="market",
                search_queries=json.dumps(["fed rates"]),
                is_active=True,
            )
            session.add(tracked)
            await session.commit()

        route = respx.post("https://api.exa.ai/search").mock(
            return_value=Response(
                200,
                json={
                    "requestId": "req_news_1",
                    "results": [
                        {
                            "id": "doc_1",
                            "url": "https://example.com/a",
                            "title": "Example",
                            "publishedDate": "2026-01-01T00:00:00Z",
                            "text": "Some text",
                            "highlights": ["Snippet"],
                        }
                    ],
                },
            )
        )

        collector = NewsCollector(
            exa=exa,
            db=db,
            sentiment_analyzer=None,
            lookback_days=7,
            max_articles_per_query=25,
        )
        new_count = await collector.collect_for_tracked_item(tracked)

        assert new_count == 1
        assert route.call_count == 1

        body = json.loads(route.calls[0].request.content.decode("utf-8"))
        assert isinstance(body["startPublishedDate"], str)

        async with db.session_factory() as session:
            article = (await session.execute(select(NewsArticle))).scalars().one()
            assert article.url == "https://example.com/a"
            assert article.exa_request_id == "req_news_1"

            link = (await session.execute(select(NewsArticleMarket))).scalars().one()
            assert link.ticker == "MKT1"
            assert link.article_id == article.id
