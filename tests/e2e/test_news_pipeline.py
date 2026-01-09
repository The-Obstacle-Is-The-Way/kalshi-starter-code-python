from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest
import respx
from httpx import Response
from typer.testing import CliRunner

from kalshi_research.cli import app

pytestmark = [pytest.mark.e2e]


def _event_dict(event_ticker: str = "EVT1") -> dict[str, Any]:
    return {
        "event_ticker": event_ticker,
        "series_ticker": "SERIES1",
        "title": "Event 1",
        "category": "Test",
    }


def _market_dict(ticker: str, *, event_ticker: str = "EVT1") -> dict[str, Any]:
    return {
        "ticker": ticker,
        "event_ticker": event_ticker,
        "series_ticker": "SERIES1",
        "title": f"Market {ticker}",
        "subtitle": "",
        "status": "active",
        "result": "",
        "yes_bid": 40,
        "yes_ask": 42,
        "no_bid": 58,
        "no_ask": 60,
        "last_price": 41,
        "volume": 1_000,
        "volume_24h": 10_000,
        "open_interest": 100,
        "liquidity": 1_000,
        "open_time": "2024-01-01T00:00:00Z",
        "close_time": "2025-01-01T00:00:00Z",
        "expiration_time": "2025-01-02T00:00:00Z",
    }


@respx.mock
def test_news_track_then_collect_writes_articles_and_sentiment() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        db_path = Path("data/kalshi.db")

        respx.get("https://api.elections.kalshi.com/trade-api/v2/markets/MKT1").mock(
            return_value=Response(200, json={"market": _market_dict("MKT1")})
        )
        respx.get("https://api.elections.kalshi.com/trade-api/v2/events/EVT1").mock(
            return_value=Response(200, json={"event": _event_dict("EVT1")})
        )

        exa_route = respx.post("https://api.exa.ai/search").mock(
            return_value=Response(
                200,
                json={
                    "requestId": "req_news_1",
                    "results": [
                        {
                            "id": "doc_1",
                            "url": "https://example.com/a",
                            "title": "Market surges on optimism",
                            "publishedDate": "2026-01-01T00:00:00Z",
                            "text": "The market is likely to surge.",
                            "highlights": ["Market surges"],
                        }
                    ],
                },
            )
        )

        track = runner.invoke(app, ["news", "track", "MKT1", "--db", str(db_path)])
        assert track.exit_code == 0

        collect = runner.invoke(
            app,
            ["news", "collect", "--db", str(db_path), "--ticker", "MKT1"],
            env={"EXA_API_KEY": "test-key"},
        )
        assert collect.exit_code == 0
        assert "MKT1: 1 new article(s)" in collect.stdout
        assert exa_route.call_count == 2

        conn = sqlite3.connect(str(db_path))
        try:
            tracked_count = conn.execute("SELECT COUNT(*) FROM tracked_items").fetchone()[0]
            assert tracked_count == 1

            article_count = conn.execute("SELECT COUNT(*) FROM news_articles").fetchone()[0]
            assert article_count == 1

            link_count = conn.execute("SELECT COUNT(*) FROM news_article_markets").fetchone()[0]
            assert link_count == 1

            sentiment_count = conn.execute("SELECT COUNT(*) FROM news_sentiments").fetchone()[0]
            assert sentiment_count == 1
        finally:
            conn.close()
