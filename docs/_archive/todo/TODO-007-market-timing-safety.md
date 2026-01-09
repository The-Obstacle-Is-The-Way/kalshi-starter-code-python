# TODO-007: Market Timing Safety Mechanism

**Status**: ✅ Core Complete (Scanner integration done)
**Updated**: 2026-01-09

## Problem
The system currently lacks a centralized "Market Timing" authority. It is possible to:
1. Recommend a trade on a CLOSED market.
2. Calculate "edge" on a market that has already SETTLED.
3. Attempt to fetch orderbooks for EXPIRED markets.

This is documented as a P2 risk in the codebase audit.

## Objectives
1. ✅ **Create `MarketStatusVerifier`**: A service that checks `market.status`, `market.close_time`, and `market.expiration_time` against `datetime.now(UTC)`.
2. ✅ **Integrate into Scanner**: `MarketScanner` should filter out markets that are not `active` or `open`.
3. ⏳ **Integrate into Client**: `create_order` should (optionally) pre-validate that the market is open before sending the request to save API calls. (Future enhancement - not blocking)

## Acceptance Criteria
- [x] `MarketScanner` never returns a "Close Race" for a market that closed 5 minutes ago.
- [ ] Attempting to `create_order` on a closed market raises `MarketClosedError` locally (fail fast). **(Optional future work)**

## Implementation Notes (2026-01-09)

`MarketStatusVerifier` class implemented in `analysis/scanner.py` with:
- `is_market_tradeable(market)` - Checks status and close_time
- `verify_market_open(market)` - Raises `MarketClosedError` if not tradeable
- `filter_tradeable_markets(markets)` - Filters list

Scanner integration complete with tests:
- `test_excludes_closed_markets` verifies closed status filtered
- `test_is_market_tradeable_past_close_time` verifies timing checked
