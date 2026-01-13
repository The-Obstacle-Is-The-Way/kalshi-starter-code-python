# DEBT-021: Kalshi API Coverage Master Reference

**Priority:** Reference Document (Tracks what needs implementing)
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
| **Exchange** | 4 | 1 | 25% | - |
| **Markets (Core)** | 5 | 5 | **100%** | Done |
| **Markets (Filters)** | 11 params | 3 params | 27% | SPEC-029 |
| **Series** | 4 | 4 | **100%** | SPEC-037 Phase 1 ✅ |
| **Search/Discovery** | 2 | 1 | 50% | - |
| **Events** | 6 | 2 | 33% | SPEC-037 Phase 2 |
| **Structured Targets** | 2 | 0 | 0% | SPEC-029 |
| **Portfolio (Read)** | 6 | 5 | 83% | Done |
| **Portfolio (Orders)** | 9 | 3 | 33% | SPEC-037 Phase 3 |
| **Order Groups** | 5 | 0 | 0% | SPEC-037 Phase 3 |
| **Subaccounts** | 4 | 0 | 0% | SPEC-037 Phase 4 |
| **RFQ/Communications** | 11 | 0 | 0% | Not planned |
| **Milestones & Live Data** | 4 | 0 | 0% | - |
| **Multivariate Collections** | 5 | 0 | 0% | - |
| **Incentive Programs** | 1 | 0 | 0% | - |
| **API Keys** | 4 | 0 | 0% | Not planned |
| **FCM** | 2 | 0 | 0% | Not planned |
| **TOTAL** | 74 | 21 | **28%** | - |

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
| `GET /exchange/announcements` | ⬜ | - | P3 - informational |
| `GET /exchange/schedule` | ⬜ | - | P3 - trading hours |
| `GET /exchange/user_data_timestamp` | ⬜ | - | P3 - rarely needed |

---

### 2. Markets (5 core endpoints + 6 filter params)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /markets` | ✅ | Done | `get_markets()`, `get_all_markets()` |
| `GET /markets/{ticker}` | ✅ | Done | `get_market()` |
| `GET /markets/{ticker}/orderbook` | ✅ | Done | `get_orderbook()` |
| `GET /markets/trades` | ✅ | Done | `get_trades()` |
| `GET /markets/candlesticks` | ✅ | Done | `get_candlesticks()` |

**Filter Parameters (on `GET /markets`):**

| Parameter | Status | Spec | Notes |
|-----------|--------|------|-------|
| `status` | ✅ | Done | Filter by market status |
| `event_ticker` | ✅ | Done | Filter by event |
| `series_ticker` | ✅ | Done | Filter by series |
| `tickers` | 🔲 | SPEC-029 | Batch lookup (comma-separated) |
| `min_*_ts` / `max_*_ts` | 🔲 | SPEC-029 | Timestamp filters (6 params) |
| `mve_filter` | 🔲 | SPEC-029 | Multivariate filtering |

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
| `GET /search/filters_by_sport` | ⬜ | - | P3 - sports-specific |

---

### 5. Events (6 endpoints)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /events` | ✅ | Done | `get_events()`, `get_all_events()` |
| `GET /events/{event_ticker}` | ✅ | Done | `get_event()` |
| `GET /events/multivariate` | 🔲 | **SPEC-037 Phase 2** | **P2 - Critical gap** |
| `GET /events/{event_ticker}/metadata` | 🔲 | SPEC-037 Phase 2 | P3 |
| `GET /series/{series_ticker}/events/{ticker}/candlesticks` | 🔲 | SPEC-029 | Event-level candlesticks |
| `GET /series/{series_ticker}/events/{ticker}/forecast_percentile_history` | ⬜ | - | P3 - auth required |

---

### 6. Structured Targets (2 endpoints)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /structured_targets` | 🔲 | SPEC-029 | P3 - sports props |
| `GET /structured_targets/{structured_target_id}` | 🔲 | SPEC-029 | P3 |

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
| `GET /portfolio/summary/total_resting_order_value` | 🔲 | SPEC-037 Phase 3 | P3 |

---

### 8. Portfolio - Orders (9 endpoints)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `POST /portfolio/orders` | ✅ | Done | `create_order()` |
| `DELETE /portfolio/orders/{order_id}` | ✅ | Done | `cancel_order()` |
| `POST /portfolio/orders/{order_id}/amend` | ✅ | Done | `amend_order()` |
| `GET /portfolio/orders/{order_id}` | 🔲 | SPEC-037 Phase 3 | Single order detail |
| `POST /portfolio/orders/batched` | 🔲 | **SPEC-037 Phase 3** | **P2 - Batch create** |
| `DELETE /portfolio/orders/batched` | 🔲 | **SPEC-037 Phase 3** | **P2 - Batch cancel** |
| `POST /portfolio/orders/{order_id}/decrease` | 🔲 | SPEC-037 Phase 3 | P2 |
| `GET /portfolio/orders/{order_id}/queue_position` | 🔲 | SPEC-037 Phase 3 | P2 |
| `GET /portfolio/orders/queue_positions` | 🔲 | SPEC-037 Phase 3 | P2 - Batch |

---

### 9. Order Groups (5 endpoints)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /portfolio/order_groups` | 🔲 | SPEC-037 Phase 3 | P3 |
| `POST /portfolio/order_groups/create` | 🔲 | SPEC-037 Phase 3 | P3 |
| `GET /portfolio/order_groups/{order_group_id}` | 🔲 | SPEC-037 Phase 3 | P3 |
| `DELETE /portfolio/order_groups/{order_group_id}` | 🔲 | SPEC-037 Phase 3 | P3 |
| `PUT /portfolio/order_groups/{order_group_id}/reset` | 🔲 | SPEC-037 Phase 3 | P3 |

---

### 10. Subaccounts (4 endpoints)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `POST /portfolio/subaccounts` | 🔲 | SPEC-037 Phase 4 | P3 |
| `GET /portfolio/subaccounts/balances` | 🔲 | SPEC-037 Phase 4 | P3 |
| `POST /portfolio/subaccounts/transfer` | 🔲 | SPEC-037 Phase 4 | Internal only |
| `GET /portfolio/subaccounts/transfers` | 🔲 | SPEC-037 Phase 4 | P3 |

**Note:** External fiat/crypto deposits are NOT available via API (use Kalshi web UI).

---

### 11. Milestones & Live Data (4 endpoints)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /milestones` | ⬜ | - | P3 |
| `GET /milestones/{milestone_id}` | ⬜ | - | P3 |
| `GET /live_data/{type}/milestone/{milestone_id}` | ⬜ | - | P3 |
| `GET /live_data/batch` | ⬜ | - | P3 |

---

### 12. Multivariate Collections (5 endpoints)

| Endpoint | Status | Spec | Notes |
|----------|--------|------|-------|
| `GET /multivariate_event_collections` | ⬜ | - | P3 |
| `GET /multivariate_event_collections/{collection_ticker}` | ⬜ | - | P3 |
| `POST /multivariate_event_collections/{collection_ticker}` | ⬜ | - | Auth required |
| `GET /multivariate_event_collections/{collection_ticker}/lookup` | ⬜ | - | P3 |
| `PUT /multivariate_event_collections/{collection_ticker}/lookup` | ⬜ | - | Auth required |

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
| `GET /incentive_programs` | ⬜ | - | P3 - bonus tracking |

---

## Implementation Priority

### P1: Next Up (SPEC-037 Phase 2)

| Endpoint | Why Critical |
|----------|--------------|
| `GET /events/multivariate` | MVEs excluded from `/events` - data incomplete |

### P2: High Value (SPEC-037 Phase 3)

| Endpoint | Why Valuable |
|----------|--------------|
| `POST /portfolio/orders/batched` | 10x more efficient for market making |
| `DELETE /portfolio/orders/batched` | Efficient order cleanup |
| `GET /portfolio/orders/{order_id}/queue_position` | Market making edge |
| `POST /portfolio/orders/{order_id}/decrease` | Order management |
| Market timestamp filters (`min_*_ts`) | Avoid "fetch all" pattern |

### P3: Nice to Have (SPEC-029)

- Structured targets
- Milestones
- Exchange schedule/announcements
- Order groups
- Subaccounts

---

## Confirmed API Limitations (Platform Design)

These are NOT bugs in our code - they are Kalshi platform limitations:

| Limitation | Confirmed Via | Our Workaround |
|------------|---------------|----------------|
| **No keyword/text search** | OpenAPI has no `/search?q=...` | Sync to local DB → SQL search |
| **MVEs excluded from `/events`** | OpenAPI docs | Implement `/events/multivariate` |
| **No deposits via API** | OpenAPI - no deposit endpoint | Use Kalshi web UI |

---

## Spec Coverage

| Spec | Scope | Status |
|------|-------|--------|
| **SPEC-029** | Strategic endpoint coverage (client + CLI) | Draft |
| **SPEC-037** | SSOT-driven implementation with fixtures | Phase 1 ✅, Phases 2-4 pending |

**All planned endpoints have spec coverage.** No new specs required.

---

## Cross-References

| Item | Relationship |
|------|--------------|
| **SPEC-029** | Strategic coverage plan |
| **SPEC-037** | SSOT implementation pattern (phases) |
| **DEBT-015** | Original missing endpoints list |
| **DEBT-020** | Discovery gaps (resolved by this work) |
| `kalshi-api-reference.md` | SSOT vendor docs |
