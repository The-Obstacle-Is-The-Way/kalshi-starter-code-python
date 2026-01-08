"""
Unit tests for rate limiting functionality.
"""

import asyncio
import time
from unittest.mock import MagicMock

import pytest

from kalshi_research.api.rate_limiter import RateLimiter, RateTier, TokenBucket


class TestTokenBucket:
    @pytest.mark.asyncio
    async def test_immediate_acquire_when_tokens_available(self) -> None:
        """Should acquire immediately when tokens available."""
        bucket = TokenBucket(tokens_per_second=10)
        start = time.monotonic()
        await bucket.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1  # Should be nearly instant

    @pytest.mark.asyncio
    async def test_wait_when_tokens_exhausted(self) -> None:
        """Should wait when tokens exhausted."""
        bucket = TokenBucket(tokens_per_second=10, burst_size=1)
        # Use the one token
        await bucket.acquire()

        start = time.monotonic()
        # Should wait ~0.1 sec (1 token / 10 per sec)
        await bucket.acquire()
        elapsed = time.monotonic() - start

        # Allow some jitter, but it should be at least 0.08s
        assert 0.08 < elapsed < 0.2

    @pytest.mark.asyncio
    async def test_burst_capacity(self) -> None:
        """Should handle burst capacity."""
        # 10 tokens/sec, but can hold 5
        bucket = TokenBucket(tokens_per_second=10, burst_size=5)

        # Wait for bucket to fill (0.5s)
        await asyncio.sleep(0.6)

        start = time.monotonic()
        # Should be able to consume 5 instantly
        for _ in range(5):
            await bucket.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1

        # The 6th should block
        start = time.monotonic()
        await bucket.acquire()
        elapsed = time.monotonic() - start
        assert elapsed > 0.08


class TestRateLimiter:
    def test_tier_limits_applied(self) -> None:
        """Verify tier limits are correctly applied."""
        limiter = RateLimiter(tier=RateTier.BASIC)
        assert limiter.tier == RateTier.BASIC
        # Access private buckets to verify config (implementation detail check)
        # Basic: 20 read, 10 write
        # Safety margin 0.9 -> 18 read, 9 write
        assert limiter._read_bucket._rate == 18
        assert limiter._write_bucket._rate == 9

    def test_advanced_tier_limits(self) -> None:
        """Verify advanced tier limits."""
        limiter = RateLimiter(tier=RateTier.ADVANCED)
        # Advanced: 30 read, 30 write
        # Safety margin 0.9 -> 27 read, 27 write
        assert limiter._read_bucket._rate == 27
        assert limiter._write_bucket._rate == 27

    @pytest.mark.asyncio
    async def test_read_vs_write_separation(self) -> None:
        """Read and write should have separate buckets."""
        limiter = RateLimiter(tier=RateTier.BASIC)

        async def mock_acquire(*args, **kwargs):
            pass

        # Mock the buckets
        limiter._read_bucket = MagicMock(spec=TokenBucket)
        limiter._read_bucket.acquire = MagicMock(side_effect=mock_acquire)

        limiter._write_bucket = MagicMock(spec=TokenBucket)
        limiter._write_bucket.acquire = MagicMock(side_effect=mock_acquire)

        # GET request -> read bucket
        await limiter.acquire("GET", "/markets")
        limiter._read_bucket.acquire.assert_called_once()
        limiter._write_bucket.acquire.assert_not_called()

        limiter._read_bucket.reset_mock()
        limiter._write_bucket.reset_mock()

        # POST request -> write bucket
        await limiter.acquire("POST", "/portfolio/orders")
        limiter._read_bucket.acquire.assert_not_called()
        limiter._write_bucket.acquire.assert_called_once_with(1.0)

    @pytest.mark.asyncio
    async def test_batch_write_cost(self) -> None:
        """Batch writes should consume multiple tokens."""
        limiter = RateLimiter(tier=RateTier.BASIC)

        async def mock_acquire(*args, **kwargs):
            pass

        limiter._write_bucket = MagicMock(spec=TokenBucket)
        limiter._write_bucket.acquire = MagicMock(side_effect=mock_acquire)

        # Batch order -> cost = batch_size
        await limiter.acquire("POST", "/portfolio/orders/batched", batch_size=5)
        limiter._write_bucket.acquire.assert_called_once_with(5.0)

    @pytest.mark.asyncio
    async def test_non_write_post(self) -> None:
        """POST to non-write endpoint should be read."""
        limiter = RateLimiter(tier=RateTier.BASIC)

        async def mock_acquire(*args, **kwargs):
            pass

        limiter._read_bucket = MagicMock(spec=TokenBucket)
        limiter._read_bucket.acquire = MagicMock(side_effect=mock_acquire)

        limiter._write_bucket = MagicMock(spec=TokenBucket)
        limiter._write_bucket.acquire = MagicMock(side_effect=mock_acquire)

        # Unknown POST -> defaults to read
        await limiter.acquire("POST", "/unknown/endpoint")
        limiter._read_bucket.acquire.assert_called_once()
        limiter._write_bucket.acquire.assert_not_called()
