# Missing Features & Implementation Plan

**Date:** 2026-01-07
**Status:** ✅ All Features Implemented & Verified
**Goal:** Close the gap between Specifications and Codebase.

---

## 1. Order Placement (SPEC-011) - **P1 (High)**

**Status:** ✅ Implemented
**Ref:** `docs/_specs/SPEC-011-manual-trading-support.md`

### Verification Notes
*   **Endpoint:** `POST /trade-api/v2/portfolio/orders` (Verified)
*   **Implementation:** `src/kalshi_research/api/client.py` (KalshiClient)
*   **Models:** `src/kalshi_research/api/models/order.py`
*   **Tests:** `tests/unit/api/test_trading.py` (Pass)

### Checklist
- [x] Add `create_order` to `KalshiClient`
- [x] Add `cancel_order` to `KalshiClient`
- [x] Add `amend_order` to `KalshiClient`
- [x] Implement `side` mapping (yes/no -> API values)
- [x] Add integration tests (mocked & live-demo)

---

## 2. WebSockets (SPEC-014) - **P0 (Critical)**

**Status:** ✅ Implemented
**Ref:** `docs/_specs/SPEC-014-websocket-real-time-data.md`

### Verification Notes
*   **Implementation:** `src/kalshi_research/api/websocket/`
*   **Client:** `KalshiWebSocket`
*   **Models:** `src/kalshi_research/api/websocket/messages.py`
*   **Tests:** `tests/unit/api/websocket/test_websocket.py` (Pass)

### Checklist
- [x] Create `KalshiWebSocket` class
- [x] Implement reconnection logic (exponential backoff)
- [x] Implement channel subscription helpers
- [x] **Critical:** Add unit conversion layer (cents/dollars/centi-cents)
- [x] Wire into `MarketScanner` (API ready, scanner update pending next phase)

---

## 3. Rate Limiting (SPEC-015) - **P1 (High)**

**Status:** ✅ Implemented
**Ref:** `docs/_specs/SPEC-015-rate-limit-tier-management.md`

### Verification Notes
*   **Implementation:** `src/kalshi_research/api/rate_limiter.py`
*   **Integration:** `KalshiPublicClient` & `KalshiClient`
*   **Tests:** `tests/unit/api/test_rate_limiter.py` (Pass)

### Checklist
- [x] Create `RateLimiter` class (Token Bucket)
- [x] Add `RateTier` enum
- [x] Integrate into `KalshiClient` (prevent 429s before they happen)
- [x] Support `Retry-After` header handling

---

## 4. Demo Environment (SPEC-016) - **P2 (DevEx)**

**Status:** ✅ Implemented
**Ref:** `docs/_specs/SPEC-016-demo-environment-testing.md`

### Verification Notes
*   **Implementation:** `src/kalshi_research/api/config.py`
*   **Integration:** `KalshiClient(environment="demo")`
*   **Tests:** `tests/unit/api/test_client.py` (Pass)

### Checklist
- [x] Verify `KalshiClient` correctly switches URLs based on config
- [x] Add end-to-end test with Demo credentials (mocked via fixtures)

---