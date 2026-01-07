from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest
import respx
from httpx import Response
from typer.testing import CliRunner

from kalshi_research.cli import app

pytestmark = [pytest.mark.e2e, pytest.mark.integration, pytest.mark.slow]


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
        "yes_bid": 49,
        "yes_ask": 51,
        "no_bid": 49,
        "no_ask": 51,
        "last_price": 50,
        "volume": 1_000,
        "volume_24h": 10_000,
        "open_interest": 100,
        "liquidity": 1_000,
        "open_time": "2024-01-01T00:00:00Z",
        "close_time": "2025-01-01T00:00:00Z",
        "expiration_time": "2025-01-02T00:00:00Z",
    }


@respx.mock
def test_full_data_pipeline_init_sync_snapshot_verify() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        db_path = Path("data/kalshi.db")

        respx.get("https://api.elections.kalshi.com/trade-api/v2/events").mock(
            return_value=Response(
                200,
                json={"events": [_event_dict()], "cursor": None, "milestones": []},
            )
        )
        respx.get("https://api.elections.kalshi.com/trade-api/v2/markets").mock(
            return_value=Response(
                200,
                json={"markets": [_market_dict("MKT1")], "cursor": None},
            )
        )

        init = runner.invoke(app, ["data", "init", "--db", str(db_path)])
        assert init.exit_code == 0

        sync = runner.invoke(app, ["data", "sync-markets", "--db", str(db_path)])
        assert sync.exit_code == 0

        snapshot = runner.invoke(
            app, ["data", "snapshot", "--db", str(db_path), "--status", "open"]
        )
        assert snapshot.exit_code == 0

        assert db_path.exists()
        with sqlite3.connect(db_path) as conn:
            events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            markets = conn.execute("SELECT COUNT(*) FROM markets").fetchone()[0]
            snaps = conn.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()[0]
            joined = conn.execute(
                "SELECT COUNT(*) FROM markets m JOIN events e ON m.event_ticker = e.ticker"
            ).fetchone()[0]

        assert events == 1
        assert markets == 1
        assert snaps == 1
        assert joined == 1
