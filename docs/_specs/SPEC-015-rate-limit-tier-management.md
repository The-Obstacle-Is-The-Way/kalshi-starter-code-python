# SPEC-015: Rate Limit Tier Management

**Status:** Proposed
**Priority:** P1 (Important for Reliability)
**Estimated Complexity:** Medium
**Dependencies:** SPEC-002 (API Client)
**Official Docs:** [docs.kalshi.com](https://docs.kalshi.com/getting_started/rate_limits)

---

## 1. Problem Statement

### Current Issue
The API client has basic retry logic for 429 errors but lacks:
1. **Tier Awareness**: Doesn't know user's rate limit tier
2. **Proactive Throttling**: Waits for 429 instead of preventing it
3. **Endpoint Classification**: Treats all endpoints the same
4. **Retry-After Header**: Ignores official backoff guidance

### Official Rate Limits

| Tier | Read Limit | Write Limit | Qualification |
|------|-----------|------------|---------------|
| **Basic** | 20/sec | 10/sec | Default (signup) |
| **Advanced** | 30/sec | 30/sec | Application form |
| **Premier** | 100/sec | 100/sec | 3.75% exchange volume |
| **Prime** | 400/sec | 400/sec | 7.5% exchange volume |

### Write-Limited Operations (Count Against Write Limit)
- `BatchCreateOrders` (each item = 1 transaction)
- `BatchCancelOrders` (each cancel = 0.2 transactions)
- `CreateOrder`, `CancelOrder`, `AmendOrder`, `DecreaseOrder`

---

## 2. Solution: Smart Rate Limiting

### 2.1 Token Bucket Algorithm

```python
# src/kalshi_research/api/rate_limiter.py
import asyncio
import time
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class RateTier(str, Enum):
    """Kalshi API rate limit tiers."""
    BASIC = "basic"
    ADVANCED = "advanced"
    PREMIER = "premier"
    PRIME = "prime"


TIER_LIMITS: dict[RateTier, dict[str, int]] = {
    RateTier.BASIC: {"read": 20, "write": 10},
    RateTier.ADVANCED: {"read": 30, "write": 30},
    RateTier.PREMIER: {"read": 100, "write": 100},
    RateTier.PRIME: {"read": 400, "write": 400},
}


class TokenBucket:
    """
    Token bucket rate limiter for smooth request throttling.

    Prevents bursts that would trigger 429 errors.
    """

    def __init__(self, tokens_per_second: int, burst_size: int | None = None) -> None:
        self._rate = tokens_per_second
        self._max_tokens = burst_size or tokens_per_second
        self._tokens = float(self._max_tokens)
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (default: 1)
        """
        async with self._lock:
            # Refill tokens based on elapsed time
            now = time.monotonic()
            elapsed = now - self._last_update
            self._tokens = min(
                self._max_tokens,
                self._tokens + elapsed * self._rate,
            )
            self._last_update = now

            # Wait if insufficient tokens
            if self._tokens < tokens:
                wait_time = (tokens - self._tokens) / self._rate
                logger.debug("Rate limit wait", wait_seconds=wait_time)
                await asyncio.sleep(wait_time)
                self._tokens = 0
            else:
                self._tokens -= tokens


class RateLimiter:
    """
    Manages rate limiting for Kalshi API requests.

    Provides separate buckets for read and write operations
    based on the user's tier.
    """

    # Endpoints that count as write operations
    WRITE_ENDPOINTS = frozenset([
        "/portfolio/orders",  # POST
        "/portfolio/orders/batched",  # POST
    ])

    # Endpoints that support batch operations
    BATCH_ENDPOINTS = frozenset([
        "/portfolio/orders/batched",
    ])

    def __init__(
        self,
        tier: RateTier = RateTier.BASIC,
        safety_margin: float = 0.9,  # Use 90% of limit
    ) -> None:
        """
        Initialize rate limiter.

        Args:
            tier: User's rate limit tier
            safety_margin: Fraction of limit to use (0.9 = 90%)
        """
        self._tier = tier
        limits = TIER_LIMITS[tier]

        # Apply safety margin to avoid edge cases
        read_limit = int(limits["read"] * safety_margin)
        write_limit = int(limits["write"] * safety_margin)

        self._read_bucket = TokenBucket(read_limit)
        self._write_bucket = TokenBucket(write_limit)

        logger.info(
            "Rate limiter initialized",
            tier=tier.value,
            read_limit=read_limit,
            write_limit=write_limit,
        )

    async def acquire_read(self) -> None:
        """Acquire permission for a read operation."""
        await self._read_bucket.acquire()

    async def acquire_write(self, operations: int = 1) -> None:
        """
        Acquire permission for write operation(s).

        Args:
            operations: Number of write operations (for batch requests)
        """
        await self._write_bucket.acquire(operations)

    async def acquire(self, method: str, path: str, batch_size: int = 0) -> None:
        """
        Acquire permission for an API request.

        Args:
            method: HTTP method (GET, POST, DELETE)
            path: API endpoint path
            batch_size: Number of items in batch request (for batched endpoints)
        """
        # POST/DELETE to specific endpoints are writes
        is_write = method in ("POST", "DELETE") and any(
            path.startswith(ep) for ep in self.WRITE_ENDPOINTS
        )

        if is_write:
            # Batch operations count each item
            ops = max(1, batch_size)
            await self.acquire_write(ops)
        else:
            await self.acquire_read()

    @property
    def tier(self) -> RateTier:
        return self._tier
```

### 2.2 Client Integration

```python
# src/kalshi_research/api/client.py (modified)
class KalshiPublicClient:
    """Enhanced client with rate limiting."""

    def __init__(
        self,
        timeout: float = 30.0,
        rate_tier: RateTier = RateTier.BASIC,
    ) -> None:
        self._client = httpx.AsyncClient(...)
        self._rate_limiter = RateLimiter(tier=rate_tier)

    async def _get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Rate-limited GET request."""
        await self._rate_limiter.acquire("GET", path)
        response = await self._client.get(path, params=params)
        # ... error handling ...
```

### 2.3 Retry-After Header Support

```python
# src/kalshi_research/api/exceptions.py (enhanced)
class RateLimitError(KalshiAPIError):
    """Rate limit exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
    ) -> None:
        super().__init__(429, message)
        self.retry_after = retry_after  # Seconds to wait


# In client:
if response.status_code == 429:
    retry_after = response.headers.get("Retry-After")
    raise RateLimitError(
        message=response.text,
        retry_after=int(retry_after) if retry_after else None,
    )
```

---

## 3. Configuration

### 3.1 Environment Variable

```bash
# .env
KALSHI_RATE_TIER=basic  # basic, advanced, premier, prime
```

### 3.2 CLI Override

```bash
# Override tier for specific commands
kalshi --rate-tier advanced scan movers --top 20
```

### 3.3 Auto-Detection (Future)

Could query account info to determine tier automatically:
```python
async def detect_tier(self) -> RateTier:
    """Attempt to detect rate tier from account info."""
    # Would require authenticated endpoint
    pass
```

---

## 4. Implementation Tasks

### 4.1 Phase 1: Core Rate Limiter
- [ ] Implement `TokenBucket` class
- [ ] Implement `RateLimiter` with read/write separation
- [ ] Add `RateTier` enum with official limits
- [ ] Write unit tests for token bucket behavior

### 4.2 Phase 2: Client Integration
- [ ] Add `RateLimiter` to `KalshiPublicClient`
- [ ] Add `RateLimiter` to `KalshiClient`
- [ ] Enhance `RateLimitError` with `retry_after`
- [ ] Update retry logic to respect `Retry-After` header

### 4.3 Phase 3: Configuration
- [ ] Add `KALSHI_RATE_TIER` environment variable
- [ ] Add `--rate-tier` CLI option
- [ ] Document tier qualification in README

---

## 5. Acceptance Criteria

1. **No 429 Errors**: Proactive throttling prevents rate limit hits
2. **Tier Aware**: Respects user's tier limits
3. **Smooth**: Token bucket prevents request bursts
4. **Configurable**: Easy to change tier via env/CLI
5. **Observable**: Logs when throttling occurs

---

## 6. Testing Strategy

```python
# tests/unit/api/test_rate_limiter.py
import pytest
import asyncio
from kalshi_research.api.rate_limiter import TokenBucket, RateLimiter, RateTier


class TestTokenBucket:
    @pytest.mark.asyncio
    async def test_immediate_acquire_when_tokens_available(self) -> None:
        """Should acquire immediately when tokens available."""
        bucket = TokenBucket(tokens_per_second=10)
        start = asyncio.get_event_loop().time()
        await bucket.acquire()
        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed < 0.1  # Should be nearly instant

    @pytest.mark.asyncio
    async def test_wait_when_tokens_exhausted(self) -> None:
        """Should wait when tokens exhausted."""
        bucket = TokenBucket(tokens_per_second=10, burst_size=1)
        await bucket.acquire()  # Use the one token
        start = asyncio.get_event_loop().time()
        await bucket.acquire()  # Should wait ~0.1 sec
        elapsed = asyncio.get_event_loop().time() - start
        assert 0.08 < elapsed < 0.15  # ~100ms wait


class TestRateLimiter:
    def test_tier_limits_applied(self) -> None:
        """Verify tier limits are correctly applied."""
        limiter = RateLimiter(tier=RateTier.BASIC)
        assert limiter.tier == RateTier.BASIC

    @pytest.mark.asyncio
    async def test_read_vs_write_separation(self) -> None:
        """Read and write should have separate buckets."""
        limiter = RateLimiter(tier=RateTier.BASIC)
        # Should not block each other
        await limiter.acquire_read()
        await limiter.acquire_write()
```

---

## 7. References

- Official rate limit docs: https://docs.kalshi.com/getting_started/rate_limits
- Tier upgrade form: https://kalshi.typeform.com/advanced-api
