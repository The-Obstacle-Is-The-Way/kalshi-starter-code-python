# SPEC-014: WebSocket Real-Time Data Integration

**Status:** ✅ Implemented
**Priority:** P0 (Critical Performance Optimization)
**Estimated Complexity:** High
**Dependencies:** SPEC-002 (API Client)
**Official Docs:** [WebSocket Connection](https://docs.kalshi.com/websockets/websocket-connection)
**Local SSOT:** [OFFICIAL-API-REFERENCE.md](../kalshi/OFFICIAL-API-REFERENCE.md)

---

## 1. Problem Statement

### Current Issue
The market scanner (`kalshi scan movers`, `kalshi scan opportunities`) is **extremely slow** because it:
1. Polls `/markets` REST endpoint repeatedly
2. Iterates through 3000+ markets via pagination
3. Each page requires a separate HTTP request
4. Subject to rate limits (20 reads/sec on Basic tier)

**Result:** Scanner takes 2-5+ minutes to complete, often timing out.

### Root Cause
SPEC-002 explicitly listed WebSocket as a "Non-Goal":
> "WebSocket streaming (keep existing, enhance later)"

This was a mistake. The **official Kalshi documentation** recommends WebSocket for:
- Real-time orderbook updates
- Price/volume/open interest changes (via `ticker` channel)
- Trade notifications
- Market lifecycle events

---

## 2. Solution: WebSocket Channels

### 2.1 Available Channels (Official API)

> **IMPORTANT:** ALL WebSocket connections require authentication via headers, even for public data channels.
> See [OFFICIAL-API-REFERENCE.md](../kalshi/OFFICIAL-API-REFERENCE.md) for auth details.

| Channel | Data Scope | Use Case |
|---------|------------|----------|
| `orderbook_delta` | Public | Real-time orderbook changes (requires market filter) |
| `ticker` | Public | Price, volume, open interest updates |
| `trade` | Public | Public trade notifications |
| `market_lifecycle_v2` | Public | Market state changes, event creation |
| `multivariate` | Public | Multivariate collection notifications |
| `fill` | Private | Your order fills (market filter ignored) |
| `market_positions` | Private | Portfolio position updates |
| `communications` | Private | RFQ and quote notifications |

### 2.2 Key Benefits

1. **No Polling**: Single persistent connection instead of 100+ HTTP requests
2. **Real-Time**: Updates pushed immediately vs. periodic polling
3. **Efficient**: Only receive changes, not entire market list
4. **Rate Limit Friendly**: WebSocket doesn't count against REST rate limits

### 2.3 Connection Details

- **Keep-Alive**: Kalshi sends Ping frames every 10 seconds with body `heartbeat`
- **Response Required**: Clients must respond with Pong frames
- **Filtering**: Can subscribe to specific markets or all markets

---

## 3. Technical Specification

### 3.1 Module Structure

```
src/kalshi_research/
├── api/
│   ├── websocket/
│   │   ├── __init__.py
│   │   ├── client.py        # WebSocket client
│   │   ├── channels.py      # Channel subscription handlers
│   │   ├── messages.py      # Message models
│   │   └── reconnect.py     # Auto-reconnection logic
```

### 3.2 WebSocket Client

```python
# src/kalshi_research/api/websocket/client.py
import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

import websockets
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()


class KalshiWebSocket:
    """
    WebSocket client for real-time Kalshi market data.

    Usage:
        async with KalshiWebSocket() as ws:
            await ws.subscribe_ticker(on_update=handle_price_update)
            await ws.subscribe_orderbook_delta(
                market_tickers=["KXBTC-25JAN-T100000"],
                on_update=handle_orderbook,
            )
            await ws.run_forever()
    """

    WS_URL = "wss://api.elections.kalshi.com/trade-api/ws/v2"
    DEMO_WS_URL = "wss://demo-api.kalshi.co/trade-api/ws/v2"

    def __init__(
        self,
        environment: str = "prod",
        auth_token: str | None = None,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 10,
    ) -> None:
        self._url = self.DEMO_WS_URL if environment == "demo" else self.WS_URL
        self._auth_token = auth_token
        self._auto_reconnect = auto_reconnect
        self._max_reconnect = max_reconnect_attempts
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._handlers: dict[str, Callable[[dict[str, Any]], Coroutine[Any, Any, None]]] = {}
        self._running = False

    async def __aenter__(self) -> "KalshiWebSocket":
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def connect(self) -> None:
        """Establish WebSocket connection."""
        self._ws = await websockets.connect(self._url)
        self._running = True
        logger.info("WebSocket connected", url=self._url)

        # Start heartbeat handler
        asyncio.create_task(self._heartbeat_handler())

    async def close(self) -> None:
        """Close WebSocket connection."""
        self._running = False
        if self._ws:
            await self._ws.close()
            logger.info("WebSocket closed")

    async def _heartbeat_handler(self) -> None:
        """Handle ping/pong heartbeat frames."""
        while self._running and self._ws:
            try:
                # websockets library handles ping/pong automatically
                # but we can monitor connection health here
                await asyncio.sleep(15)
                if self._ws.closed:
                    logger.warning("WebSocket connection lost")
                    if self._auto_reconnect:
                        await self._reconnect()
            except Exception as e:
                logger.error("Heartbeat error", error=str(e))

    async def _reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        for attempt in range(self._max_reconnect):
            try:
                wait_time = min(2 ** attempt, 60)
                logger.info("Reconnecting", attempt=attempt + 1, wait=wait_time)
                await asyncio.sleep(wait_time)
                await self.connect()
                # Resubscribe to channels
                await self._resubscribe()
                return
            except Exception as e:
                logger.error("Reconnect failed", error=str(e))
        raise ConnectionError("Max reconnect attempts exceeded")

    async def subscribe_ticker(
        self,
        on_update: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
        market_tickers: list[str] | None = None,
    ) -> None:
        """
        Subscribe to ticker channel for price/volume/OI updates.

        Args:
            on_update: Async callback for updates
            market_tickers: Optional list of specific markets (None = all)
        """
        msg = {"cmd": "subscribe", "params": {"channels": ["ticker"]}}
        if market_tickers:
            msg["params"]["market_tickers"] = market_tickers

        await self._send(msg)
        self._handlers["ticker"] = on_update

    async def subscribe_orderbook_delta(
        self,
        on_update: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
        market_tickers: list[str] | None = None,
    ) -> None:
        """Subscribe to orderbook delta channel."""
        msg = {"cmd": "subscribe", "params": {"channels": ["orderbook_delta"]}}
        if market_tickers:
            msg["params"]["market_tickers"] = market_tickers

        await self._send(msg)
        self._handlers["orderbook_delta"] = on_update

    async def subscribe_trades(
        self,
        on_update: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
        market_tickers: list[str] | None = None,
    ) -> None:
        """Subscribe to public trade notifications."""
        msg = {"cmd": "subscribe", "params": {"channels": ["trade"]}}
        if market_tickers:
            msg["params"]["market_tickers"] = market_tickers

        await self._send(msg)
        self._handlers["trade"] = on_update

    async def subscribe_market_lifecycle(
        self,
        on_update: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        """Subscribe to market state change notifications."""
        msg = {"cmd": "subscribe", "params": {"channels": ["market_lifecycle_v2"]}}
        await self._send(msg)
        self._handlers["market_lifecycle_v2"] = on_update

    async def _send(self, msg: dict[str, Any]) -> None:
        """Send message over WebSocket."""
        if not self._ws:
            raise ConnectionError("WebSocket not connected")
        import json
        await self._ws.send(json.dumps(msg))

    async def run_forever(self) -> None:
        """Process incoming messages until stopped."""
        import json

        if not self._ws:
            raise ConnectionError("WebSocket not connected")

        async for message in self._ws:
            try:
                data = json.loads(message)
                channel = data.get("type") or data.get("channel")

                if channel in self._handlers:
                    await self._handlers[channel](data)
                else:
                    logger.debug("Unhandled message", type=channel)
            except Exception as e:
                logger.error("Message handling error", error=str(e))

    async def _resubscribe(self) -> None:
        """Resubscribe to all channels after reconnect."""
        # Implementation would re-send subscription messages
        pass
```

### 3.3 Price Unit Conversion

**CRITICAL:** WebSocket price units vary by channel!

| Channel/Field | Unit | Example | To Dollars |
|---------------|------|---------|------------|
| `ticker.price`, `ticker.yes_bid` | **Cents** | `48` | ÷ 100 = $0.48 |
| `ticker.price_dollars` | **Dollars (string)** | `"0.480"` | Direct use |
| `orderbook_delta.price` | **Cents** | `96` | ÷ 100 = $0.96 |
| `market_positions.position_cost` | **Centi-cents** | `500000` | ÷ 10,000 = $50.00 |
| `market_positions.realized_pnl` | **Centi-cents** | `100000` | ÷ 10,000 = $10.00 |
| `market_positions.fees_paid` | **Centi-cents** | `10000` | ÷ 10,000 = $1.00 |

```python
# src/kalshi_research/api/websocket/messages.py
from decimal import Decimal
from pydantic import BaseModel


class TickerUpdate(BaseModel):
    """Ticker channel update message. Prices in CENTS (0-100)."""

    market_ticker: str
    price: int  # cents (0-100)
    yes_bid: int  # cents
    yes_ask: int  # cents
    price_dollars: str  # dollar string "0.480"
    yes_bid_dollars: str
    no_bid_dollars: str
    volume: int
    open_interest: int

    @property
    def price_as_dollars(self) -> Decimal:
        """Convert cents to dollars."""
        return Decimal(self.price) / Decimal(100)


class MarketPositionUpdate(BaseModel):
    """Market positions channel update. Monetary values in CENTI-CENTS."""

    market_ticker: str
    position: int  # contract count
    position_cost: int  # centi-cents
    realized_pnl: int  # centi-cents
    fees_paid: int  # centi-cents

    @property
    def position_cost_dollars(self) -> Decimal:
        """Convert centi-cents to dollars (÷10,000)."""
        return Decimal(self.position_cost) / Decimal(10000)

    @property
    def realized_pnl_dollars(self) -> Decimal:
        """Convert centi-cents to dollars (÷10,000)."""
        return Decimal(self.realized_pnl) / Decimal(10000)
```

---

## 4. Scanner Optimization

### 4.1 Before (Current - Slow)

```python
# Current implementation - SLOW
async def scan_movers(client: KalshiPublicClient, top: int) -> list[Market]:
    # Fetches ALL markets via REST pagination (100+ requests)
    markets = []
    async for market in client.get_all_markets(status="open"):
        markets.append(market)  # 3000+ iterations

    # Then filters in memory
    return sorted(markets, key=lambda m: m.volume_24h, reverse=True)[:top]
```

### 4.2 After (WebSocket - Fast)

```python
# New implementation - FAST
class MarketTracker:
    """Track market prices via WebSocket for instant queries."""

    def __init__(self) -> None:
        self._markets: dict[str, TickerUpdate] = {}

    async def handle_ticker_update(self, data: dict[str, Any]) -> None:
        """Update local cache from WebSocket message."""
        update = TickerUpdate.model_validate(data)
        self._markets[update.market_ticker] = update

    def get_top_movers(self, top: int = 10) -> list[TickerUpdate]:
        """Instant query - no API calls needed."""
        return sorted(
            self._markets.values(),
            key=lambda m: m.volume,
            reverse=True,
        )[:top]


async def run_scanner() -> None:
    tracker = MarketTracker()

    async with KalshiWebSocket() as ws:
        await ws.subscribe_ticker(on_update=tracker.handle_ticker_update)

        # Initial sync via REST (one-time)
        async with KalshiPublicClient() as client:
            async for market in client.get_all_markets(status="open"):
                # Seed initial state
                pass

        # Then WebSocket keeps it updated
        await ws.run_forever()
```

---

## 5. Implementation Tasks

### 5.1 Phase 1: WebSocket Client
- [ ] Create `KalshiWebSocket` class with connection management
- [ ] Implement heartbeat handling (ping/pong)
- [ ] Add auto-reconnection with exponential backoff
- [ ] Write unit tests with mock WebSocket server

### 5.2 Phase 2: Channel Handlers
- [ ] Implement `ticker` channel subscription
- [ ] Implement `orderbook_delta` channel subscription
- [ ] Implement `trade` channel subscription
- [ ] Implement `market_lifecycle_v2` channel subscription
- [ ] Handle centi-cents → cents conversion

### 5.3 Phase 3: Scanner Integration
- [ ] Create `MarketTracker` for in-memory state
- [ ] Modify `kalshi scan movers` to use WebSocket
- [ ] Modify `kalshi scan opportunities` to use WebSocket
- [ ] Add `--live` flag for continuous scanning

### 5.4 Phase 4: Data Layer Integration
- [ ] Stream price updates to SQLite via WebSocket
- [ ] Add `kalshi data stream` command for continuous collection
- [ ] Implement deduplication for rapid updates

---

## 6. Acceptance Criteria

1. **Speed**: Scanner completes in <5 seconds (vs. 2-5 minutes currently)
2. **Real-Time**: Updates received within 1 second of market change
3. **Reliability**: Auto-reconnects on connection loss
4. **Efficiency**: Uses single WebSocket connection for all channels
5. **Compatibility**: Works alongside existing REST client

---

## 7. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| WebSocket connection drops | Auto-reconnect with exponential backoff |
| Message ordering issues | Use sequence numbers if available |
| Memory growth | Cap in-memory cache size, evict stale markets |
| Initial sync latency | Parallel REST fetch + WebSocket subscription |

---

## 8. References

- **Official WebSocket docs:** https://docs.kalshi.com/websockets/websocket-connection
- **Quick Start:** https://docs.kalshi.com/getting_started/quick_start_websockets
- **Ticker channel:** https://docs.kalshi.com/websockets/market-ticker
- **Orderbook updates:** https://docs.kalshi.com/websockets/orderbook-updates
- **Market positions:** https://docs.kalshi.com/websockets/market-positions
- **Production URL:** `wss://api.elections.kalshi.com/trade-api/ws/v2`
- **Demo URL:** `wss://demo-api.kalshi.co/trade-api/ws/v2`
- **Local SSOT:** [OFFICIAL-API-REFERENCE.md](../kalshi/OFFICIAL-API-REFERENCE.md)

### Channels
`orderbook_delta`, `ticker`, `trade`, `fill`, `market_positions`, `market_lifecycle_v2`, `multivariate`, `communications`

### Keep-Alive
Kalshi sends Ping frames (0x9) every ~10 seconds with body `heartbeat`. Respond with Pong frames (0xA).
