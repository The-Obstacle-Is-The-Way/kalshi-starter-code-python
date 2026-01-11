"""WebSocket client for Kalshi API."""

# RESERVED: Real-time streaming is not yet exposed via the CLI.
# See docs/_debt/DEBT-009-finish-halfway-implementations.md (WebSocket Real-time Data).

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

import structlog
import websockets
from websockets.protocol import State

from kalshi_research.api.auth import KalshiAuth

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from types import TracebackType

    from websockets.asyncio.client import ClientConnection

from kalshi_research.api.config import APIConfig, Environment, get_config
from kalshi_research.api.websocket.messages import (
    MarketPositionUpdate,
    OrderbookDelta,
    TickerUpdate,
    TradeUpdate,
)

logger = structlog.get_logger()


class KalshiWebSocket:
    """
    WebSocket client for real-time Kalshi market data.
    """

    WS_PATH = "/trade-api/ws/v2"

    def __init__(
        self,
        key_id: str,
        private_key_path: str | None = None,
        private_key_b64: str | None = None,
        environment: str | None = None,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 10,
    ) -> None:
        config = get_config()
        if environment:
            config = APIConfig(environment=Environment(environment))

        self._url = config.websocket_url
        self._auth = KalshiAuth(
            key_id, private_key_path=private_key_path, private_key_b64=private_key_b64
        )
        self._auto_reconnect = auto_reconnect
        self._max_reconnect = max_reconnect_attempts

        self._ws: ClientConnection | None = None
        self._running = False
        self._lock = asyncio.Lock()
        self._msg_id = 0  # Auto-incrementing message ID for commands

        # Handlers: channel -> callback
        self._handlers: dict[str, list[Callable[[Any], Coroutine[Any, Any, None]]]] = {}

        # Active subscriptions for resubscribe logic
        self._subscriptions: set[tuple[str, tuple[str, ...]]] = set()

    async def __aenter__(self) -> KalshiWebSocket:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def connect(self) -> None:
        """Establish WebSocket connection."""
        # Generate auth headers
        headers = self._auth.get_headers("GET", self.WS_PATH)

        logger.info("Connecting to WebSocket", url=self._url)
        self._ws = await websockets.connect(self._url, additional_headers=headers)
        self._running = True
        logger.info("WebSocket connected")

    async def close(self) -> None:
        """Close WebSocket connection."""
        self._running = False
        if self._ws:
            await self._ws.close()
            logger.info("WebSocket closed")

    async def _send(self, msg: dict[str, Any]) -> None:
        """Send message over WebSocket."""
        if not self._ws:
            raise ConnectionError("WebSocket not connected")
        await self._ws.send(json.dumps(msg))

    async def subscribe(
        self,
        channels: list[str],
        market_tickers: list[str] | None = None,
    ) -> None:
        """
        Subscribe to channels.

        Args:
            channels: List of channel names (ticker, orderbook_delta, etc)
            market_tickers: Optional list of market tickers
        """
        params: dict[str, Any] = {"channels": channels}
        if market_tickers:
            params["market_tickers"] = market_tickers

        # Include required "id" field per Kalshi WebSocket API spec
        self._msg_id += 1
        msg: dict[str, Any] = {"id": self._msg_id, "cmd": "subscribe", "params": params}

        await self._send(msg)

        # Track for resubscribe
        tickers_tuple = tuple(sorted(market_tickers)) if market_tickers else ()
        for channel in channels:
            self._subscriptions.add((channel, tickers_tuple))

    async def subscribe_ticker(
        self,
        callback: Callable[[TickerUpdate], Coroutine[Any, Any, None]],
        market_tickers: list[str] | None = None,
    ) -> None:
        """Subscribe to ticker updates."""
        self._add_handler("ticker", callback)
        await self.subscribe(["ticker"], market_tickers)

    async def subscribe_orderbook(
        self,
        callback: Callable[[OrderbookDelta], Coroutine[Any, Any, None]],
        market_tickers: list[str] | None = None,
    ) -> None:
        """Subscribe to orderbook delta updates."""
        self._add_handler("orderbook_delta", callback)
        await self.subscribe(["orderbook_delta"], market_tickers)

    async def subscribe_trades(
        self,
        callback: Callable[[TradeUpdate], Coroutine[Any, Any, None]],
        market_tickers: list[str] | None = None,
    ) -> None:
        """Subscribe to trade updates."""
        self._add_handler("trade", callback)
        await self.subscribe(["trade"], market_tickers)

    async def subscribe_positions(
        self,
        callback: Callable[[MarketPositionUpdate], Coroutine[Any, Any, None]],
    ) -> None:
        """Subscribe to position updates (private channel)."""
        self._add_handler("market_positions", callback)
        await self.subscribe(["market_positions"])

    def _add_handler(
        self, channel: str, callback: Callable[[Any], Coroutine[Any, Any, None]]
    ) -> None:
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(callback)

    async def _check_connection(self) -> bool:
        """Check connection state and reconnect if needed. Returns True if connected."""
        if not self._ws or self._ws.state is State.CLOSED:
            if self._auto_reconnect:
                await self._reconnect()
                return True
            return False
        return True

    async def run_forever(self) -> None:
        """Process incoming messages loop."""
        if not self._ws:
            raise ConnectionError("WebSocket not connected")

        while self._running:
            try:
                if not await self._check_connection():
                    break

                async for message in self._ws:
                    await self._handle_message(message)

                # Iterator exhausted - reconnect if enabled.
                logger.warning("WebSocket iterator exhausted")
                if self._running and self._auto_reconnect:
                    await self._reconnect()
                else:
                    break

            except websockets.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                if self._auto_reconnect:
                    await self._reconnect()
                else:
                    break
            except Exception:
                logger.exception("WebSocket error")
                if not self._running:
                    break
                await asyncio.sleep(1)

    async def _handle_message(self, raw_message: str | bytes) -> None:
        """Parse and route message."""
        try:
            data = json.loads(raw_message)
            # Kalshi WebSocket messages use "type" field per official docs
            # See: https://docs.kalshi.com/websockets/
            channel = data.get("type")

            # Skip non-data messages (subscription confirmations, etc)

            if not channel or channel not in self._handlers:
                return

            msg_obj: Any = None
            # Message payload is in the "msg" field per Kalshi WebSocket API spec
            payload = data.get("msg")
            if not payload:
                # Some system messages might differ
                return

            if channel == "ticker":
                msg_obj = TickerUpdate.model_validate(payload)
            elif channel == "orderbook_delta":
                msg_obj = OrderbookDelta.model_validate(payload)
            elif channel == "trade":
                msg_obj = TradeUpdate.model_validate(payload)
            elif channel == "market_positions":
                msg_obj = MarketPositionUpdate.model_validate(payload)

            if msg_obj:
                for handler in self._handlers[channel]:
                    try:
                        await handler(msg_obj)
                    except Exception as e:
                        logger.exception(f"Handler error: {e}")

        except json.JSONDecodeError:
            message_type = type(raw_message).__name__
            message_len = len(raw_message)
            logger.debug(
                "Received non-JSON WebSocket message",
                type=message_type,
                length=message_len,
            )
        except Exception:
            logger.exception("Message parsing error")

    async def _reconnect(self) -> None:
        """Attempt to reconnect."""
        logger.info("Attempting to reconnect...")
        for attempt in range(self._max_reconnect):
            try:
                wait_time = min(2**attempt, 60)
                await asyncio.sleep(wait_time)
                await self.connect()
                await self._resubscribe()
                return
            except Exception as e:
                logger.error(f"Reconnect attempt {attempt + 1} failed: {e}")

        self._running = False
        raise ConnectionError("Max reconnect attempts exceeded")

    async def _resubscribe(self) -> None:
        """Resubscribe to all active channels."""
        for channel, tickers_tuple in self._subscriptions:
            tickers = list(tickers_tuple) if tickers_tuple else None
            await self.subscribe([channel], tickers)
