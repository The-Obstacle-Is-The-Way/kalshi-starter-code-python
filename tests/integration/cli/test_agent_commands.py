from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import respx
from httpx import Response
from typer.testing import CliRunner

from kalshi_research.cli import app

pytestmark = [pytest.mark.integration]


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _market_dict(
    ticker: str,
    *,
    event_ticker: str = "EVT1",
    yes_bid: int = 49,
    yes_ask: int = 51,
    status: str = "active",
    volume_24h: int = 10_000,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    last_price = (yes_bid + yes_ask) // 2
    return {
        "ticker": ticker,
        "event_ticker": event_ticker,
        "series_ticker": "SERIES1",
        "title": f"Market {ticker}",
        "subtitle": "",
        "status": status,
        "result": "",
        "yes_bid": yes_bid,
        "yes_ask": yes_ask,
        "yes_bid_dollars": f"{yes_bid / 100:.4f}",
        "yes_ask_dollars": f"{yes_ask / 100:.4f}",
        "no_bid": 100 - yes_ask,
        "no_ask": 100 - yes_bid,
        "no_bid_dollars": f"{(100 - yes_ask) / 100:.4f}",
        "no_ask_dollars": f"{(100 - yes_bid) / 100:.4f}",
        "last_price": last_price,
        "last_price_dollars": f"{last_price / 100:.4f}",
        "volume": 1_000,
        "volume_24h": volume_24h,
        "open_interest": 100,
        "liquidity": 1_000,
        "open_time": "2024-01-01T00:00:00Z",
        "close_time": (now + timedelta(days=30)).isoformat().replace("+00:00", "Z"),
        "expiration_time": (now + timedelta(days=31)).isoformat().replace("+00:00", "Z"),
    }


def _orderbook_dict(
    *, yes_bid: int = 49, yes_qty: int = 10, no_bid: int = 51, no_qty: int = 10
) -> dict[str, Any]:
    return {
        "orderbook": {
            "yes": [[yes_bid, yes_qty]],
            "no": [[no_bid, no_qty]],
            "yes_dollars": [[f"{yes_bid / 100:.4f}", yes_qty]],
            "no_dollars": [[f"{no_bid / 100:.4f}", no_qty]],
        }
    }


def _exa_search_response() -> dict[str, Any]:
    return {
        "requestId": "req-1",
        "results": [
            {
                "id": "r1",
                "url": "https://example.com/article",
                "title": "Example",
                "publishedDate": "2026-01-01T00:00:00Z",
            }
        ],
        "costDollars": {"total": 0.01},
    }


@respx.mock
def test_agent_research_invalid_ticker_exits_2(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """404 errors exit with code 2 (not found convention)."""
    with runner.isolated_filesystem():
        monkeypatch.setenv("EXA_API_KEY", "test-key")
        ticker = "BADTICKER"

        respx.get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}").mock(
            return_value=Response(404, text="Not found")
        )

        result = runner.invoke(app, ["agent", "research", ticker, "--mode", "fast", "--json"])
        assert result.exit_code == 2  # 404 uses exit code 2 per CLI convention
        assert "API Error 404" in result.stdout


@respx.mock
def test_agent_research_happy_path_json(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    with runner.isolated_filesystem():
        monkeypatch.setenv("EXA_API_KEY", "test-key")
        ticker = "MKT1"

        respx.get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}").mock(
            return_value=Response(200, json={"market": _market_dict(ticker)})
        )
        respx.post("https://api.exa.ai/search").mock(
            return_value=Response(200, json=_exa_search_response())
        )

        result = runner.invoke(app, ["agent", "research", ticker, "--mode", "fast", "--json"])
        assert result.exit_code == 0

        payload = json.loads(result.stdout)
        assert payload["ticker"] == ticker
        assert payload["mode"] == "fast"
        assert payload["total_cost_usd"] > 0
        assert len(payload["factors"]) > 0


@respx.mock
def test_agent_analyze_invalid_ticker_exits_2(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """404 errors exit with code 2 (not found convention)."""
    with runner.isolated_filesystem():
        monkeypatch.setenv("EXA_API_KEY", "test-key")
        monkeypatch.setenv("KALSHI_SYNTHESIZER_BACKEND", "mock")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ticker = "BADTICKER"

        respx.get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}").mock(
            return_value=Response(404, text="Not found")
        )

        result = runner.invoke(app, ["agent", "analyze", ticker, "--mode", "fast"])
        assert result.exit_code == 2  # 404 uses exit code 2 per CLI convention
        assert "API Error 404" in result.stdout


@respx.mock
def test_agent_analyze_happy_path_json(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    with runner.isolated_filesystem():
        monkeypatch.setenv("EXA_API_KEY", "test-key")
        monkeypatch.setenv("KALSHI_SYNTHESIZER_BACKEND", "mock")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        ticker = "MKT1"

        respx.get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}").mock(
            return_value=Response(200, json={"market": _market_dict(ticker)})
        )
        respx.get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}/orderbook").mock(
            return_value=Response(200, json=_orderbook_dict())
        )
        respx.post("https://api.exa.ai/search").mock(
            return_value=Response(200, json=_exa_search_response())
        )

        result = runner.invoke(app, ["agent", "analyze", ticker, "--mode", "fast"])
        assert result.exit_code == 0

        payload = json.loads(result.stdout)
        assert payload["analysis"]["ticker"] == ticker
        assert payload["research"]["mode"] == "fast"
        assert payload["verification"]["passed"] is True
