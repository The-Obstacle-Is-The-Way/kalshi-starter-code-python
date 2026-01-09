# BUG-049: Asymmetrical Rate Limiting (Read vs. Write)

**Status**: ✅ CLOSED
**Fixed**: 2026-01-09

## Overview
The `KalshiClient` enforces proactive rate limiting for **write** operations (orders, amendments) via `self._rate_limiter.acquire()`, but completely neglects **read** operations (market data, portfolio fetches).

## Severity: High (Trading Risk)
- **Impact**: High frequency polling (e.g., waiting for a market to open or scanning for arb) will rapidly exhaust the API rate limit.
- **Consequence**: The application will hit HTTP 429 errors. While the retry logic handles this, repeated 429s can lead to an IP ban from Kalshi, shutting down all trading activity.

## Vendor Verification (SSOT)
- **Source**: `docs/_vendor-docs/kalshi-api-reference.md` (Section: Rate Limits)
- **Citation**: "Tier Basic: Read/sec 20, Write/sec 10".
- **Confirmation**: The API explicitly imposes a **Read Limit** (20/sec for Basic). The current implementation only throttles writes (`CreateOrder`, etc.), leaving reads unprotected.

## Location
- `src/kalshi_research/api/client.py`
  - `_auth_get()`: **MISSING** `acquire()` call.
  - `_get()` (Public Client): **MISSING** `acquire()` call.
  - `create_order()`: **HAS** `await self._rate_limiter.acquire(...)`.

## Reproduction
1. Run a loop calling `client.get_market("KXBTC")` 100 times/second.
2. Observe 429 errors in logs.

## Proposed Fix
1. Inject the `RateLimiter` into `KalshiPublicClient` as well (currently only in `KalshiClient`).
2. Call `await self._rate_limiter.acquire("GET", path)` in both `_get` and `_auth_get`.
3. Ensure the `RateLimiter` distinguishes between Public API limits and Authenticated API limits if they differ (Kalshi docs specify different tiers).
