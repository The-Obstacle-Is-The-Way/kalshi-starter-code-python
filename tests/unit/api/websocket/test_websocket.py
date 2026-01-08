"""Unit tests for WebSocket client."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from kalshi_research.api.websocket.client import KalshiWebSocket
from kalshi_research.api.websocket.messages import TickerUpdate


class MockWebSocket:
    def __init__(self):
        self.send = AsyncMock()
        self.close = AsyncMock()
        self.closed = False
        self._messages = []
        self._iter_idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._iter_idx < len(self._messages):
            msg = self._messages[self._iter_idx]
            self._iter_idx += 1
            return msg
        raise StopAsyncIteration

    def add_message(self, msg: dict):
        self._messages.append(json.dumps(msg))


@pytest.fixture
def mock_ws_connect():
    with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
        mock_ws = MockWebSocket()
        mock_connect.return_value = mock_ws
        yield mock_connect, mock_ws


@pytest.fixture
def mock_auth():
    with patch("kalshi_research.api.websocket.client.KalshiAuth") as MockAuth:
        instance = MockAuth.return_value
        instance.get_headers.return_value = {"Auth": "Token"}
        yield instance


@pytest.mark.asyncio
async def test_connect_headers(mock_ws_connect, mock_auth):
    """Test connection includes auth headers."""
    mock_connect, _ = mock_ws_connect

    client = KalshiWebSocket(key_id="test", private_key_b64="fake", environment="demo")
    await client.connect()

    mock_connect.assert_called_once()
    args, kwargs = mock_connect.call_args
    assert kwargs["extra_headers"] == {"Auth": "Token"}


@pytest.mark.asyncio
async def test_subscribe_ticker(mock_ws_connect, mock_auth):
    """Test ticker subscription sends correct JSON."""
    mock_connect, mock_ws = mock_ws_connect

    client = KalshiWebSocket(key_id="test", private_key_b64="fake", environment="demo")
    await client.connect()

    await client.subscribe_ticker(AsyncMock(), ["KXTEST"])

    mock_ws.send.assert_called_once()
    sent_msg = json.loads(mock_ws.send.call_args[0][0])

    assert sent_msg["cmd"] == "subscribe"
    assert sent_msg["params"]["channels"] == ["ticker"]
    assert sent_msg["params"]["market_tickers"] == ["KXTEST"]


@pytest.mark.asyncio
async def test_message_routing(mock_ws_connect, mock_auth):
    """Test message routing to callbacks."""
    mock_connect, mock_ws = mock_ws_connect

    # Prepare message
    ticker_msg = {
        "type": "ticker",
        "msg": {
            "market_ticker": "KXTEST",
            "price": 50,
            "yes_bid": 49,
            "yes_ask": 51,
            "volume": 100,
            "open_interest": 1000,
        },
    }
    mock_ws.add_message(ticker_msg)

    client = KalshiWebSocket(key_id="test", private_key_b64="fake", environment="demo")
    await client.connect()

    # Register handler
    callback = AsyncMock()
    await client.subscribe_ticker(callback, ["KXTEST"])

    # Run loop manually for one tick
    # Since run_forever is infinite, we can't await it directly without cancelling
    # But our mock iterator stops after 1 message, so it should exit the loop?
    # Wait, run_forever loop condition is `while self._running`.
    # And inside `async for message in self._ws`.
    # If iterator finishes, loop continues?
    # Logic:
    # async for message in self._ws: ...
    # if loop ends (StopAsyncIteration), we go back to while self._running.
    # We check if ws.closed. Our mock isn't closed.
    # So it will try to reconnect or loop.

    # Let's modify run_forever logic or test _handle_message directly.
    # Testing _handle_message directly is easier and safer for unit tests.

    await client._handle_message(json.dumps(ticker_msg))

    callback.assert_called_once()
    arg = callback.call_args[0][0]
    assert isinstance(arg, TickerUpdate)
    assert arg.price == 50
    assert arg.market_ticker == "KXTEST"
