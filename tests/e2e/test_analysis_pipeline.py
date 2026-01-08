from __future__ import annotations

import json
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


def _market_dict(
    ticker: str,
    *,
    event_ticker: str = "EVT1",
    yes_bid: int = 49,
    yes_ask: int = 51,
) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "event_ticker": event_ticker,
        "series_ticker": "SERIES1",
        "title": f"Market {ticker}",
        "subtitle": "",
        "status": "active",
        "result": "",
        "yes_bid": yes_bid,
        "yes_ask": yes_ask,
        "no_bid": 100 - yes_ask,
        "no_ask": 100 - yes_bid,
        "last_price": (yes_bid + yes_ask) // 2,
        "volume": 1_000,
        "volume_24h": 10_000,
        "open_interest": 100,
        "liquidity": 1_000,
        "open_time": "2024-01-01T00:00:00Z",
        "close_time": "2025-01-01T00:00:00Z",
        "expiration_time": "2025-01-02T00:00:00Z",
    }


@respx.mock
def test_sync_scan_alert_notify_pipeline() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        db_path = Path("data/kalshi.db")

        respx.get("https://api.elections.kalshi.com/trade-api/v2/events").mock(
            return_value=Response(
                200,
                json={"events": [_event_dict()], "cursor": None, "milestones": []},
            )
        )
        markets_route = respx.get("https://api.elections.kalshi.com/trade-api/v2/markets")
        markets_route.side_effect = [
            # data sync-markets
            Response(
                200,
                json={"markets": [_market_dict("MKT1"), _market_dict("MKT2")], "cursor": None},
            ),
            # scan opportunities
            Response(
                200,
                json={"markets": [_market_dict("MKT1"), _market_dict("MKT2")], "cursor": None},
            ),
            # alerts monitor (trigger)
            Response(
                200,
                json={"markets": [_market_dict("MKT1", yes_bid=70, yes_ask=72)], "cursor": None},
            ),
        ]

        init = runner.invoke(app, ["data", "init", "--db", str(db_path)])
        assert init.exit_code == 0

        sync = runner.invoke(
            app, ["data", "sync-markets", "--db", str(db_path), "--max-pages", "1"]
        )
        assert sync.exit_code == 0

        scan = runner.invoke(app, ["scan", "opportunities", "--top", "5", "--max-pages", "1"])
        assert scan.exit_code == 0

        add_alert = runner.invoke(app, ["alerts", "add", "price", "MKT1", "--above", "0.6"])
        assert add_alert.exit_code == 0

        stored = json.loads(Path("data/alerts.json").read_text())
        assert len(stored.get("conditions", [])) == 1

        monitor = runner.invoke(
            app, ["alerts", "monitor", "--once", "--interval", "1", "--max-pages", "1"]
        )
        assert monitor.exit_code == 0
        assert "alert(s) triggered" in monitor.stdout or "ALERT TRIGGERED" in monitor.stdout
