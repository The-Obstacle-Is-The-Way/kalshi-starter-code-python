"""
Rate limiting for Kalshi API.

Implements a token bucket algorithm to enforce rate limits per tier.
"""

import asyncio
import time
from enum import Enum

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
    """

    def __init__(self, tokens_per_second: float, burst_size: float | None = None) -> None:
        self._rate = tokens_per_second
        self._max_tokens = burst_size or tokens_per_second
        self._tokens = float(self._max_tokens)
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire.
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
                if wait_time > 0.1:  # Only log significant waits
                    logger.debug("Rate limit wait", wait_seconds=wait_time)
                await asyncio.sleep(wait_time)
                self._tokens = 0.0
            else:
                self._tokens -= tokens


class RateLimiter:
    """
    Manages rate limiting for Kalshi API requests.
    """

    BATCH_ORDERS_PATH = "/portfolio/orders/batched"

    # Endpoints that count as write operations
    # Note: DELETE is implicitly a write
    WRITE_ENDPOINTS_PREFIX = frozenset(
        [
            "/portfolio/orders",
        ]
    )

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

        # Apply safety margin
        read_limit = limits["read"] * safety_margin
        write_limit = limits["write"] * safety_margin

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
        await self._read_bucket.acquire(1.0)

    async def acquire_write(self, cost: float = 1.0) -> None:
        """Acquire permission for write operation(s)."""
        await self._write_bucket.acquire(cost)

    async def acquire(self, method: str, path: str, batch_size: int = 0) -> None:
        """
        Acquire permission for an API request.
        """
        # Determine if it's a write operation
        # All DELETEs are writes
        # POSTs to order endpoints are writes
        is_write = method == "DELETE" or (
            method == "POST" and any(path.startswith(ep) for ep in self.WRITE_ENDPOINTS_PREFIX)
        )

        if is_write:
            # Kalshi write-limit cost model:
            # - CreateOrder / CancelOrder / AmendOrder / DecreaseOrder: 1 transaction
            # - BatchCreateOrders: 1 transaction per order item
            # - BatchCancelOrders: 0.2 transactions per cancel item (sole 0.2 exception)
            cost = 1.0

            if path == self.BATCH_ORDERS_PATH:
                item_count = float(batch_size if batch_size > 0 else 1)
                if method == "DELETE":
                    cost = 0.2 * item_count
                elif method == "POST":
                    cost = item_count

            await self.acquire_write(cost)
        else:
            await self.acquire_read()

    @property
    def tier(self) -> RateTier:
        """Return the configured Kalshi rate limit tier."""
        return self._tier
