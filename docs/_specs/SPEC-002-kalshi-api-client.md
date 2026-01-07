# SPEC-002: Kalshi API Client Enhancement

**Status:** ✅ Implemented (core endpoints)
**Priority:** P0 (Required for any data fetching)
**Estimated Complexity:** High
**Dependencies:** SPEC-001 (Modern Python Foundation)

---

## 1. Overview

Extend the existing bare-bones Kalshi client to cover ALL public and authenticated API endpoints with proper error handling, retry logic, pagination support, and rate limiting.

## 1.0 Implementation (Current SSOT)

**Primary implementation:**
- `src/kalshi_research/api/client.py`
- `src/kalshi_research/api/models/`
- `src/kalshi_research/api/auth.py`
- `src/kalshi_research/api/exceptions.py`

**Implemented endpoints (public):**
- `/exchange/status`
- `/events`, `/events/{event_ticker}` (cursor pagination, max `limit=200`)
- `/markets`, `/markets/{ticker}`, `/markets/{ticker}/orderbook` (cursor pagination, max `limit=1000`)
- `/markets/trades`
- `/markets/candlesticks`
- `/series/{series_ticker}/markets/{ticker}/candlesticks`

**Implemented endpoints (authenticated):**
- `/portfolio/balance`
- `/portfolio/positions`
- `/portfolio/orders`
- `/portfolio/fills`

**Deferred (not yet implemented in this repo):**
- `/series/{series_ticker}` (series info)
- `/portfolio/settlements`
- Order placement/cancel endpoints

### 1.1 Goals

- Implement core Kalshi API v2 endpoints used by the platform (public research + basic portfolio reads)
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
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MarketStatus(str, Enum):
    """Market status as returned in API responses."""

    INITIALIZED = "initialized"
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
    yes_price: int = Field(..., ge=0, le=100, description="YES price in cents (rounded)")
    no_price: int = Field(..., ge=0, le=100, description="NO price in cents (rounded)")
    count: int = Field(..., ge=1, description="Number of contracts")
    taker_side: Literal["yes", "no"]


# src/kalshi_research/api/models/candlestick.py
class CandleSide(BaseModel):
    """Bid/ask series for a candlestick."""

    model_config = ConfigDict(frozen=True)

    open: int | None = None
    high: int | None = None
    low: int | None = None
    close: int | None = None

    open_dollars: str | None = None
    high_dollars: str | None = None
    low_dollars: str | None = None
    close_dollars: str | None = None


class CandlePrice(BaseModel):
    """Trade/mark price series for a candlestick."""

    model_config = ConfigDict(frozen=True)

    open: int | None = None
    high: int | None = None
    low: int | None = None
    close: int | None = None

    open_dollars: str | None = None
    high_dollars: str | None = None
    low_dollars: str | None = None
    close_dollars: str | None = None

    mean: int | None = None
    mean_dollars: str | None = None

    min: int | None = None
    max: int | None = None
    previous: int | None = None
    previous_dollars: str | None = None


class Candlestick(BaseModel):
    """
    Candlestick record as returned by the Kalshi API.

    Note: The API uses `end_period_ts` (Unix seconds) and nested objects for `price`, `yes_bid`,
    and `yes_ask`.
    """

    model_config = ConfigDict(frozen=True)

    end_period_ts: int = Field(..., description="Period end timestamp (Unix seconds)")
    open_interest: int = Field(..., ge=0)
    volume: int = Field(..., ge=0)

    price: CandlePrice
    yes_bid: CandleSide
    yes_ask: CandleSide

    @property
    def period_end(self) -> datetime:
        """Period end as datetime (UTC)."""
        from datetime import timezone

        return datetime.fromtimestamp(self.end_period_ts, tz=timezone.utc)


class CandlestickResponse(BaseModel):
    """Response from batch candlesticks endpoint."""

    model_config = ConfigDict(frozen=True)

    market_ticker: str
    candlesticks: list[Candlestick]


# src/kalshi_research/api/models/event.py
class Event(BaseModel):
    """Event as returned by the Kalshi API."""

    model_config = ConfigDict(frozen=True)

    event_ticker: str = Field(..., description="Unique event identifier")
    series_ticker: str = Field(..., description="Parent series ticker")
    title: str
    sub_title: str = ""
    category: str | None = None

    mutually_exclusive: bool = False
    available_on_brokers: bool = False

    collateral_return_type: str = ""
    strike_period: str = ""
    strike_date: datetime | None = None

    @field_validator("strike_date", mode="before")
    @classmethod
    def _empty_str_to_none(cls, value: Any) -> Any:
        if value in ("", None):
            return None
        return value
```

### 3.3 Client Architecture

```python
# src/kalshi_research/api/auth.py
import base64
import time
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class KalshiAuth:
    """
    Handles Kalshi API authentication (RSA-PSS signing).
    """

    def __init__(self, key_id: str, private_key_path: str) -> None:
        self.key_id = key_id
        self.private_key = self._load_private_key(private_key_path)

    def _load_private_key(self, path: str) -> rsa.RSAPrivateKey:
        """Load RSA private key from PEM file."""
        with open(path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None,
            )
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise ValueError("Invalid key type: expected RSA private key")
        return private_key

    def sign_pss_text(self, text: str) -> str:
        """Sign text using RSA-PSS and return base64 signature."""
        message = text.encode("utf-8")
        try:
            signature = self.private_key.sign(
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH,
                ),
                hashes.SHA256(),
            )
            return base64.b64encode(signature).decode("utf-8")
        except InvalidSignature as e:
            raise ValueError("RSA signing failed") from e

    def get_headers(self, method: str, path: str) -> dict[str, str]:
        """
        Generate authentication headers.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Full API path (e.g., /trade-api/v2/portfolio/balance)
                  MUST exclude query parameters.
        """
        # Timestamp in milliseconds
        timestamp_str = str(int(time.time() * 1000))

        # Remove query params from path if present (safety check)
        clean_path = path.split("?")[0]

        # Signature payload: timestamp + method + path
        msg_string = timestamp_str + method + clean_path
        signature = self.sign_pss_text(msg_string)

        return {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_str,
        }


# src/kalshi_research/api/client.py
from typing import Any, AsyncIterator

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .auth import KalshiAuth
from .exceptions import KalshiAPIError, RateLimitError
from .models.candlestick import Candlestick, CandlestickResponse
from .models.event import Event
from .models.market import Market, MarketFilterStatus
from .models.orderbook import Orderbook
from .models.trade import Trade


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
    ) -> None:
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
        status: MarketFilterStatus | str | None = None,
        series_ticker: str | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Fetch events with optional filters."""
        params: dict[str, Any] = {"limit": min(limit, 1000)}
        if status:
            params["status"] = status.value if isinstance(status, MarketFilterStatus) else status
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
    ) -> None:
        # Determine base URL based on environment
        base_host = self.DEMO_BASE if environment == "demo" else self.PROD_BASE
        self._base_url = base_host + self.API_PATH
        
        # Initialize parent with the correct base_url
        # Note: We override the hardcoded BASE_URL of the parent instance
        super().__init__(timeout=timeout)
        self._client.base_url = self._base_url  # Update httpx client base URL
        
        self._auth = KalshiAuth(key_id, private_key_path)

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

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")


class RateLimitError(KalshiAPIError):
    """Rate limit exceeded (HTTP 429)."""

    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(429, message)


class AuthenticationError(KalshiAPIError):
    """Authentication failed (HTTP 401)."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(401, message)


class MarketNotFoundError(KalshiAPIError):
    """Market ticker not found (HTTP 404)."""

    def __init__(self, ticker: str) -> None:
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

## 7. Testing Patterns (Minimal Mocking)

**PHILOSOPHY: Mock ONLY at system boundaries. Everything else uses REAL objects.**

The API client is a boundary - it's the ONLY place where `respx` mocking is appropriate.
The tests below verify:
1. HTTP responses are correctly parsed into REAL Pydantic models
2. Error handling works with real exceptions
3. Retry logic actually retries

**Do NOT mock:**
- The Market, Orderbook, Trade models - use real instances
- Client methods when testing services that use the client
- Computed properties or business logic

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
                            {
                                "end_period_ts": 1700003600,
                                "open_interest": 123,
                                "volume": 1000,
                                "price": {"open": 45, "high": 48, "low": 44, "close": 47},
                                "yes_bid": {"open": 44, "high": 45, "low": 43, "close": 44},
                                "yes_ask": {"open": 46, "high": 47, "low": 45, "close": 46},
                            },
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
        assert responses[0].candlesticks[0].end_period_ts == 1700003600
        assert responses[0].candlesticks[0].price.close == 47
```

---

## 8. Model Tests (NO MOCKS - Real Objects Only)

**These tests use REAL Pydantic models to verify domain logic. No mocking allowed.**

```python
# tests/unit/test_api_models.py
"""
Model tests - use REAL objects, NO MOCKS.

These tests verify that domain logic works correctly using actual
Pydantic model instances, not mocked stand-ins.
"""
import pytest
from datetime import datetime, timezone
from decimal import Decimal

from kalshi_research.api.models.market import Market, MarketStatus
from kalshi_research.api.models.orderbook import Orderbook
from kalshi_research.api.models.trade import Trade


class TestMarketModel:
    """Test Market model with REAL instances."""

    def test_market_creation_from_api_data(self, make_market) -> None:
        """Market model correctly parses API response data."""
        data = make_market(ticker="BTC-100K", yes_bid=45, yes_ask=47)

        market = Market.model_validate(data)

        assert market.ticker == "BTC-100K"
        assert market.yes_bid == 45
        assert market.yes_ask == 47
        assert market.status == MarketStatus.ACTIVE

    def test_market_status_enum_parsing(self) -> None:
        """Status string correctly maps to enum."""
        for status_str, expected_enum in [
            ("active", MarketStatus.ACTIVE),
            ("closed", MarketStatus.CLOSED),
            ("determined", MarketStatus.DETERMINED),
            ("finalized", MarketStatus.FINALIZED),
        ]:
            market = Market.model_validate({
                "ticker": "TEST",
                "event_ticker": "EVT",
                "title": "Test",
                "subtitle": "",
                "status": status_str,
                "result": "",
                "yes_bid": 50, "yes_ask": 50, "no_bid": 50, "no_ask": 50,
                "volume": 0, "volume_24h": 0, "open_interest": 0, "liquidity": 0,
                "open_time": "2024-01-01T00:00:00Z",
                "close_time": "2025-01-01T00:00:00Z",
                "expiration_time": "2025-01-02T00:00:00Z",
            })
            assert market.status == expected_enum

    def test_market_immutability(self, make_market) -> None:
        """Market model is frozen (immutable)."""
        market = Market.model_validate(make_market())

        with pytest.raises(Exception):  # Pydantic raises ValidationError on frozen
            market.ticker = "CHANGED"


class TestOrderbookModel:
    """Test Orderbook computed properties with REAL data."""

    def test_orderbook_best_bids(self) -> None:
        """Computed properties return correct best prices."""
        orderbook = Orderbook(
            yes=[(45, 100), (44, 200), (43, 500)],
            no=[(53, 150), (54, 250), (55, 400)],
        )

        assert orderbook.best_yes_bid == 45
        assert orderbook.best_no_bid == 55

    def test_orderbook_spread_calculation(self) -> None:
        """Spread = 100 - best_yes_bid - best_no_bid."""
        orderbook = Orderbook(
            yes=[(45, 100)],
            no=[(54, 100)],
        )

        # Spread = 100 - 45 - 54 = 1
        assert orderbook.spread == 1

    def test_orderbook_midpoint_calculation(self) -> None:
        """Midpoint uses implied ask from NO side."""
        orderbook = Orderbook(
            yes=[(45, 100)],
            no=[(54, 100)],
        )

        # Implied YES ask = 100 - best_no_bid = 100 - 54 = 46
        # Midpoint = (45 + 46) / 2 = 45.5
        assert orderbook.midpoint == Decimal("45.5")

    def test_orderbook_empty_sides(self) -> None:
        """Handle empty or None orderbook sides gracefully."""
        orderbook = Orderbook(yes=None, no=None)

        assert orderbook.best_yes_bid is None
        assert orderbook.best_no_bid is None
        assert orderbook.spread is None
        assert orderbook.midpoint is None

    @pytest.mark.parametrize(
        "yes_bids,no_bids,expected_spread",
        [
            ([(50, 100)], [(50, 100)], 0),     # Tight market
            ([(40, 100)], [(40, 100)], 20),    # Wide spread
            ([(1, 100)], [(1, 100)], 98),      # Extreme
        ],
    )
    def test_spread_various_scenarios(
        self,
        yes_bids: list[tuple[int, int]],
        no_bids: list[tuple[int, int]],
        expected_spread: int,
    ) -> None:
        """Spread calculation handles various market conditions."""
        orderbook = Orderbook(yes=yes_bids, no=no_bids)
        assert orderbook.spread == expected_spread


class TestTradeModel:
    """Test Trade model with REAL instances."""

    def test_trade_creation(self) -> None:
        """Trade model parses API data correctly."""
        trade = Trade(
            trade_id="abc123",
            ticker="BTC-100K",
            created_time=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
            yes_price=46,
            no_price=54,
            count=10,
            taker_side="yes",
        )

        assert trade.yes_price == 46
        assert trade.no_price == 54
        assert trade.count == 10

    def test_trade_price_validation(self) -> None:
        """Prices must be in valid range (1-99)."""
        with pytest.raises(ValueError):
            Trade(
                trade_id="bad",
                ticker="TEST",
                created_time=datetime.now(timezone.utc),
                yes_price=0,  # Invalid - must be >= 1
                no_price=100,  # Invalid - must be <= 99
                count=1,
                taker_side="yes",
            )
```
