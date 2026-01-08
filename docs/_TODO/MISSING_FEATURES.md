# Missing Features & Implementation Plan

**Date:** 2026-01-07
**Status:** Validated against Official Kalshi Docs
**Goal:** Close the gap between Specifications and Codebase.

---

## 1. Order Placement (SPEC-011) - **P1 (High)**

**Status:** ❌ Missing
**Ref:** `docs/_specs/SPEC-011-manual-trading-support.md`

### Verification Notes
*   **Endpoint:** `POST /trade-api/v2/portfolio/orders` (Verified)
*   **Parameter Mapping:**
    *   **Side:** The API expects `'yes'` (or 1) / `'no'` (or 2). The Python client should handle the abstraction `Literal["yes", "no"]` -> API value.
    *   **Price:** Must be in **cents** (1-99). Client must validate this to prevent user error (e.g. entering 0.50 instead of 50).
    *   **Count:** Integer number of contracts.
*   **Auth:** Requires strict request signing (already implemented in `Auth` class, need to verify it works for POST bodies).

### Implementation Checklist
- [ ] Add `create_order` to `KalshiClient`
- [ ] Add `cancel_order` to `KalshiClient`
- [ ] Add `amend_order` to `KalshiClient`
- [ ] Implement `side` mapping (yes/no -> API values)
- [ ] Add integration tests (mocked & live-demo)

---

## 2. WebSockets (SPEC-014) - **P0 (Critical)**

**Status:** ❌ Missing
**Ref:** `docs/_specs/SPEC-014-websocket-real-time-data.md`

### Verification Notes
*   **URLs:**
    *   Prod: `wss://api.elections.kalshi.com/trade-api/ws/v2`
    *   Demo: `wss://demo-api.kalshi.co/trade-api/ws/v2`
*   **Auth:** Handshake requires `KALSHI-ACCESS-KEY`, `KALSHI-ACCESS-SIGNATURE`, `KALSHI-ACCESS-TIMESTAMP` headers.
*   **Signing:** Signature string is `timestamp + "GET" + "/trade-api/ws/v2"`.
*   **Channels:** `ticker`, `orderbook_delta`, `trade`.
*   **Units:** **CRITICAL:** WebSocket price data units vary by channel (cents vs dollars vs centi-cents). Strict typing and conversion helpers are required.

### Implementation Checklist
- [ ] Create `KalshiWebSocket` class
- [ ] Implement reconnection logic (exponential backoff)
- [ ] Implement channel subscription helpers
- [ ] **Critical:** Add unit conversion layer (dont mix up cents/dollars!)
- [ ] Wire into `MarketScanner` to replace REST polling

---

## 3. Rate Limiting (SPEC-015) - **P1 (High)**

**Status:** ❌ Missing
**Ref:** `docs/_specs/SPEC-015-rate-limit-tier-management.md`

### Verification Notes
*   **Limits:**
    *   Basic: 20 read / 10 write (Default)
    *   Advanced: 30 read / 30 write
    *   Premier: 100 read / 100 write
    *   Prime: 400 read / 400 write
*   **Write Costs:** `BatchCancelOrders` counts as 0.2 transactions per item.
*   **Headers:** API returns `Retry-After` on 429s.

### Implementation Checklist
- [ ] Create `RateLimiter` class (Token Bucket)
- [ ] Add `RateTier` enum
- [ ] Integrate into `KalshiClient` (prevent 429s before they happen)
- [ ] Support `Retry-After` header handling

---

## 4. Demo Environment (SPEC-016) - **Partially Implemented**

**Status:** ⚠️ Partial
**Ref:** `docs/_specs/SPEC-016-demo-environment-testing.md`

### Verification Notes
*   **Base URL:** `https://demo-api.kalshi.co/trade-api/v2` (Verified)
*   **Current State:**
    *   `APIConfig` exists and has correct URLs.
    *   `--env` flag exists.
    *   **Gap:** Need to verify end-to-end connectivity with a real demo key.

### Implementation Checklist
- [ ] Verify `KalshiClient` correctly switches URLs based on config
- [ ] Add end-to-end test with Demo credentials (if available)

---

**Next Step:** Pause for user approval.
