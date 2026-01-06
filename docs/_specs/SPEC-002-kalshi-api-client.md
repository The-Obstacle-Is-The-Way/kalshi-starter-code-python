# SPEC-002: Kalshi API Client Enhancement

**Status:** Draft
**Priority:** P0 (Required for any data fetching)
**Estimated Complexity:** High
**Dependencies:** SPEC-001 (Modern Python Foundation)

---

## 1. Overview

Extend the existing bare-bones Kalshi client to cover ALL public and authenticated API endpoints with proper error handling, retry logic, pagination support, and rate limiting.

### 1.1 Goals

- Implement ALL Kalshi API v2 endpoints
- Add unauthenticated client for public market data (no keys needed)
- Proper async support with httpx
- Robust error handling with custom exceptions
- Automatic pagination handling
- **Robust Rate Limiting:** Use `tenacity` for process-safe retries on 429 errors
- Full type safety with Pydantic models (using `Decimal` for money)

### 1.2 Non-Goals

- WebSocket streaming (keep existing, enhance later)
- Order execution automation (manual trading only)
- Real-time data pipelines

---

## 2. Kalshi API Endpoint Inventory

### 2.1 Public Endpoints (No Auth Required)

These are critical for research - we can fetch market data without API keys.

| Endpoint | Method | Description | Priority |
|----------|--------|-------------|----------|
| `/exchange/status` | GET | Exchange operational status | P0 |
| `/events` | GET | List all events | P0 |
| `/events/{event_ticker}` | GET | Single event details | P0 |
| `/series/{series_ticker}` | GET | Series information | P1 |
| `/markets` | GET | List all markets | P0 |
| `/markets/{ticker}` | GET | Single market details | P0 |
| `/markets/{ticker}/orderbook` | GET | Current orderbook | P0 |
| `/markets/trades` | GET | Public trade history | P0 |
| `/markets/{ticker}/candlesticks` | GET | OHLC price history (Verify path) | P0 |

### 2.2 Authenticated Endpoints (Trading/Portfolio)

| Endpoint | Method | Description | Priority |
|----------|--------|-------------|----------|
| `/portfolio/balance` | GET | Account balance | P1 |
| `/portfolio/positions` | GET | Current positions | P1 |
| `/portfolio/orders` | GET | Order history | P1 |
| `/portfolio/fills` | GET | Fill history | P1 |
| `/portfolio/settlements` | GET | Settlement history | P2 |
| `/portfolio/orders` | POST | Place order | P2 |
| `/portfolio/orders/{order_id}` | DELETE | Cancel order | P2 |
| `/portfolio/orders/batched` | POST | Batch orders | P3 |

---

## 3. Technical Specification

### 3.1 Module Structure

```
src/kalshi_research/
├── api/
│   ├── __init__.py
│   ├── client.py           # Main client classes
│   ├── endpoints/
│   │   ├── __init__.py
│   │   ├── markets.py      # Market-related endpoints
│   │   ├── events.py       # Event-related endpoints
│   │   ├── exchange.py     # Exchange status
│   │   └── portfolio.py    # Portfolio/trading endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   ├── market.py       # Market data models
│   │   ├── event.py        # Event data models
│   │   ├── orderbook.py    # Orderbook models
│   │   ├── trade.py        # Trade models
│   │   └── portfolio.py    # Portfolio models
│   ├── exceptions.py       # Custom exceptions
│   ├── auth.py             # Authentication logic
│   └── pagination.py       # Pagination helpers
```

### 3.2 Data Models (Pydantic)

```python
# src/kalshi_research/api/models/market.py
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MarketStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    SETTLED = "settled"


class MarketResult(str, Enum):
    YES = "yes"
    NO = "no"
    VOID = "void"
    UNDETERMINED = ""


class Market(BaseModel):
    """Represents a Kalshi prediction market."""

    ticker: str = Field(..., description="Unique market identifier")
    event_ticker: str = Field(..., description="Parent event ticker")
    series_ticker: str = Field(..., description="Parent series ticker")

    title: str = Field(..., description="Market question/title")
    subtitle: str = Field(default="", description="Additional context")

    status: MarketStatus
    result: Optional[MarketResult] = None

    # Pricing (in cents, 1-99)
    yes_bid: int = Field(..., ge=0, le=100, description="Best yes bid in cents")
    yes_ask: int = Field(..., ge=0, le=100, description="Best yes ask in cents")
    no_bid: int = Field(..., ge=0, le=100, description="Best no bid in cents")
    no_ask: int = Field(..., ge=0, le=100, description="Best no ask in cents")
    last_price: Optional[int] = Field(None, ge=0, le=100)

    # Volume
    volume: int = Field(..., ge=0, description="Total contracts traded")
    volume_24h: int = Field(..., ge=0, description="24h volume")
    open_interest: int = Field(..., ge=0, description="Open contracts")

    # Timestamps
    open_time: datetime
    close_time: datetime
    expiration_time: datetime

    # Liquidity
    liquidity: int = Field(..., ge=0, description="Dollar liquidity")

    class Config:
        frozen = True  # Immutable


class OrderbookLevel(BaseModel):
    """Single level in orderbook."""

    price: int = Field(..., ge=1, le=99, description="Price in cents")
    quantity: int = Field(..., ge=0, description="Contracts available")


class Orderbook(BaseModel):
    """Market orderbook snapshot."""

    ticker: str
    timestamp: datetime
    yes_bids: list[OrderbookLevel] = Field(default_factory=list)
    yes_asks: list[OrderbookLevel] = Field(default_factory=list)

    @property
    def spread(self) -> Optional[int]:
        """Calculate bid-ask spread in cents."""
        if not self.yes_bids or not self.yes_asks:
            return None
        best_bid = max(level.price for level in self.yes_bids)
        best_ask = min(level.price for level in self.yes_asks)
        return best_ask - best_bid

    @property
    def midpoint(self) -> Optional[Decimal]:
        """Calculate midpoint price."""
        if not self.yes_bids or not self.yes_asks:
            return None
        best_bid = max(level.price for level in self.yes_bids)
        best_ask = min(level.price for level in self.yes_asks)
        return (Decimal(best_bid) + Decimal(best_ask)) / 2


class Trade(BaseModel):
    """Public trade record."""

    trade_id: str
    ticker: str
    timestamp: datetime
    price: int = Field(..., ge=1, le=99)
    count: int = Field(..., ge=1, description="Number of contracts")
    taker_side: str  # "yes" or "no"


class Candlestick(BaseModel):
    """OHLC price data."""

    ticker: str
    period_start: datetime
    period_end: datetime
    open: int
    high: int
    low: int
    close: int
    volume: int
```

### 3.3 Client Architecture

```python
# src/kalshi_research/api/client.py
from typing import AsyncIterator, Optional
from decimal import Decimal
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError
)

from .models.market import Market, Orderbook, Trade, Candlestick
from .models.event import Event
from .exceptions import KalshiAPIError, RateLimitError
from .auth import KalshiAuth


class KalshiPublicClient:
    """
    Unauthenticated client for public Kalshi API endpoints.

    Use this for market research - no API keys required.
    """

    BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 5,
    ):
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        self._max_retries = max_retries

    async def __aenter__(self) -> "KalshiPublicClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self._client.aclose()

    @retry(
        retry=retry_if_exception_type((RateLimitError, httpx.NetworkError, httpx.TimeoutException)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=60),
    )
    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        """Make rate-limited GET request with retry."""
        response = await self._client.get(path, params=params)

        if response.status_code == 429:
            # Raise exception to trigger tenacity retry
            raise RateLimitError("Rate limit exceeded")
            
        if response.status_code >= 400:
            raise KalshiAPIError(
                status_code=response.status_code,
                message=response.text,
            )
        return response.json()

    # ==================== Markets ====================

    async def get_markets(
        self,
        status: Optional[str] = None,
        event_ticker: Optional[str] = None,
        series_ticker: Optional[str] = None,
        limit: int = 100,
    ) -> list[Market]:
        """
        Fetch markets with optional filters.
        """
        params = {"limit": min(limit, 1000)}
        if status:
            params["status"] = status
        if event_ticker:
            params["event_ticker"] = event_ticker
        if series_ticker:
            params["series_ticker"] = series_ticker

        data = await self._get("/markets", params)
        return [Market.model_validate(m) for m in data.get("markets", [])]

    async def get_all_markets(
        self,
        status: Optional[str] = None,
        max_pages: int = 100,
    ) -> AsyncIterator[Market]:
        """
        Iterate through ALL markets with automatic pagination.
        Includes a safety limit to prevent infinite loops.
        """
        cursor = None
        pages = 0
        while pages < max_pages:
            params = {"limit": 1000}
            if status:
                params["status"] = status
            if cursor:
                params["cursor"] = cursor

            data = await self._get("/markets", params)
            markets = data.get("markets", [])

            for market_data in markets:
                yield Market.model_validate(market_data)

            cursor = data.get("cursor")
            if not cursor or not markets:
                break
            pages += 1

    async def get_market(self, ticker: str) -> Market:
        """Fetch single market by ticker."""
        data = await self._get(f"/markets/{ticker}")
        return Market.model_validate(data["market"])

    async def get_orderbook(self, ticker: str, depth: int = 10) -> Orderbook:
        """
        Fetch current orderbook for a market.
        """
        data = await self._get(
            f"/markets/{ticker}/orderbook",
            params={"depth": depth}
        )
        return Orderbook.model_validate(data["orderbook"])

    async def get_trades(
        self,
        ticker: Optional[str] = None,
        limit: int = 100,
        min_ts: Optional[int] = None,
        max_ts: Optional[int] = None,
    ) -> list[Trade]:
        """Fetch public trade history."""
        params = {"limit": min(limit, 1000)}
        if ticker:
            params["ticker"] = ticker
        if min_ts:
            params["min_ts"] = min_ts
        if max_ts:
            params["max_ts"] = max_ts

        data = await self._get("/markets/trades", params)
        return [Trade.model_validate(t) for t in data.get("trades", [])]

    async def get_candlesticks(
        self,
        ticker: str,
        period_interval: int = 60,  # Minutes
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
    ) -> list[Candlestick]:
        """
        Fetch OHLC candlestick data.
        """
        params = {"period_interval": period_interval}
        if start_ts:
            params["start_ts"] = start_ts
        if end_ts:
            params["end_ts"] = end_ts

        # Note: API path might vary between markets/series. 
        # Using markets/{ticker}/candlesticks as per V2 docs for specific contracts.
        data = await self._get(f"/markets/{ticker}/candlesticks", params)
        return [Candlestick.model_validate(c) for c in data.get("candlesticks", [])]

    # ==================== Events ====================

    async def get_events(
        self,
        status: Optional[str] = None,
        series_ticker: Optional[str] = None,
        limit: int = 100,
    ) -> list[Event]:
        """Fetch events with optional filters."""
        params = {"limit": min(limit, 1000)}
        if status:
            params["status"] = status
        if series_ticker:
            params["series_ticker"] = series_ticker

        data = await self._get("/events", params)
        return [Event.model_validate(e) for e in data.get("events", [])]

    async def get_event(self, event_ticker: str) -> Event:
        """Fetch single event by ticker."""
        data = await self._get(f"/events/{event_ticker}")
        return Event.model_validate(data["event"])

    # ==================== Exchange ====================

    async def get_exchange_status(self) -> dict:
        """Check if exchange is operational."""
        return await self._get("/exchange/status")


class KalshiClient(KalshiPublicClient):
    """
    Authenticated client extending public client with portfolio endpoints.
    """

    def __init__(
        self,
        key_id: str,
        private_key_path: str,
        environment: str = "prod",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._auth = KalshiAuth(key_id, private_key_path)

        # Override base URL for demo if needed
        if environment == "demo":
            self._client = httpx.AsyncClient(
                base_url="https://demo-api.kalshi.co/trade-api/v2",
                timeout=kwargs.get("timeout", 30.0),
            )

    @retry(
        retry=retry_if_exception_type((RateLimitError, httpx.NetworkError, httpx.TimeoutException)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=60),
    )
    async def _auth_get(self, path: str, params: Optional[dict] = None) -> dict:
        """Authenticated GET request with retry."""
        headers = self._auth.get_headers("GET", path)
        response = await self._client.get(path, params=params, headers=headers)
        
        if response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")

        if response.status_code >= 400:
            raise KalshiAPIError(response.status_code, response.text)
            
        return response.json()

    async def get_balance(self) -> dict:
        """Get account balance."""
        return await self._auth_get("/portfolio/balance")

    async def get_positions(self) -> list[dict]:
        """Get current positions."""
        data = await self._auth_get("/portfolio/positions")
        return data.get("positions", [])

    async def get_orders(
        self,
        ticker: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict]:
        """Get order history."""
        params = {}
        if ticker:
            params["ticker"] = ticker
        if status:
            params["status"] = status
        data = await self._auth_get("/portfolio/orders", params)
        return data.get("orders", [])
```

### 3.4 Custom Exceptions

```python
# src/kalshi_research/api/exceptions.py
class KalshiError(Exception):
    """Base exception for Kalshi API errors."""
    pass


class KalshiAPIError(KalshiError):
    """HTTP API error with status code."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")


class RateLimitError(KalshiAPIError):
    """Rate limit exceeded (HTTP 429)."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(429, message)


class AuthenticationError(KalshiAPIError):
    """Authentication failed (HTTP 401)."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(401, message)


class MarketNotFoundError(KalshiAPIError):
    """Market ticker not found (HTTP 404)."""

    def __init__(self, ticker: str):
        super().__init__(404, f"Market not found: {ticker}")
```

---

## 4. Implementation Tasks

### 4.1 Phase 1: Core Infrastructure

- [ ] Create module structure under `src/kalshi_research/api/`
- [ ] Implement base Pydantic models for Market, Event, Trade
- [ ] Implement custom exception hierarchy
- [ ] Implement `KalshiPublicClient` using `tenacity` for robust retries

### 4.2 Phase 2: Public Client

- [ ] Add `/markets` endpoint with pagination and safety limits
- [ ] Add `/markets/{ticker}` endpoint
- [ ] Add `/markets/{ticker}/orderbook` endpoint
- [ ] Add `/markets/trades` endpoint
- [ ] Add `/markets/{ticker}/candlesticks` endpoint
- [ ] Add `/events` endpoints
- [ ] Add `/exchange/status` endpoint
- [ ] Write comprehensive unit tests with `respx` mocking

### 4.3 Phase 3: Authenticated Client

- [ ] Port existing RSA-PSS auth to new architecture
- [ ] Implement `KalshiClient` extending public client
- [ ] Add portfolio endpoints (balance, positions, orders)
- [ ] Write integration tests (requires API keys)

### 4.4 Phase 4: Sync Wrapper

- [ ] Add synchronous wrapper for non-async contexts (optional but nice)

---

## 5. Acceptance Criteria

1. **Public Data**: Can fetch all open markets without API keys
2. **Pagination**: `get_all_markets()` iterates through 1000+ markets
3. **Robustness**: Automatically retries on 429 and network errors, handling concurrency safely
4. **Error Handling**: Proper exceptions for 4xx/5xx responses
5. **Type Safety**: All responses validated through Pydantic models
6. **Tests**: >90% coverage on public client code
7. **Integration**: Existing `main.py` still works after refactor

---

## 6. Usage Examples

```python
# Research usage - no API keys needed
import asyncio
from kalshi_research.api import KalshiPublicClient

async def main():
    async with KalshiPublicClient() as client:
        # Get all open markets
        markets = await client.get_markets(status="open")
        print(f"Found {len(markets)} open markets")

        # Get specific market details
        market = await client.get_market("KXBTC-24DEC31-T100000")
        print(f"{market.title}: {market.yes_bid}c / {market.yes_ask}c")

        # Get orderbook
        orderbook = await client.get_orderbook(market.ticker)
        print(f"Spread: {orderbook.spread}c, Midpoint: {orderbook.midpoint}c")

        # Iterate through ALL markets
        async for market in client.get_all_markets(status="open"):
            if market.volume_24h > 10000:
                print(f"High volume: {market.ticker}")

asyncio.run(main())
```