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
| `/markets/candlesticks` | GET | OHLC price history (batch, requires market_tickers param) | P0 |
| `/series/{series_ticker}/markets/{ticker}/candlesticks` | GET | Single market candlesticks | P1 |

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

**Important:** The Kalshi API uses different values for filter parameters vs response fields:
- **Filter status** (query param): `unopened`, `open`, `closed`, `settled`
- **Response status** (field value): `active`, `closed`, `determined`, `finalized`

```python
# src/kalshi_research/api/models/market.py
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MarketStatus(str, Enum):
    """Market status as returned in API responses."""

    ACTIVE = "active"
    CLOSED = "closed"
    DETERMINED = "determined"
    FINALIZED = "finalized"


class MarketFilterStatus(str, Enum):
    """Market status values for API filter parameters."""

    UNOPENED = "unopened"
    OPEN = "open"
    CLOSED = "closed"
    SETTLED = "settled"


class Market(BaseModel):
    """Represents a Kalshi prediction market."""

    model_config = ConfigDict(frozen=True)

    ticker: str = Field(..., description="Unique market identifier")
    event_ticker: str = Field(..., description="Parent event ticker")
    # Note: series_ticker may not be present in all responses
    series_ticker: str | None = Field(default=None, description="Parent series ticker")

    title: str = Field(..., description="Market question/title")
    subtitle: str = Field(default="", description="Additional context")

    status: MarketStatus
    # Result can be "yes", "no", "void", or "" (empty string when undetermined)
    result: Literal["yes", "no", "void", ""] = ""

    # Pricing (in cents, 0-100)
    yes_bid: int = Field(..., ge=0, le=100, description="Best yes bid in cents")
    yes_ask: int = Field(..., ge=0, le=100, description="Best yes ask in cents")
    no_bid: int = Field(..., ge=0, le=100, description="Best no bid in cents")
    no_ask: int = Field(..., ge=0, le=100, description="Best no ask in cents")
    last_price: int | None = Field(default=None, ge=0, le=100)

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


# src/kalshi_research/api/models/orderbook.py
class Orderbook(BaseModel):
    """
    Market orderbook snapshot.

    Note: API returns yes/no as list of [price, quantity] tuples, or null if empty.
    The API only returns bids (no asks) - use yes for YES bids, no for NO bids.
    """

    model_config = ConfigDict(frozen=True)

    # Each level is [price_cents, quantity]
    yes: list[tuple[int, int]] | None = None
    no: list[tuple[int, int]] | None = None
    # Dollar-denominated versions (optional in response)
    yes_dollars: list[tuple[str, int]] | None = None
    no_dollars: list[tuple[str, int]] | None = None

    @property
    def best_yes_bid(self) -> int | None:
        """Best YES bid price in cents."""
        if not self.yes:
            return None
        return max(price for price, _ in self.yes)

    @property
    def best_no_bid(self) -> int | None:
        """Best NO bid price in cents."""
        if not self.no:
            return None
        return max(price for price, _ in self.no)

    @property
    def spread(self) -> int | None:
        """
        Calculate implied spread in cents.

        Since orderbook only has bids, spread = 100 - best_yes_bid - best_no_bid.
        """
        if self.best_yes_bid is None or self.best_no_bid is None:
            return None
        return 100 - self.best_yes_bid - self.best_no_bid

    @property
    def midpoint(self) -> Decimal | None:
        """Calculate midpoint price for YES side."""
        if self.best_yes_bid is None or self.best_no_bid is None:
            return None
        # Implied YES ask = 100 - best_no_bid
        implied_yes_ask = 100 - self.best_no_bid
        return (Decimal(self.best_yes_bid) + Decimal(implied_yes_ask)) / 2


# src/kalshi_research/api/models/trade.py
class Trade(BaseModel):
    """Public trade record."""

    model_config = ConfigDict(frozen=True)

    trade_id: str
    ticker: str
    created_time: datetime  # Note: API uses created_time, not timestamp
    yes_price: int = Field(..., ge=1, le=99, description="YES price in cents")
    no_price: int = Field(..., ge=1, le=99, description="NO price in cents")
    count: int = Field(..., ge=1, description="Number of contracts")
    taker_side: Literal["yes", "no"]


# src/kalshi_research/api/models/candlestick.py
class Candlestick(BaseModel):
    """OHLC price data for a single period."""

    model_config = ConfigDict(frozen=True)

    # Timestamps as Unix seconds
    start_ts: int = Field(..., description="Period start timestamp (Unix seconds)")
    end_ts: int = Field(..., description="Period end timestamp (Unix seconds)")

    # OHLC prices in cents
    open: int
    high: int
    low: int
    close: int
    volume: int

    @property
    def period_start(self) -> datetime:
        """Period start as datetime (UTC)."""
        from datetime import timezone

        return datetime.fromtimestamp(self.start_ts, tz=timezone.utc)

    @property
    def period_end(self) -> datetime:
        """Period end as datetime (UTC)."""
        from datetime import timezone

        return datetime.fromtimestamp(self.end_ts, tz=timezone.utc)


class CandlestickResponse(BaseModel):
    """Response from batch candlesticks endpoint."""

    model_config = ConfigDict(frozen=True)

    market_ticker: str
    candlesticks: list[Candlestick]
```

### 3.3 Client Architecture

```python
# src/kalshi_research/api/client.py
from typing import Any, AsyncIterator

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .exceptions import KalshiAPIError, RateLimitError
from .models.market import (
    Candlestick,
    CandlestickResponse,
    Market,
    MarketFilterStatus,
    Orderbook,
    Trade,
)
from .models.event import Event


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

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self._client.aclose()

    @retry(
        retry=retry_if_exception_type(
            (RateLimitError, httpx.NetworkError, httpx.TimeoutException)
        ),
        stop=stop_after_attempt(5),  # TODO: Use self._max_retries when tenacity supports it
        wait=wait_exponential(multiplier=1, min=1, max=60),
    )
    async def _get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make rate-limited GET request with retry."""
        response = await self._client.get(path, params=params)

        if response.status_code == 429:
            # Raise exception to trigger tenacity retry
            # TODO: Respect Retry-After header if present
            raise RateLimitError("Rate limit exceeded")

        if response.status_code >= 400:
            raise KalshiAPIError(
                status_code=response.status_code,
                message=response.text,
            )
        result: dict[str, Any] = response.json()
        return result

    # ==================== Markets ====================

    async def get_markets(
        self,
        status: MarketFilterStatus | str | None = None,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        limit: int = 100,
    ) -> list[Market]:
        """
        Fetch markets with optional filters.

        Note: status filter uses different values than response status field.
        Filter: unopened, open, closed, settled
        Response: active, closed, determined, finalized
        """
        params: dict[str, Any] = {"limit": min(limit, 1000)}
        if status:
            params["status"] = status.value if isinstance(status, MarketFilterStatus) else status
        if event_ticker:
            params["event_ticker"] = event_ticker
        if series_ticker:
            params["series_ticker"] = series_ticker

        data = await self._get("/markets", params)
        return [Market.model_validate(m) for m in data.get("markets", [])]

    async def get_all_markets(
        self,
        status: MarketFilterStatus | str | None = None,
        max_pages: int = 100,
    ) -> AsyncIterator[Market]:
        """
        Iterate through ALL markets with automatic pagination.
        Includes a safety limit to prevent infinite loops.
        """
        cursor: str | None = None
        pages = 0
        while pages < max_pages:
            params: dict[str, Any] = {"limit": 1000}
            if status:
                params["status"] = (
                    status.value if isinstance(status, MarketFilterStatus) else status
                )
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

        Note: Orderbook returns yes/no bids only (no asks).
        Each is a list of [price, quantity] tuples, or null if empty.
        """
        data = await self._get(
            f"/markets/{ticker}/orderbook", params={"depth": depth}
        )
        return Orderbook.model_validate(data["orderbook"])

    async def get_trades(
        self,
        ticker: str | None = None,
        limit: int = 100,
        min_ts: int | None = None,
        max_ts: int | None = None,
    ) -> list[Trade]:
        """Fetch public trade history."""
        params: dict[str, Any] = {"limit": min(limit, 1000)}
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
        market_tickers: list[str],
        start_ts: int,
        end_ts: int,
        period_interval: int = 60,  # Minutes: 1, 60, or 1440
    ) -> list[CandlestickResponse]:
        """
        Fetch OHLC candlestick data for multiple markets (batch endpoint).

        Args:
            market_tickers: List of market tickers (max 100)
            start_ts: Start timestamp (Unix seconds)
            end_ts: End timestamp (Unix seconds)
            period_interval: Candle period in minutes (1, 60, or 1440)

        Returns:
            List of CandlestickResponse, one per market
        """
        if len(market_tickers) > 100:
            raise ValueError("Maximum 100 market tickers per request")

        params: dict[str, Any] = {
            "market_tickers": ",".join(market_tickers),
            "start_ts": start_ts,
            "end_ts": end_ts,
            "period_interval": period_interval,
        }

        data = await self._get("/markets/candlesticks", params)
        return [
            CandlestickResponse.model_validate(m) for m in data.get("markets", [])
        ]

    async def get_series_candlesticks(
        self,
        series_ticker: str,
        ticker: str,
        start_ts: int | None = None,
        end_ts: int | None = None,
        period_interval: int = 60,
    ) -> list[Candlestick]:
        """
        Fetch OHLC candlestick data for a single market within a series.

        Args:
            series_ticker: The series ticker
            ticker: The market ticker
            start_ts: Optional start timestamp (Unix seconds)
            end_ts: Optional end timestamp (Unix seconds)
            period_interval: Candle period in minutes (1, 60, or 1440)
        """
        params: dict[str, Any] = {"period_interval": period_interval}
        if start_ts:
            params["start_ts"] = start_ts
        if end_ts:
            params["end_ts"] = end_ts

        data = await self._get(
            f"/series/{series_ticker}/markets/{ticker}/candlesticks", params
        )
        return [Candlestick.model_validate(c) for c in data.get("candlesticks", [])]

    # ==================== Events ====================

    async def get_events(
        self,
        status: str | None = None,
        series_ticker: str | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Fetch events with optional filters."""
        params: dict[str, Any] = {"limit": min(limit, 1000)}
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

    async def get_exchange_status(self) -> dict[str, Any]:
        """Check if exchange is operational."""
        return await self._get("/exchange/status")


class KalshiClient(KalshiPublicClient):
    """
    Authenticated client extending public client with portfolio endpoints.

    IMPORTANT: Auth signing requires the FULL path including /trade-api/v2 prefix.
    The signature is computed over: timestamp + method + full_path (without query params).
    """

    DEMO_BASE = "https://demo-api.kalshi.co"
    PROD_BASE = "https://api.elections.kalshi.com"
    API_PATH = "/trade-api/v2"

    def __init__(
        self,
        key_id: str,
        private_key_path: str,
        environment: str = "prod",
        timeout: float = 30.0,
    ):
        # Don't call super().__init__() - we create client with environment-specific URL
        base_host = self.DEMO_BASE if environment == "demo" else self.PROD_BASE
        self._base_url = base_host + self.API_PATH
        self._auth = KalshiAuth(key_id, private_key_path)
        self._max_retries = 5

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    async def __aenter__(self) -> "KalshiClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self._client.aclose()

    @retry(
        retry=retry_if_exception_type(
            (RateLimitError, httpx.NetworkError, httpx.TimeoutException)
        ),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=60),
    )
    async def _auth_get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Authenticated GET request with retry.

        CRITICAL: Auth signing uses the FULL path including /trade-api/v2 prefix.
        """
        # Sign with full path (e.g., /trade-api/v2/portfolio/balance)
        full_path = self.API_PATH + path
        headers = self._auth.get_headers("GET", full_path)
        response = await self._client.get(path, params=params, headers=headers)

        if response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")

        if response.status_code >= 400:
            raise KalshiAPIError(response.status_code, response.text)

        result: dict[str, Any] = response.json()
        return result

    async def get_balance(self) -> dict[str, Any]:
        """Get account balance."""
        return await self._auth_get("/portfolio/balance")

    async def get_positions(self) -> list[dict[str, Any]]:
        """Get current positions."""
        data = await self._auth_get("/portfolio/positions")
        return data.get("positions", [])

    async def get_orders(
        self,
        ticker: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get order history."""
        params: dict[str, Any] = {}
        if ticker:
            params["ticker"] = ticker
        if status:
            params["status"] = status
        data = await self._auth_get("/portfolio/orders", params or None)
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
- [ ] Add `/markets/candlesticks` batch endpoint
- [ ] Add `/series/{series_ticker}/markets/{ticker}/candlesticks` endpoint
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
import time

from kalshi_research.api import KalshiPublicClient
from kalshi_research.api.models.market import MarketFilterStatus


async def main() -> None:
    async with KalshiPublicClient() as client:
        # Get all open markets (filter status != response status)
        # Filter uses: unopened, open, closed, settled
        # Response returns: active, closed, determined, finalized
        markets = await client.get_markets(status=MarketFilterStatus.OPEN)
        print(f"Found {len(markets)} open markets")

        # Get specific market details
        market = await client.get_market("KXBTC-24DEC31-T100000")
        print(f"{market.title}: {market.yes_bid}c / {market.yes_ask}c")
        print(f"Status: {market.status.value}")  # e.g., "active"

        # Get orderbook (returns yes/no bids as [[price, qty], ...])
        orderbook = await client.get_orderbook(market.ticker)
        if orderbook.spread is not None:
            print(f"Spread: {orderbook.spread}c, Midpoint: {orderbook.midpoint}c")

        # Get trades (note: created_time, yes_price, no_price)
        trades = await client.get_trades(ticker=market.ticker, limit=10)
        for trade in trades:
            print(f"Trade: {trade.yes_price}c @ {trade.created_time}")

        # Get candlesticks (batch endpoint)
        now = int(time.time())
        week_ago = now - 7 * 24 * 60 * 60
        candles = await client.get_candlesticks(
            market_tickers=[market.ticker],
            start_ts=week_ago,
            end_ts=now,
            period_interval=60,  # 1 hour candles
        )
        for response in candles:
            print(f"{response.market_ticker}: {len(response.candlesticks)} candles")

        # Iterate through ALL markets
        async for mkt in client.get_all_markets(status=MarketFilterStatus.OPEN):
            if mkt.volume_24h > 10000:
                print(f"High volume: {mkt.ticker}")


asyncio.run(main())
```

---

## 7. Testing Patterns (respx)

**All unit tests MUST mock HTTP requests using `respx`. Never hit the real API in unit tests.**

```python
# tests/unit/test_api_client.py
import pytest
import respx
from httpx import Response

from kalshi_research.api.client import KalshiPublicClient
from kalshi_research.api.exceptions import KalshiAPIError, RateLimitError
from kalshi_research.api.models.market import Market, MarketStatus


@pytest.fixture
def mock_market_response() -> dict:
    """Mock market response matching real API structure."""
    return {
        "market": {
            "ticker": "KXBTC-25JAN-T100000",
            "event_ticker": "KXBTC-25JAN",
            "series_ticker": "KXBTC",
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
    async def test_get_market_success(self, mock_market_response: dict) -> None:
        """Test successful market fetch."""
        # Arrange
        ticker = "KXBTC-25JAN-T100000"
        respx.get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}").mock(
            return_value=Response(200, json=mock_market_response)
        )

        # Act
        async with KalshiPublicClient() as client:
            market = await client.get_market(ticker)

        # Assert
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
    async def test_rate_limit_retry(self, mock_market_response: dict) -> None:
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
        page1 = {
            "markets": [{"ticker": f"MKT-{i}", "event_ticker": "EVT", "title": f"Market {i}",
                        "subtitle": "", "status": "active", "result": "", "yes_bid": 50,
                        "yes_ask": 52, "no_bid": 48, "no_ask": 50, "last_price": 51,
                        "volume": 1000, "volume_24h": 100, "open_interest": 500,
                        "liquidity": 1000, "open_time": "2024-01-01T00:00:00Z",
                        "close_time": "2025-01-01T00:00:00Z",
                        "expiration_time": "2025-01-02T00:00:00Z"} for i in range(3)],
            "cursor": "page2_cursor",
        }
        page2 = {
            "markets": [{"ticker": f"MKT-{i+3}", "event_ticker": "EVT", "title": f"Market {i+3}",
                        "subtitle": "", "status": "active", "result": "", "yes_bid": 50,
                        "yes_ask": 52, "no_bid": 48, "no_ask": 50, "last_price": 51,
                        "volume": 1000, "volume_24h": 100, "open_interest": 500,
                        "liquidity": 1000, "open_time": "2024-01-01T00:00:00Z",
                        "close_time": "2025-01-01T00:00:00Z",
                        "expiration_time": "2025-01-02T00:00:00Z"} for i in range(2)],
            "cursor": None,  # No more pages
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
            return_value=Response(200, json={
                "orderbook": {
                    "yes": [[45, 100], [44, 200], [43, 500]],
                    "no": [[53, 150], [54, 250]],
                }
            })
        )

        async with KalshiPublicClient() as client:
            orderbook = await client.get_orderbook(ticker)

        assert orderbook.best_yes_bid == 45
        assert orderbook.best_no_bid == 54
        assert orderbook.spread == 100 - 45 - 54  # = 1 cent

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_candlesticks_batch(self) -> None:
        """Test batch candlesticks endpoint."""
        respx.get("https://api.elections.kalshi.com/trade-api/v2/markets/candlesticks").mock(
            return_value=Response(200, json={
                "markets": [
                    {
                        "market_ticker": "KXBTC-25JAN-T100000",
                        "candlesticks": [
                            {"start_ts": 1700000000, "end_ts": 1700003600,
                             "open": 45, "high": 48, "low": 44, "close": 47, "volume": 1000},
                        ]
                    }
                ]
            })
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
```