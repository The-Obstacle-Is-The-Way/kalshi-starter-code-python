# DEBT-015: Missing API Endpoints

**Priority:** P3 (Nice-to-have - critical paths complete)
**Status:** Mostly Resolved (Phase 1-3 Complete)
**Found:** 2026-01-12
**Verified:** 2026-01-12 - Confirmed endpoints missing from `api/client.py`
**Updated:** 2026-01-15 - Phase 3 (Discovery) complete via SPEC-040
**Source:** Audit against `docs/_vendor-docs/kalshi-api-reference.md`

---

## Summary

The Kalshi API client was missing 45+ documented endpoints. **Phases 1-3 are now complete (34/74 = 46% coverage).** Remaining gaps are P3 (nice-to-have):
- ~~Category/tag discovery (proper market browsing)~~ ✅ DONE
- ~~Series-based filtering (Kalshi's intended pattern)~~ ✅ DONE
- ~~Batch order operations~~ ✅ DONE (SPEC-040 Phase 2)
- ~~Queue position monitoring~~ ✅ DONE (SPEC-040 Phase 2)
- ~~Event metadata, structured targets, sports filters~~ ✅ DONE (SPEC-040 Phase 3)
- Order groups (batch management)
- RFQ system (large block trades) - NOT PLANNED (institutional only)
- Live data feeds

**Status update (2026-01-15):**
- ✅ **SPEC-040 Phase 1 Complete**: Market filter parameters (`tickers`, timestamp filters)
- ✅ **SPEC-040 Phase 2 Complete**: Order operations (batch create/cancel, get order, decrease, queue positions, resting value)
- ✅ **SPEC-040 Phase 3 Complete**: Discovery endpoints (event metadata, event candlesticks, filters by sport, structured targets)
- 🔲 Phase 4 (Operational) remains for future work

---

## Missing Endpoint Categories

### 1. Exchange & System (4 endpoints) - P3

| Endpoint | Description | Priority | Status |
|----------|-------------|----------|--------|
| `GET /exchange/announcements` | Exchange-wide announcements | P3 | Missing |
| `GET /exchange/schedule` | Trading schedule | P3 | Missing |
| `GET /series/fee_changes` | Series fee change schedule | P3 | ✅ **DONE** |
| `GET /exchange/user_data_timestamp` | User data timestamp | P3 | Missing |

**Impact:** Low - informational only
**Note:** `GET /series/fee_changes` implemented in SPEC-037 (`get_series_fee_changes()`)

### 2. Series Endpoints (3 endpoints) - ✅ MOSTLY DONE

| Endpoint | Description | Priority | Status |
|----------|-------------|----------|--------|
| `GET /series` | List series with filters | **P2** | ✅ **DONE** |
| `GET /series/{series_ticker}` | Single series details | P2 | ✅ **DONE** |
| `GET /series/{series_ticker}/events/{ticker}/forecast_percentile_history` | Forecast history (auth) | P3 | Missing |

**Impact:** ~~Medium~~ **Resolved** - Series-centric navigation now available via:
- `get_series_list()` - List all series with optional category filter
- `get_series()` - Get single series details
- `get_series_candlesticks()` - Historical price data for series

**Implemented:** SPEC-037 (2026-01-12)

### 3. Search & Discovery (2 endpoints) - ✅ PARTIALLY DONE

| Endpoint | Description | Priority | Status |
|----------|-------------|----------|--------|
| `GET /search/tags_by_categories` | Category → tags mapping | **P2** | ✅ **DONE** |
| `GET /search/filters_by_sport` | Sports-specific filters | P3 | Missing |

**Impact:** ~~Medium~~ **Resolved** - Category browsing now available via `get_tags_by_categories()`

**Implemented:** SPEC-037 (2026-01-12)

### 4. Structured Targets (2 endpoints) - P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /structured_targets` | List structured targets (filters: `type`, `competition`) | P3 |
| `GET /structured_targets/{structured_target_id}` | Structured target details | P3 |

**Impact:** Low - Advanced market mechanics only
**Note:** SSOT reference: `docs/_vendor-docs/kalshi-api-reference.md` documents filter params (`type`, `competition`).

### 5. Milestones & Live Data (4 endpoints) - P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /milestones` | List milestones | P3 |
| `GET /milestones/{milestone_id}` | Milestone details | P3 |
| `GET /live_data/{type}/milestone/{milestone_id}` | Live data for milestone | P3 |
| `GET /live_data/batch` | Batch live data | P3 |

**Impact:** Low - Used for real-time event tracking

### 6. Order Management Advanced (7 endpoints) - ✅ COMPLETE

| Endpoint | Description | Priority | Status |
|----------|-------------|----------|--------|
| `POST /portfolio/orders/batched` | Batch create up to 20 orders | **P2** | ✅ **DONE** |
| `DELETE /portfolio/orders/batched` | Cancel orders in batch | P2 | ✅ **DONE** |
| `POST /portfolio/orders/{order_id}/decrease` | Decrease order size | P2 | ✅ **DONE** |
| `GET /portfolio/orders/{order_id}` | Single order details | P2 | ✅ **DONE** |
| `GET /portfolio/orders/{order_id}/queue_position` | Queue position for one order | P2 | ✅ **DONE** |
| `GET /portfolio/orders/queue_positions` | Queue positions for multiple | P2 | ✅ **DONE** |
| `GET /portfolio/summary/total_resting_order_value` | Total resting order value | P3 | ✅ **DONE** |

**Impact:** ~~Medium~~ **Resolved** - All order operations implemented via SPEC-040 Phase 2 (2026-01-14)

**Note:** Phase 2 fixtures are recorded against the real demo API (including 403 fixtures where the endpoint is permissioned). Client methods are tested against expected schema.

### 7. Order Groups (5 endpoints) - P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /portfolio/order_groups` | List order groups | P3 |
| `POST /portfolio/order_groups/create` | Create order group | P3 |
| `GET /portfolio/order_groups/{order_group_id}` | Get order group details | P3 |
| `DELETE /portfolio/order_groups/{order_group_id}` | Delete order group | P3 |
| `PUT /portfolio/order_groups/{order_group_id}/reset` | Reset order group | P3 |

**Impact:** Low - Advanced order management

### 8. RFQ / Communications System (11 endpoints) - P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /communications/id` | Get communications ID | P3 |
| `POST /communications/rfqs` | Create RFQ | P3 |
| `GET /communications/rfqs` | List RFQs | P3 |
| `GET /communications/rfqs/{rfq_id}` | RFQ details | P3 |
| `DELETE /communications/rfqs/{rfq_id}` | Delete RFQ | P3 |
| `POST /communications/quotes` | Create quote | P3 |
| `GET /communications/quotes` | List quotes | P3 |
| `GET /communications/quotes/{quote_id}` | Quote details | P3 |
| `DELETE /communications/quotes/{quote_id}` | Delete quote | P3 |
| `PUT /communications/quotes/{quote_id}/accept` | Accept quote | P3 |
| `PUT /communications/quotes/{quote_id}/confirm` | Confirm quote | P3 |

**Impact:** Low for research use - RFQ is for large block trades

### 9. Multivariate Event Collections (5 endpoints) - P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /multivariate_event_collections` | List collections | P3 |
| `GET /multivariate_event_collections/{collection_ticker}` | Collection details | P3 |
| `POST /multivariate_event_collections/{collection_ticker}` | Create/update | P3 |
| `GET /multivariate_event_collections/{collection_ticker}/lookup` | Lookup tickers | P3 |
| `PUT /multivariate_event_collections/{collection_ticker}/lookup` | Update lookup | P3 |

**Impact:** Low - Sports parlay combinations

### 10. API Key Management (4 endpoints) - P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /api_keys` | List API keys | P3 |
| `POST /api_keys` | Create API key | P3 |
| `POST /api_keys/generate` | Generate new key | P3 |
| `DELETE /api_keys/{api_key}` | Delete API key | P3 |

**Impact:** Low - Can manage via web UI

### 11. FCM (2 endpoints) - P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /fcm/orders` | FCM orders | P3 |
| `GET /fcm/positions` | FCM positions | P3 |

**Impact:** Low - Institutional only

### 12. Event Metadata & MVEs (2 endpoints) - P2/P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /events/{event_ticker}/metadata` | Event metadata | P3 |
| `GET /events/multivariate` | Multivariate events only | **P2** ✅ **DONE** |

**Impact:** `/events/multivariate` is **P2 critical** - MVEs excluded from `/events` endpoint (data incomplete without it). Metadata is P3.

---

## Recommended Implementation Order

### Phase 1: Market Filters (P2) - ✅ COMPLETE
- ~~`tickers` parameter~~ ✅ Batch market lookup
- ~~Timestamp filters (`min_*_ts`, `max_*_ts`)~~ ✅ 6 params implemented
- Client-side validation for incompatible filter combinations

**Implemented:** SPEC-040 Phase 1 (2026-01-14)

### Phase 1 (Legacy): Category Discovery (P2) - ✅ COMPLETE
1. ~~`GET /search/tags_by_categories`~~ ✅ `get_tags_by_categories()`
2. ~~`GET /series`~~ ✅ `get_series_list()`
3. ~~`GET /series/{ticker}`~~ ✅ `get_series()`
4. ~~`GET /series/fee_changes`~~ ✅ `get_series_fee_changes()`

**Implemented:** SPEC-037 (2026-01-12)

### Phase 2: Order Efficiency (P2) - ✅ COMPLETE
1. ~~`POST /portfolio/orders/batched`~~ ✅ `batch_create_orders()` - 10x more efficient
2. ~~`DELETE /portfolio/orders/batched`~~ ✅ `batch_cancel_orders()` - Batch cancel
3. ~~`GET /portfolio/orders/{order_id}`~~ ✅ `get_order()` - Single order detail
4. ~~`POST /portfolio/orders/{order_id}/decrease`~~ ✅ `decrease_order()` - Order management
5. ~~`GET /portfolio/orders/{order_id}/queue_position`~~ ✅ `get_order_queue_position()` - Market making
6. ~~`GET /portfolio/orders/queue_positions`~~ ✅ `get_orders_queue_positions()` - Batch queue positions
7. ~~`GET /portfolio/summary/total_resting_order_value`~~ ✅ `get_total_resting_order_value()`

**Implemented:** SPEC-040 Phase 2 (2026-01-14)

### Phase 3: Discovery (P3) - ✅ COMPLETE (except optional auth-only forecast history)
- ~~`GET /events/{event_ticker}/metadata`~~ ✅ `get_event_metadata()`
- ~~`GET /structured_targets`~~ ✅ `get_structured_targets()`
- ~~`GET /structured_targets/{structured_target_id}`~~ ✅ `get_structured_target()`
- ~~`GET /search/filters_by_sport`~~ ✅ `get_filters_by_sport()`
- ~~`GET /series/{series_ticker}/events/{event_ticker}/candlesticks`~~ ✅ `get_event_candlesticks()`
- `GET /series/{series_ticker}/events/{event_ticker}/forecast_percentile_history` 🔲 (auth required; optional)

### Phase 4: Operational (P3) - ✅ COMPLETE
- ~~Exchange schedule/announcements/user_data_timestamp~~ ✅ `get_exchange_schedule()`, `get_exchange_announcements()`, `get_user_data_timestamp()`
- ~~Order groups~~ ✅ `get_order_groups()`, `create_order_group()`, `get_order_group()`, `reset_order_group()`, `delete_order_group()`
- ~~Milestones/live data~~ ✅ `get_milestones()`, `get_milestone()`, `get_milestone_live_data()`, `get_live_data_batch()`
- ~~Incentive programs~~ ✅ `get_incentive_programs()`

---

## Relationship to Other Debt/Bugs

- **DEBT-014 Section C1**: Tracks the `/series` endpoint work; now ✅ resolved via SPEC-037 (kept for context)
- **BUG-064**: Missing order safety parameters (different issue - params vs endpoints)

---

## Cross-References

| Item | Relationship |
|------|--------------|
| DEBT-014 C1 | Series endpoint subset |
| BUG-064 | Order params (not endpoints) |
| `docs/_vendor-docs/kalshi-api-reference.md` | SSOT for API |
