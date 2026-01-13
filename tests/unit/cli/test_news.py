from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from typer.testing import CliRunner

from kalshi_research.api.models.event import Event as KalshiEvent
from kalshi_research.api.models.market import Market as KalshiMarket
from kalshi_research.api.models.market import MarketStatus
from kalshi_research.cli import app
from kalshi_research.data import DatabaseManager
from kalshi_research.data.models import Event as EventRow
from kalshi_research.data.models import Market as MarketRow
from kalshi_research.data.models import TrackedItem
from kalshi_research.exa import ExaConfig
from kalshi_research.news.aggregator import SentimentSummary

runner = CliRunner()


def _make_event(*, ticker: str = "EVT1") -> KalshiEvent:
    return KalshiEvent(
        event_ticker=ticker,
        series_ticker="SERIES1",
        title="Some Event",
        category="econ",
        mutually_exclusive=True,
    )


def _make_market(*, ticker: str = "MKT1", event_ticker: str = "EVT1") -> KalshiMarket:
    now = datetime.now(UTC)
    return KalshiMarket(
        ticker=ticker,
        event_ticker=event_ticker,
        series_ticker="SERIES1",
        title="Will the fed cut rates?",
        subtitle="",
        status=MarketStatus.ACTIVE,
        result="",
        yes_bid=50,
        yes_ask=52,
        no_bid=48,
        no_ask=50,
        last_price=None,
        volume=0,
        volume_24h=0,
        open_interest=0,
        open_time=now - timedelta(days=1),
        close_time=now + timedelta(days=1),
        expiration_time=now + timedelta(days=2),
        liquidity=0,
    )


def test_news_track_market_creates_tracked_item_and_upserts_targets(tmp_path) -> None:
    db_path = tmp_path / "news.db"
    market = _make_market()
    event = _make_event(ticker=market.event_ticker)

    mock_kalshi = AsyncMock()
    mock_kalshi.__aenter__.return_value = mock_kalshi
    mock_kalshi.__aexit__.return_value = None
    mock_kalshi.get_market = AsyncMock(return_value=market)
    mock_kalshi.get_event = AsyncMock(return_value=event)

    with patch("kalshi_research.api.KalshiPublicClient", return_value=mock_kalshi):
        result = runner.invoke(app, ["news", "track", market.ticker, "--db", str(db_path)])

    assert result.exit_code == 0
    assert f"Now tracking: {market.ticker} (market)" in result.stdout
    assert "Will the fed cut rates" in result.stdout

    async def _assert_db() -> None:
        async with DatabaseManager(db_path) as db, db.session_factory() as session:
            tracked = (
                await session.execute(
                    select(TrackedItem).where(TrackedItem.ticker == market.ticker)
                )
            ).scalar_one_or_none()
            assert tracked is not None
            assert tracked.item_type == "market"
            assert json.loads(tracked.search_queries)

            event_row = (
                await session.execute(select(EventRow).where(EventRow.ticker == event.event_ticker))
            ).scalar_one_or_none()
            assert event_row is not None

            market_row = (
                await session.execute(select(MarketRow).where(MarketRow.ticker == market.ticker))
            ).scalar_one_or_none()
            assert market_row is not None

    asyncio.run(_assert_db())


def test_news_track_event_with_custom_queries(tmp_path) -> None:
    db_path = tmp_path / "news.db"
    event = _make_event(ticker="EVT-AAA")

    mock_kalshi = AsyncMock()
    mock_kalshi.__aenter__.return_value = mock_kalshi
    mock_kalshi.__aexit__.return_value = None
    mock_kalshi.get_event = AsyncMock(return_value=event)

    with patch("kalshi_research.api.KalshiPublicClient", return_value=mock_kalshi):
        result = runner.invoke(
            app,
            [
                "news",
                "track",
                event.event_ticker,
                "--event",
                "--queries",
                "alpha, beta",
                "--db",
                str(db_path),
            ],
        )

    assert result.exit_code == 0
    assert f"Now tracking: {event.event_ticker} (event)" in result.stdout
    assert "alpha" in result.stdout and "beta" in result.stdout


def test_news_track_ticker_not_found_exits(tmp_path) -> None:
    from kalshi_research.api.exceptions import KalshiAPIError

    db_path = tmp_path / "news.db"

    mock_kalshi = AsyncMock()
    mock_kalshi.__aenter__.return_value = mock_kalshi
    mock_kalshi.__aexit__.return_value = None
    mock_kalshi.get_market = AsyncMock(side_effect=KalshiAPIError(404, "nope"))

    with patch("kalshi_research.api.KalshiPublicClient", return_value=mock_kalshi):
        result = runner.invoke(app, ["news", "track", "MISSING", "--db", str(db_path)])

    assert result.exit_code == 2
    assert "Ticker not found" in result.stdout


def test_news_untrack_not_tracked_exits(tmp_path) -> None:
    db_path = tmp_path / "news.db"
    result = runner.invoke(app, ["news", "untrack", "NOPE", "--db", str(db_path)])
    assert result.exit_code == 2
    assert "Not tracked" in result.stdout


def test_news_untrack_success(tmp_path) -> None:
    db_path = tmp_path / "news.db"

    async def _setup_db() -> None:
        async with DatabaseManager(db_path) as db, db.session_factory() as session:
            await db.create_tables()
            session.add(EventRow(ticker="EVT1", series_ticker="S1", title="Event 1"))
            session.add(
                MarketRow(
                    ticker="MKT1",
                    event_ticker="EVT1",
                    series_ticker="S1",
                    title="Market 1",
                    subtitle="",
                    status="active",
                    result="",
                    open_time=datetime.now(UTC),
                    close_time=datetime.now(UTC),
                    expiration_time=datetime.now(UTC),
                    category=None,
                    subcategory=None,
                )
            )
            session.add(
                TrackedItem(
                    ticker="MKT1",
                    item_type="market",
                    search_queries=json.dumps(["q"]),
                    is_active=True,
                )
            )
            await session.commit()

    asyncio.run(_setup_db())

    result = runner.invoke(app, ["news", "untrack", "MKT1", "--db", str(db_path)])
    assert result.exit_code == 0
    assert "Untracked: MKT1" in result.stdout


def test_news_list_tracked_empty(tmp_path) -> None:
    db_path = tmp_path / "news.db"
    result = runner.invoke(app, ["news", "list-tracked", "--db", str(db_path)])
    assert result.exit_code == 0
    assert "No tracked items" in result.stdout


def test_news_collect_missing_exa_key_exits(tmp_path) -> None:
    db_path = tmp_path / "news.db"

    with patch(
        "kalshi_research.exa.ExaConfig.from_env",
        side_effect=ValueError("EXA_API_KEY is required"),
    ):
        result = runner.invoke(app, ["news", "collect", "--db", str(db_path)])

    assert result.exit_code == 1
    assert "EXA_API_KEY" in result.stdout


def test_news_collect_for_ticker_prints_count(tmp_path) -> None:
    db_path = tmp_path / "news.db"

    async def _setup_db() -> None:
        async with DatabaseManager(db_path) as db, db.session_factory() as session:
            await db.create_tables()
            session.add(EventRow(ticker="EVT1", series_ticker="S1", title="Event 1"))
            session.add(
                MarketRow(
                    ticker="MKT1",
                    event_ticker="EVT1",
                    series_ticker="S1",
                    title="Market 1",
                    subtitle="",
                    status="active",
                    result="",
                    open_time=datetime.now(UTC),
                    close_time=datetime.now(UTC),
                    expiration_time=datetime.now(UTC),
                    category=None,
                    subcategory=None,
                )
            )
            session.add(
                TrackedItem(
                    ticker="MKT1",
                    item_type="market",
                    search_queries=json.dumps(["q"]),
                    is_active=True,
                )
            )
            await session.commit()

    asyncio.run(_setup_db())

    mock_exa = AsyncMock()
    mock_exa.__aenter__.return_value = mock_exa
    mock_exa.__aexit__.return_value = None

    mock_collector = AsyncMock()
    mock_collector.collect_for_tracked_item = AsyncMock(return_value=2)

    with (
        patch("kalshi_research.exa.ExaConfig.from_env", return_value=ExaConfig(api_key="test")),
        patch("kalshi_research.exa.ExaClient", return_value=mock_exa),
        patch("kalshi_research.news.NewsCollector", return_value=mock_collector),
    ):
        result = runner.invoke(
            app,
            [
                "news",
                "collect",
                "--ticker",
                "MKT1",
                "--lookback-days",
                "3",
                "--max-per-query",
                "5",
                "--db",
                str(db_path),
            ],
        )

    assert result.exit_code == 0
    assert "MKT1: 2 new article(s)" in result.stdout


def test_news_sentiment_prints_summary(tmp_path) -> None:
    db_path = tmp_path / "news.db"
    now = datetime.now(UTC)
    summary = SentimentSummary(
        ticker="MKT1",
        period_start=now - timedelta(days=7),
        period_end=now,
        avg_score=0.42,
        median_score=0.42,
        score_std=0.0,
        total_articles=3,
        positive_count=2,
        negative_count=0,
        neutral_count=1,
        previous_avg_score=0.12,
        score_change=0.3,
        top_keywords=[("rates", 2), ("inflation", 1)],
    )

    mock_aggr = AsyncMock()
    mock_aggr.get_market_summary = AsyncMock(return_value=summary)

    with patch("kalshi_research.news.SentimentAggregator", return_value=mock_aggr):
        result = runner.invoke(app, ["news", "sentiment", "MKT1", "--db", str(db_path)])

    assert result.exit_code == 0
    assert "Sentiment:" in result.stdout
    assert "rates" in result.stdout
