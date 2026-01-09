# TODO-007: Market Timing Safety Mechanism

## Problem
The system currently lacks a centralized "Market Timing" authority. It is possible to:
1. Recommend a trade on a CLOSED market.
2. Calculate "edge" on a market that has already SETTLED.
3. Attempt to fetch orderbooks for EXPIRED markets.

This is documented as a P2 risk in the codebase audit.

## Objectives
1. **Create `MarketStatusVerifier`**: A service that checks `market.status`, `market.close_time`, and `market.expiration_time` against `datetime.now(UTC)`.
2. **Integrate into Scanner**: `MarketScanner` should filter out markets that are not `active` or `open`.
3. **Integrate into Client**: `create_order` should (optionally) pre-validate that the market is open before sending the request to save API calls.

## Acceptance Criteria
- [ ] `MarketScanner` never returns a "Close Race" for a market that closed 5 minutes ago.
- [ ] Attempting to `create_order` on a closed market raises `MarketClosedError` locally (fail fast).
