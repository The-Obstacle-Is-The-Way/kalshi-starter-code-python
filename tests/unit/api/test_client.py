"""
API client tests - mock ONLY at HTTP boundary.

These tests use respx to mock HTTP requests. Everything else
(models, parsing, error handling) uses REAL implementations.
"""

from __future__ import annotations

from typing import Any

import pytest
import respx
from httpx import Response

from kalshi_research.api.client import KalshiPublicClient
from kalshi_research.api.exceptions import KalshiAPIError
from kalshi_research.api.models.market import Market, MarketStatus


@pytest.fixture
def mock_market_response() -> dict[str, Any]:
    """Mock market response matching real API structure."""
    return {
        "market": {
            "ticker": "KXBTC-25JAN-T100000",
            "event_ticker": "KXBTC-25JAN",
            "title": "Bitcoin above $100,000?",
            "subtitle": "On January 25, 2025",
            "status": "active",
            "result": "",
            "yes_bid": 45,
            "yes_ask": 47,
            "no_bid": 53,
            "no_ask": 55,
            "last_price": 46,
            "volume": 125000,
            "volume_24h": 5000,
            "open_interest": 50000,
            "liquidity": 10000,
            "open_time": "2024-01-01T00:00:00Z",
            "close_time": "2025-01-25T00:00:00Z",
            "expiration_time": "2025-01-26T00:00:00Z",
        }
    }


class TestKalshiPublicClient:
    """Tests for KalshiPublicClient."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_market_success(self, mock_market_response: dict[str, Any]) -> None:
        """Test successful market fetch."""
        ticker = "KXBTC-25JAN-T100000"
        respx.get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}").mock(
            return_value=Response(200, json=mock_market_response)
        )

        async with KalshiPublicClient() as client:
            market = await client.get_market(ticker)

        assert market.ticker == ticker
        assert market.status == MarketStatus.ACTIVE
        assert market.yes_bid == 45

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_market_not_found(self) -> None:
        """Test 404 handling."""
        ticker = "NONEXISTENT"
        respx.get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}").mock(
            return_value=Response(404, json={"error": "Market not found"})
        )

        async with KalshiPublicClient() as client:
            with pytest.raises(KalshiAPIError) as exc_info:
                await client.get_market(ticker)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @respx.mock
    async def test_rate_limit_retry(self, mock_market_response: dict[str, Any]) -> None:
        """Test that 429 triggers retry."""
        ticker = "KXBTC-25JAN-T100000"
        route = respx.get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}")

        # First call returns 429, second succeeds
        route.side_effect = [
            Response(429, json={"error": "Rate limited"}),
            Response(200, json=mock_market_response),
        ]

        async with KalshiPublicClient() as client:
            market = await client.get_market(ticker)

        assert market.ticker == ticker
        assert route.call_count == 2  # Verify retry happened

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_markets_pagination(self) -> None:
        """Test pagination through multiple pages."""
        base_market = {
            "event_ticker": "EVT",
            "title": "Market",
            "subtitle": "",
            "status": "active",
            "result": "",
            "yes_bid": 50,
            "yes_ask": 52,
            "no_bid": 48,
            "no_ask": 50,
            "last_price": 51,
            "volume": 1000,
            "volume_24h": 100,
            "open_interest": 500,
            "liquidity": 1000,
            "open_time": "2024-01-01T00:00:00Z",
            "close_time": "2025-01-01T00:00:00Z",
            "expiration_time": "2025-01-02T00:00:00Z",
        }
        page1 = {
            "markets": [{**base_market, "ticker": f"MKT-{i}"} for i in range(3)],
            "cursor": "page2_cursor",
        }
        page2 = {
            "markets": [{**base_market, "ticker": f"MKT-{i + 3}"} for i in range(2)],
            "cursor": None,
        }

        route = respx.get("https://api.elections.kalshi.com/trade-api/v2/markets")
        route.side_effect = [
            Response(200, json=page1),
            Response(200, json=page2),
        ]

        async with KalshiPublicClient() as client:
            markets = [m async for m in client.get_all_markets()]

        assert len(markets) == 5
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_orderbook(self) -> None:
        """Test orderbook parsing with [[price, qty], ...] format."""
        ticker = "KXBTC-25JAN-T100000"
        respx.get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}/orderbook").mock(
            return_value=Response(
                200,
                json={
                    "orderbook": {
                        "yes": [[45, 100], [44, 200], [43, 500]],
                        "no": [[53, 150], [54, 250]],
                    }
                },
            )
        )

        async with KalshiPublicClient() as client:
            orderbook = await client.get_orderbook(ticker)

        assert orderbook.best_yes_bid == 45
        assert orderbook.best_no_bid == 54
        assert orderbook.spread == 100 - 45 - 54  # = 1 cent

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_trades(self) -> None:
        """Test trades endpoint parsing."""
        respx.get("https://api.elections.kalshi.com/trade-api/v2/markets/trades").mock(
            return_value=Response(
                200,
                json={
                    "trades": [
                        {
                            "trade_id": "trade123",
                            "ticker": "TEST-MKT",
                            "created_time": "2024-06-15T10:30:00Z",
                            "yes_price": 46,
                            "no_price": 54,
                            "count": 10,
                            "taker_side": "yes",
                        }
                    ]
                },
            )
        )

        async with KalshiPublicClient() as client:
            trades = await client.get_trades(ticker="TEST-MKT", limit=10)

        assert len(trades) == 1
        assert trades[0].trade_id == "trade123"
        assert trades[0].yes_price == 46

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_candlesticks_batch(self) -> None:
        """Test batch candlesticks endpoint."""
        respx.get("https://api.elections.kalshi.com/trade-api/v2/markets/candlesticks").mock(
            return_value=Response(
                200,
                json={
                    "markets": [
                        {
                            "market_ticker": "KXBTC-25JAN-T100000",
                            "candlesticks": [
                                {
                                    "end_period_ts": 1700003600,
                                    "open_interest": 123,
                                    "volume": 1000,
                                    "price": {"open": 45, "high": 48, "low": 44, "close": 47},
                                    "yes_bid": {"open": 44, "high": 45, "low": 43, "close": 44},
                                    "yes_ask": {"open": 46, "high": 47, "low": 45, "close": 46},
                                },
                            ],
                        }
                    ]
                },
            )
        )

        async with KalshiPublicClient() as client:
            responses = await client.get_candlesticks(
                market_tickers=["KXBTC-25JAN-T100000"],
                start_ts=1700000000,
                end_ts=1700100000,
            )

        assert len(responses) == 1
        assert responses[0].market_ticker == "KXBTC-25JAN-T100000"
        assert len(responses[0].candlesticks) == 1
        assert responses[0].candlesticks[0].end_period_ts == 1700003600
        assert responses[0].candlesticks[0].price.close == 47

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_exchange_status(self) -> None:
        """Test exchange status endpoint."""
        respx.get("https://api.elections.kalshi.com/trade-api/v2/exchange/status").mock(
            return_value=Response(200, json={"exchange_active": True, "trading_active": True})
        )

        async with KalshiPublicClient() as client:
            status = await client.get_exchange_status()

        assert status["exchange_active"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_events(self) -> None:
        """Test events endpoint."""
        respx.get("https://api.elections.kalshi.com/trade-api/v2/events").mock(
            return_value=Response(
                200,
                json={
                    "events": [
                        {
                            "event_ticker": "KXBTC-25JAN",
                            "series_ticker": "KXBTC",
                            "title": "Bitcoin Price",
                            "sub_title": "January 2025",
                            "category": "Crypto",
                        }
                    ]
                },
            )
        )

        async with KalshiPublicClient() as client:
            events = await client.get_events()

        assert len(events) == 1
        assert events[0].event_ticker == "KXBTC-25JAN"


class TestMarketModelValidation:
    """Test Market model validation with real API-like data."""

    def test_market_parses_all_required_fields(self, mock_market_response: dict[str, Any]) -> None:
        """Market model correctly parses all required fields."""
        market = Market.model_validate(mock_market_response["market"])

        assert market.ticker == "KXBTC-25JAN-T100000"
        assert market.event_ticker == "KXBTC-25JAN"
        assert market.title == "Bitcoin above $100,000?"
        assert market.status == MarketStatus.ACTIVE
        assert market.yes_bid == 45
        assert market.yes_ask == 47
        assert market.volume == 125000

    def test_market_optional_fields(self) -> None:
        """Market handles optional/missing fields."""
        minimal_data = {
            "ticker": "TEST",
            "event_ticker": "EVT",
            "title": "Test Market",
            "status": "active",
            "yes_bid": 50,
            "yes_ask": 50,
            "no_bid": 50,
            "no_ask": 50,
            "volume": 0,
            "volume_24h": 0,
            "open_interest": 0,
            "liquidity": 0,
            "open_time": "2024-01-01T00:00:00Z",
            "close_time": "2025-01-01T00:00:00Z",
            "expiration_time": "2025-01-02T00:00:00Z",
        }
        market = Market.model_validate(minimal_data)

        assert market.subtitle == ""  # Default value
        assert market.result == ""  # Default value
        assert market.last_price is None  # Optional field
        assert market.series_ticker is None  # Optional field
