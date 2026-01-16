# Kalshi OpenAPI Coverage Reference

**Type:** Internal reference (derived from Kalshi OpenAPI)
**Status:** Living Document
**Created:** 2026-01-13
**Source:** OpenAPI audit at `https://docs.kalshi.com/openapi.yaml`

---

## Purpose

This document is the **master reference** for Kalshi API endpoint coverage. It tracks:
- What endpoints exist in the OpenAPI spec
- What we've implemented
- What we need to implement (and which spec covers it)
- Our deliberate non-implementations (with reasoning)

---

## Coverage Summary

| Category | OpenAPI Ops | Implemented | Coverage | Spec |
|----------|-------------|-------------|----------|------|
| **Exchange** | 4 | 4 | **100%** | ✅ SPEC-040 Phase 4 |
| **Markets (Core)** | 5 | 5 | **100%** | Done |
| **Markets (Filters)** | 11 params | 11 params | **100%** | ✅ SPEC-040 Phase 1 |
| **Series** | 4 | 4 | **100%** | SPEC-037 Phase 1 ✅ |
| **Search/Discovery** | 2 | 2 | **100%** | ✅ SPEC-040 Phase 3 |
| **Events** | 6 | 5 | 83% | 🚫 Forecast history API blocked |
| **Structured Targets** | 2 | 2 | **100%** | ✅ SPEC-040 Phase 3 |
| **Portfolio (Read)** | 6 | 6 | **100%** | ✅ SPEC-040 Phase 2 |
| **Portfolio (Orders)** | 9 | 9 | **100%** | ✅ SPEC-040 Phase 2 |
| **Order Groups** | 5 | 5 | **100%** | ✅ SPEC-040 Phase 4 |
| **Subaccounts** | 4 | 0 | 0% | 🚫 API blocked (403/404) |
| **RFQ/Communications** | 11 | 0 | 0% | Not planned |
| **Milestones & Live Data** | 4 | 4 | **100%** | ✅ SPEC-040 Phase 4 |
| **Multivariate Collections** | 5 | 3 | 60% | ✅ SPEC-041 Phase 5 (partial) |
| **Incentive Programs** | 1 | 1 | **100%** | ✅ SPEC-040 Phase 4 |
| **API Keys** | 4 | 0 | 0% | Not planned |
| **FCM** | 2 | 0 | 0% | Not planned |
| **TOTAL** | 74 | 50 | **68%** | - |

---

## Complete Endpoint Matrix

### Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Implemented with golden fixture + tests |
| 🔲 | Planned - has spec coverage |
| ⬜ | Not planned - low priority |

---

### 1. Exchange & System (4 endpoints)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /exchange/status` | ✅ | Done | `get_exchange_status()` |
| `GET /exchange/announcements` | ✅ | SPEC-040 Phase 4 | `get_exchange_announcements()` |
| `GET /exchange/schedule` | ✅ | SPEC-040 Phase 4 | `get_exchange_schedule()` |
| `GET /exchange/user_data_timestamp` | ✅ | SPEC-040 Phase 4 | `get_user_data_timestamp()` |

---

### 2. Markets (5 core endpoints + 6 filter params)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /markets` | ✅ | Done | `get_markets()`, `get_all_markets()` |
| `GET /markets/{ticker}` | ✅ | Done | `get_market()` |
| `GET /markets/{ticker}/orderbook` | ✅ | Done | `get_orderbook()` |
| `GET /markets/trades` | ✅ | Done | `get_trades()` |
| `GET /markets/candlesticks` | ✅ | Done | `get_candlesticks()` |

**Filter Parameters (on `GET /markets`):** ✅ COMPLETE

| Parameter | Status | Spec | Notes |
|-----------|--------|------|-------|
| `status` | ✅ | Done | Filter by market status |
| `event_ticker` | ✅ | Done | Filter by event |
| `series_ticker` | ✅ | Done | Filter by series |
| `tickers` | ✅ | SPEC-040 Phase 1 | Batch lookup (comma-separated) |
| `min_*_ts` / `max_*_ts` | ✅ | SPEC-040 Phase 1 | Timestamp filters (6 params) |
| `mve_filter` | ✅ | Done | Multivariate filtering |

---

### 3. Series (4 endpoints) - ✅ COMPLETE

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /series` | ✅ | SPEC-037 Phase 1 | `get_series_list()` |
| `GET /series/{series_ticker}` | ✅ | SPEC-037 Phase 1 | `get_series()` |
| `GET /series/fee_changes` | ✅ | SPEC-037 Phase 1 | `get_series_fee_changes()` |
| `GET /series/{series_ticker}/markets/{ticker}/candlesticks` | ✅ | Done | `get_series_candlesticks()` |

---

### 4. Search & Discovery (2 endpoints)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /search/tags_by_categories` | ✅ | SPEC-037 Phase 1 | `get_tags_by_categories()` |
| `GET /search/filters_by_sport` | ✅ | SPEC-040 Phase 3 | `get_filters_by_sport()` |

---

### 5. Events (6 endpoints)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /events` | ✅ | Done | `get_events()`, `get_all_events()` |
| `GET /events/{event_ticker}` | ✅ | Done | `get_event()` |
| `GET /events/multivariate` | ✅ | Done | `get_multivariate_events*()` (MVEs excluded from `/events`) |
| `GET /events/{event_ticker}/metadata` | ✅ | SPEC-040 Phase 3 | `get_event_metadata()` |
| `GET /series/{series_ticker}/events/{ticker}/candlesticks` | ✅ | SPEC-040 Phase 3 | `get_event_candlesticks()` |
| `GET /series/{series_ticker}/events/{ticker}/forecast_percentile_history` | ⬜ | - | OpenAPI exists, but returned `400 bad_request` for all tested events (2026-01-15) |

---

### 6. Structured Targets (2 endpoints)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /structured_targets` | ✅ | SPEC-040 Phase 3 | `get_structured_targets()` |
| `GET /structured_targets/{structured_target_id}` | ✅ | SPEC-040 Phase 3 | `get_structured_target()` |

**Filter Parameters:**
- `type` (e.g., `PLAYER_STATS`, `GAME_EVENT`)
- `competition` (e.g., `NFL`, `NBA`, `EPL`)
- `page_size`, `cursor`

---

### 7. Portfolio - Read (6 endpoints)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /portfolio/balance` | ✅ | Done | `get_balance()` |
| `GET /portfolio/positions` | ✅ | Done | `get_positions()` |
| `GET /portfolio/orders` | ✅ | Done | `get_orders()` |
| `GET /portfolio/fills` | ✅ | Done | `get_fills()` |
| `GET /portfolio/settlements` | ✅ | Done | `get_settlements()` |
| `GET /portfolio/summary/total_resting_order_value` | ✅ | SPEC-040 Phase 2 | `get_total_resting_order_value()` (returns 403 on demo - prod-only permission) |

---

### 8. Portfolio - Orders (9 endpoints) ✅ COMPLETE

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `POST /portfolio/orders` | ✅ | Done | `create_order()` |
| `DELETE /portfolio/orders/{order_id}` | ✅ | Done | `cancel_order()` |
| `POST /portfolio/orders/{order_id}/amend` | ✅ | Done | `amend_order()` |
| `GET /portfolio/orders/{order_id}` | ✅ | SPEC-040 Phase 2 | `get_order()` |
| `POST /portfolio/orders/batched` | ✅ | SPEC-040 Phase 2 | `batch_create_orders()` |
| `DELETE /portfolio/orders/batched` | ✅ | SPEC-040 Phase 2 | `batch_cancel_orders()` |
| `POST /portfolio/orders/{order_id}/decrease` | ✅ | SPEC-040 Phase 2 | `decrease_order()` |
| `GET /portfolio/orders/{order_id}/queue_position` | ✅ | SPEC-040 Phase 2 | `get_order_queue_position()` |
| `GET /portfolio/orders/queue_positions` | ✅ | SPEC-040 Phase 2 | `get_orders_queue_positions()` |

---

### 9. Order Groups (5 endpoints)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /portfolio/order_groups` | ✅ | SPEC-040 Phase 4 | `get_order_groups()` |
| `POST /portfolio/order_groups/create` | ✅ | SPEC-040 Phase 4 | `create_order_group()` |
| `GET /portfolio/order_groups/{order_group_id}` | ✅ | SPEC-040 Phase 4 | `get_order_group()` |
| `DELETE /portfolio/order_groups/{order_group_id}` | ✅ | SPEC-040 Phase 4 | `delete_order_group()` |
| `PUT /portfolio/order_groups/{order_group_id}/reset` | ✅ | SPEC-040 Phase 4 | `reset_order_group()` |

---

### 10. Subaccounts (4 endpoints)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `POST /portfolio/subaccounts` | ⬜ | - | OpenAPI exists, but endpoint returned `404 page not found` in demo + prod (2026-01-15) |
| `GET /portfolio/subaccounts/balances` | ⬜ | - | Demo: `200` empty; Prod: `403 invalid_parameters` (“not available in production”) |
| `POST /portfolio/subaccounts/transfer` | ⬜ | - | OpenAPI exists, but endpoint returned `404 page not found` in demo + prod (2026-01-15) |
| `GET /portfolio/subaccounts/transfers` | ⬜ | - | Demo: `200` empty; Prod: `403 invalid_parameters` (“not available in production”) |

**Note:** External fiat/crypto deposits are NOT available via API (use Kalshi web UI).

---

### 11. Milestones & Live Data (4 endpoints)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /milestones` | ✅ | SPEC-040 Phase 4 | `get_milestones()` |
| `GET /milestones/{milestone_id}` | ✅ | SPEC-040 Phase 4 | `get_milestone()` |
| `GET /live_data/{type}/milestone/{milestone_id}` | ✅ | SPEC-040 Phase 4 | `get_milestone_live_data()` |
| `GET /live_data/batch` | ✅ | SPEC-040 Phase 4 | `get_live_data_batch()` |

---

### 12. Multivariate Collections (5 endpoints)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /multivariate_event_collections` | ✅ | SPEC-041 Phase 5 | `get_multivariate_event_collections()` |
| `GET /multivariate_event_collections/{collection_ticker}` | ✅ | SPEC-041 Phase 5 | `get_multivariate_event_collection()` |
| `POST /multivariate_event_collections/{collection_ticker}` | ⬜ | - | Auth required |
| `GET /multivariate_event_collections/{collection_ticker}/lookup` | ⬜ | - | Lookup history (low value) |
| `PUT /multivariate_event_collections/{collection_ticker}/lookup` | ✅ | SPEC-041 Phase 5 | `lookup_multivariate_event_collection_tickers()` |

---

### 13. RFQ / Communications (11 endpoints) - NOT PLANNED

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /communications/id` | ⬜ | Large block trades only |
| `GET /communications/rfqs` | ⬜ | Institutional use |
| `POST /communications/rfqs` | ⬜ | Institutional use |
| `GET /communications/rfqs/{rfq_id}` | ⬜ | Institutional use |
| `DELETE /communications/rfqs/{rfq_id}` | ⬜ | Institutional use |
| `GET /communications/quotes` | ⬜ | Institutional use |
| `POST /communications/quotes` | ⬜ | Institutional use |
| `GET /communications/quotes/{quote_id}` | ⬜ | Institutional use |
| `DELETE /communications/quotes/{quote_id}` | ⬜ | Institutional use |
| `PUT /communications/quotes/{quote_id}/accept` | ⬜ | Institutional use |
| `PUT /communications/quotes/{quote_id}/confirm` | ⬜ | Institutional use |

**Why not planned:** RFQ is for negotiating large block trades. Not relevant for research or retail automation.

---

### 14. API Keys (4 endpoints) - NOT PLANNED

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api_keys` | ⬜ | Manage via web UI |
| `POST /api_keys` | ⬜ | Manage via web UI |
| `POST /api_keys/generate` | ⬜ | Manage via web UI |
| `DELETE /api_keys/{api_key}` | ⬜ | Manage via web UI |

**Why not planned:** Key management is better done via web UI with proper RBAC.

---

### 15. FCM (2 endpoints) - NOT PLANNED

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /fcm/orders` | ⬜ | Institutional only |
| `GET /fcm/positions` | ⬜ | Institutional only |

**Why not planned:** FCM (Futures Commission Merchant) endpoints are for institutional clearing members.

---

### 16. Incentive Programs (1 endpoint)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /incentive_programs` | ✅ | SPEC-040 Phase 4 | `get_incentive_programs()` |

---

## Implementation Priority

### P1: Critical Path (SPEC-040 Phase 1–2)

- Market filters (`tickers`, `min_*_ts` / `max_*_ts`) to avoid the "fetch all" anti-pattern.
- Order operations (batch create/cancel, get order detail, decrease, queue positions, resting order total value).

### P2: Discovery Completeness (SPEC-040 Phase 3)

- Event metadata and event-level candlesticks.
- Sports discovery helpers (`/search/filters_by_sport`, structured targets).
- (Optional, auth) forecast percentile history.

### P3: Operational Nice-to-Have (SPEC-040 Phase 4)

- Exchange schedule/announcements/user_data_timestamp.
- Order groups, subaccounts (only if you use them).
- Milestones/live data and incentive programs (informational / alerts-driven).

---

## Confirmed API Limitations (Platform Design)

These are NOT bugs in our code - they are Kalshi platform limitations:

| Limitation | Confirmed Via | Our Workaround |
|------------|---------------|----------------|
| **No keyword/text search** | OpenAPI has no `/search?q=...` | Sync to local DB → SQL search |
| **MVEs excluded from `/events`** | OpenAPI docs | Use `/events/multivariate` (implemented) |
| **No deposits via API** | OpenAPI - no deposit endpoint | Use Kalshi web UI |

---

## Spec Coverage

| Spec | Scope | Status |
|------|-------|--------|
| **SPEC-040** | Complete Kalshi endpoint implementation plan (TDD, SSOT-driven) | Draft (Ready) |
| SPEC-029 | Strategic endpoint coverage (client + CLI) | Superseded by SPEC-040 |
| SPEC-037 | SSOT-driven implementation with fixtures | Superseded by SPEC-040 |

**All planned endpoints have spec coverage.** No new specs required.

---

## Cross-References

| Item | Relationship |
|------|--------------|
| **SPEC-040** | Consolidated endpoint implementation plan |
| SPEC-029 | Superseded strategy doc |
| SPEC-037 | Superseded phase doc |
| **DEBT-015** | Original missing endpoints list |
| **DEBT-020** | Discovery gaps (resolved by this work) |
| `kalshi-api-reference.md` | SSOT vendor docs |
