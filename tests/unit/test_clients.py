"""
Unit tests for clients module.

Tests the existing Kalshi client infrastructure.
Uses mocking ONLY at HTTP boundaries.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import rsa
from websockets.exceptions import ConnectionClosed
from websockets.frames import Close

from kalshi_research.clients import (
    Environment,
    KalshiBaseClient,
    KalshiHttpClient,
    KalshiWebSocketClient,
)


def generate_test_key() -> rsa.RSAPrivateKey:
    """Generate a test RSA key for testing."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class TestEnvironment:
    """Tests for Environment enum."""

    def test_environment_demo_value(self) -> None:
        """Test DEMO environment has correct value."""
        assert Environment.DEMO.value == "demo"

    def test_environment_prod_value(self) -> None:
        """Test PROD environment has correct value."""
        assert Environment.PROD.value == "prod"

    def test_environment_values_are_unique(self) -> None:
        """Test all environment values are unique."""
        values = [e.value for e in Environment]
        assert len(values) == len(set(values))


class TestMarketDataFactories:
    """Tests for test fixture factories - validate they create consistent data."""

    def test_make_market_default_values(self, make_market: Any) -> None:
        """Test make_market creates valid default market data."""
        market = cast("dict[str, Any]", make_market())

        assert market["ticker"] == "TEST-MARKET"
        assert market["status"] == "active"
        assert market["yes_bid"] == 45
        assert market["yes_ask"] == 47

    def test_make_market_price_consistency(self, make_market: Any) -> None:
        """Test yes/no prices are consistent (sum to 100)."""
        market = cast("dict[str, Any]", make_market(yes_bid=40, yes_ask=45))

        # no_bid = 100 - yes_ask, no_ask = 100 - yes_bid
        assert market["no_bid"] == 55  # 100 - 45
        assert market["no_ask"] == 60  # 100 - 40
        # Verify the math holds
        assert market["yes_bid"] + market["no_ask"] == 100
        assert market["yes_ask"] + market["no_bid"] == 100

    def test_make_market_custom_overrides(self, make_market: Any) -> None:
        """Test make_market accepts custom overrides."""
        market = cast("dict[str, Any]", make_market(ticker="CUSTOM-123", volume=50000))

        assert market["ticker"] == "CUSTOM-123"
        assert market["volume"] == 50000

    def test_make_orderbook_default_values(self, make_orderbook: Any) -> None:
        """Test make_orderbook creates valid default orderbook data."""
        orderbook = cast("dict[str, list[list[int]]]", make_orderbook())

        assert len(orderbook["yes"]) == 3
        assert len(orderbook["no"]) == 3
        # First element of yes should be best bid (price, qty)
        assert orderbook["yes"][0] == [45, 100]

    def test_make_orderbook_custom_bids(self, make_orderbook: Any) -> None:
        """Test make_orderbook accepts custom bids."""
        orderbook = cast(
            "dict[str, list[list[int]]]",
            make_orderbook(yes_bids=[(50, 200), (49, 300)]),
        )

        assert orderbook["yes"] == [[50, 200], [49, 300]]

    def test_make_trade_default_values(self, make_trade: Any) -> None:
        """Test make_trade creates valid default trade data."""
        trade = cast("dict[str, Any]", make_trade())

        assert trade["ticker"] == "TEST-MARKET"
        assert trade["yes_price"] == 46
        assert trade["no_price"] == 54  # 100 - 46
        assert trade["count"] == 10

    def test_make_trade_price_consistency(self, make_trade: Any) -> None:
        """Test yes_price + no_price = 100."""
        trade = cast("dict[str, Any]", make_trade(yes_price=75))

        assert trade["yes_price"] + trade["no_price"] == 100


class TestFixedClock:
    """Tests for the fixed clock fixture."""

    def test_fixed_clock_returns_same_time(self, fixed_clock: Any) -> None:
        """Test fixed_clock always returns the same time."""
        time1 = fixed_clock()
        time2 = fixed_clock()

        assert time1 == time2

    def test_fixed_clock_has_time_attribute(self, fixed_clock: Any) -> None:
        """Test fixed_clock.time gives direct access to the fixed time."""
        assert fixed_clock() == fixed_clock.time

    def test_fixed_clock_is_timezone_aware(self, fixed_clock: Any) -> None:
        """Test the fixed time is timezone-aware."""
        assert fixed_clock.time.tzinfo is not None


class TestSpreadCalculation:
    """Tests for spread calculation logic - pure math, no mocks needed."""

    @pytest.mark.parametrize(
        ("yes_bid", "yes_ask", "expected_spread"),
        [
            (45, 47, 2),
            (50, 50, 0),
            (10, 90, 80),
            (1, 99, 98),
        ],
    )
    def test_spread_calculation(self, yes_bid: int, yes_ask: int, expected_spread: int) -> None:
        """Test spread = yes_ask - yes_bid."""
        spread = yes_ask - yes_bid
        assert spread == expected_spread

    @pytest.mark.parametrize(
        ("yes_bid", "yes_ask", "expected_midpoint"),
        [
            (45, 47, 46),
            (50, 50, 50),
            (10, 90, 50),
        ],
    )
    def test_midpoint_calculation(self, yes_bid: int, yes_ask: int, expected_midpoint: int) -> None:
        """Test midpoint = (yes_bid + yes_ask) / 2."""
        midpoint = (yes_bid + yes_ask) // 2
        assert midpoint == expected_midpoint


class TestPriceConversions:
    """Tests for price to probability conversions - pure math."""

    @pytest.mark.parametrize(
        ("price", "expected_probability"),
        [
            (50, 0.50),
            (75, 0.75),
            (1, 0.01),
            (99, 0.99),
        ],
    )
    def test_price_to_probability(self, price: int, expected_probability: float) -> None:
        """Test conversion from Kalshi price (cents) to probability."""
        probability = price / 100
        assert probability == expected_probability

    @pytest.mark.parametrize("price", [1, 25, 50, 75, 99])
    def test_probability_is_in_valid_range(self, price: int) -> None:
        """Test all valid prices convert to probabilities in (0, 1)."""
        probability = price / 100
        assert 0 < probability < 1


class TestKalshiBaseClient:
    """Test KalshiBaseClient initialization and headers."""

    def test_demo_urls(self) -> None:
        """Demo environment uses correct URLs."""
        key = generate_test_key()
        client = KalshiBaseClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        assert "demo-api.kalshi.co" in client.HTTP_BASE_URL
        assert "demo-api.kalshi.co" in client.WS_BASE_URL

    def test_prod_urls(self) -> None:
        """Prod environment uses correct URLs."""
        key = generate_test_key()
        client = KalshiBaseClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.PROD,
        )

        assert "api.elections.kalshi.com" in client.HTTP_BASE_URL
        assert "api.elections.kalshi.com" in client.WS_BASE_URL

    def test_request_headers_structure(self) -> None:
        """Request headers have correct structure."""
        key = generate_test_key()
        client = KalshiBaseClient(
            key_id="test-key-123",
            private_key=key,
            environment=Environment.DEMO,
        )

        headers = client.request_headers("GET", "/trade-api/v2/markets")

        assert "KALSHI-ACCESS-KEY" in headers
        assert headers["KALSHI-ACCESS-KEY"] == "test-key-123"
        assert "KALSHI-ACCESS-SIGNATURE" in headers
        assert "KALSHI-ACCESS-TIMESTAMP" in headers
        assert headers["Content-Type"] == "application/json"

    def test_request_headers_strips_query_params(self) -> None:
        """Request headers path strips query params for signing."""
        key = generate_test_key()
        client = KalshiBaseClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        # Should not raise - query params are stripped for signing
        headers1 = client.request_headers("GET", "/api/markets")
        headers2 = client.request_headers("GET", "/api/markets?limit=10")

        assert headers1["KALSHI-ACCESS-KEY"] == headers2["KALSHI-ACCESS-KEY"]

    def test_sign_pss_text(self) -> None:
        """Can sign text with PSS."""
        key = generate_test_key()
        client = KalshiBaseClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        signature = client.sign_pss_text("test message")

        # Signature should be base64 encoded
        assert isinstance(signature, str)
        assert len(signature) > 0
        # Should be valid base64
        import base64

        base64.b64decode(signature)  # Should not raise

    def test_sign_pss_text_handles_invalid_signature(self) -> None:
        key = generate_test_key()
        client = KalshiBaseClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        client.private_key = MagicMock()
        client.private_key.sign.side_effect = InvalidSignature()

        with pytest.raises(ValueError, match="RSA sign PSS failed"):
            client.sign_pss_text("test message")

    def test_invalid_environment_raises(self) -> None:
        """Invalid environment raises ValueError."""
        key = generate_test_key()
        with pytest.raises(ValueError, match="Invalid environment"):
            KalshiBaseClient(
                key_id="test-key",
                private_key=key,
                environment=cast("Environment", "nope"),
            )


class TestKalshiHttpClient:
    """Test KalshiHttpClient initialization."""

    def test_inherits_base_client(self) -> None:
        """HttpClient inherits from BaseClient."""
        key = generate_test_key()
        client = KalshiHttpClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        assert isinstance(client, KalshiBaseClient)

    def test_has_endpoint_urls(self) -> None:
        """HttpClient has endpoint URL paths."""
        key = generate_test_key()
        client = KalshiHttpClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        assert client.exchange_url is not None
        assert client.markets_url is not None
        assert client.portfolio_url is not None
        assert "exchange" in client.exchange_url
        assert "markets" in client.markets_url
        assert "portfolio" in client.portfolio_url

    def test_host_matches_base_url(self) -> None:
        """Host attribute matches HTTP_BASE_URL."""
        key = generate_test_key()
        client = KalshiHttpClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        assert client.host == client.HTTP_BASE_URL

    def test_rate_limit_sleeps_when_called_too_fast(self) -> None:
        key = generate_test_key()
        client = KalshiHttpClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )
        client.last_api_call = datetime.now()

        with patch("kalshi_research.clients.time.sleep") as mock_sleep:
            client.rate_limit()

        mock_sleep.assert_called_once()

    def test_rate_limit_does_not_sleep_when_called_late(self) -> None:
        key = generate_test_key()
        client = KalshiHttpClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )
        client.last_api_call = datetime.now() - timedelta(seconds=1)

        with patch("kalshi_research.clients.time.sleep") as mock_sleep:
            client.rate_limit()

        mock_sleep.assert_not_called()

    def test_raise_if_bad_response_raises_http_error(self) -> None:
        key = generate_test_key()
        client = KalshiHttpClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        response = MagicMock(spec=requests.Response)
        response.status_code = 400
        response.raise_for_status.side_effect = requests.HTTPError("bad")

        with pytest.raises(requests.HTTPError):
            client.raise_if_bad_response(response)

    def test_raise_if_bad_response_noop_on_success(self) -> None:
        key = generate_test_key()
        client = KalshiHttpClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        response = MagicMock(spec=requests.Response)
        response.status_code = 200
        client.raise_if_bad_response(response)

        response.raise_for_status.assert_not_called()

    def test_http_methods_call_requests_and_return_json(self) -> None:
        key = generate_test_key()
        client = KalshiHttpClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        response = MagicMock(spec=requests.Response)
        response.status_code = 200
        response.json.return_value = {"ok": True}

        with (
            patch.object(client, "rate_limit"),
            patch.object(client, "request_headers", return_value={"X": "Y"}),
            patch.object(client, "raise_if_bad_response"),
            patch("kalshi_research.clients.requests.post", return_value=response) as mock_post,
            patch("kalshi_research.clients.requests.get", return_value=response) as mock_get,
            patch("kalshi_research.clients.requests.delete", return_value=response) as mock_delete,
        ):
            assert client.post("/path", {"a": 1}) == {"ok": True}
            assert client.get("/path", params={"q": "1"}) == {"ok": True}
            assert client.delete("/path") == {"ok": True}

        mock_post.assert_called_once()
        mock_get.assert_called_once()
        mock_delete.assert_called_once()

    def test_get_trades_filters_none_params(self) -> None:
        key = generate_test_key()
        client = KalshiHttpClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        with patch.object(client, "get", return_value={"trades": []}) as mock_get:
            client.get_trades(ticker="TICK", limit=10, cursor=None, max_ts=None, min_ts=None)

        mock_get.assert_called_once()
        (path,) = mock_get.call_args.args
        params = mock_get.call_args.kwargs["params"]
        assert path.endswith("/trades")
        assert params == {"ticker": "TICK", "limit": 10}

    def test_balance_and_exchange_status_call_get(self) -> None:
        key = generate_test_key()
        client = KalshiHttpClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        with patch.object(client, "get", return_value={"ok": True}) as mock_get:
            assert client.get_balance() == {"ok": True}
            assert client.get_exchange_status() == {"ok": True}

        assert mock_get.call_count == 2


class _AsyncCM:
    def __init__(self, value: object) -> None:
        self._value = value

    async def __aenter__(self) -> object:
        return self._value

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


class _FakeWS:
    def __init__(self, messages: list[str] | None = None, exc: Exception | None = None) -> None:
        self._messages = list(messages or [])
        self._exc = exc
        self.send = AsyncMock()

    def __aiter__(self) -> _FakeWS:
        return self

    async def __anext__(self) -> str:
        if self._exc is not None:
            raise self._exc
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)


class TestKalshiWebSocketClient:
    @pytest.mark.asyncio
    async def test_subscribe_sends_and_increments_message_id(self) -> None:
        key = generate_test_key()
        client = KalshiWebSocketClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )
        ws = _FakeWS()
        client.ws = ws

        assert client.message_id == 1
        await client.subscribe_to_tickers()
        assert client.message_id == 2
        ws.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_subscribe_without_ws_only_increments_message_id(self) -> None:
        key = generate_test_key()
        client = KalshiWebSocketClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        assert client.ws is None
        assert client.message_id == 1
        await client.subscribe_to_tickers()
        assert client.message_id == 2

    @pytest.mark.asyncio
    async def test_handler_no_ws_noops(self) -> None:
        key = generate_test_key()
        client = KalshiWebSocketClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )
        client.ws = None
        await client.handler()

    @pytest.mark.asyncio
    async def test_handler_calls_on_message(self) -> None:
        key = generate_test_key()
        client = KalshiWebSocketClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )
        ws = _FakeWS(messages=["m1", "m2"])
        client.ws = ws

        client.on_message = AsyncMock()
        await client.handler()

        assert client.on_message.await_count == 2

    @pytest.mark.asyncio
    async def test_handler_calls_on_close_on_connection_closed(self) -> None:
        key = generate_test_key()
        client = KalshiWebSocketClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        exc = ConnectionClosed(Close(1000, "bye"), Close(1000, "bye"), rcvd_then_sent=True)
        client.ws = _FakeWS(exc=exc)

        client.on_close = AsyncMock()
        await client.handler()
        client.on_close.assert_awaited_once_with(1000, "bye")

    @pytest.mark.asyncio
    async def test_handler_calls_on_error_on_unexpected_exception(self) -> None:
        key = generate_test_key()
        client = KalshiWebSocketClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        client.ws = _FakeWS(exc=RuntimeError("boom"))
        client.on_error = AsyncMock()
        await client.handler()

        client.on_error.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_on_open_calls_subscribe(self) -> None:
        key = generate_test_key()
        client = KalshiWebSocketClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        client.subscribe_to_tickers = AsyncMock()
        with patch("builtins.print"):
            await client.on_open()

        client.subscribe_to_tickers.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_on_message_and_error_and_close_print(self) -> None:
        key = generate_test_key()
        client = KalshiWebSocketClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        with patch("builtins.print") as mock_print:
            await client.on_message("hello")
            await client.on_error(RuntimeError("boom"))
            await client.on_close(1000, "bye")

        assert mock_print.call_count == 3

    @pytest.mark.asyncio
    async def test_connect_calls_websockets_connect(self) -> None:
        key = generate_test_key()
        client = KalshiWebSocketClient(
            key_id="test-key",
            private_key=key,
            environment=Environment.DEMO,
        )

        ws = _FakeWS()
        client.on_open = AsyncMock()
        client.handler = AsyncMock()

        with patch(
            "kalshi_research.clients.websockets.connect",
            return_value=_AsyncCM(ws),
        ) as mock_connect:
            await client.connect()

        mock_connect.assert_called_once()
        assert client.ws is ws
        client.on_open.assert_awaited_once()
        client.handler.assert_awaited_once()
