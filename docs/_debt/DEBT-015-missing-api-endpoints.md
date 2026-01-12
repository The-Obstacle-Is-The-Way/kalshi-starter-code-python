# DEBT-015: Missing API Endpoints

**Priority:** P2-P3 (Non-blocking but limiting)
**Status:** Open
**Found:** 2026-01-12
**Verified:** 2026-01-12 - Confirmed endpoints missing from `api/client.py`
**Source:** Audit against `docs/_vendor-docs/kalshi-api-reference.md`

---

## Summary

The Kalshi API client is missing 45+ documented endpoints. While the core trading and research functionality works, these gaps limit advanced features like:
- Category/tag discovery (proper market browsing)
- Series-based filtering (Kalshi's intended pattern)
- Order groups (batch management)
- RFQ system (large block trades)
- Queue position monitoring
- Live data feeds

---

## Missing Endpoint Categories

### 1. Exchange & System (4 endpoints) - P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /exchange/announcements` | Exchange-wide announcements | P3 |
| `GET /exchange/schedule` | Trading schedule | P3 |
| `GET /series/fee_changes` | Series fee change schedule | P3 |
| `GET /exchange/user_data_timestamp` | User data timestamp | P3 |

**Impact:** Low - informational only

### 2. Series Endpoints (4 endpoints) - P2

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /series` | List series with filters | **P2** |
| `GET /series/{series_ticker}` | Single series details | P2 |
| `GET /series/{series_ticker}/events/{ticker}/forecast_percentile_history` | Forecast history (auth) | P3 |

**Impact:** Medium - This is Kalshi's intended category filtering pattern:
1. `GET /search/tags_by_categories` → Discover categories
2. `GET /series?category=Politics` → Get series in category
3. `GET /markets?series_ticker=...` → Get markets

Currently we use `/events` which works but is deprecated pattern.

### 3. Search & Discovery (2 endpoints) - P2

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /search/tags_by_categories` | Category → tags mapping | **P2** |
| `GET /search/filters_by_sport` | Sports-specific filters | P3 |

**Impact:** Medium - Can't build proper category filter UIs

### 4. Structured Targets (2 endpoints) - P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /structured_targets` | List structured targets | P3 |
| `GET /structured_targets/{id}` | Structured target details | P3 |

**Impact:** Low - Advanced market mechanics only

### 5. Milestones & Live Data (4 endpoints) - P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /milestones` | List milestones | P3 |
| `GET /milestones/{id}` | Milestone details | P3 |
| `GET /live_data/{type}/milestone/{id}` | Live data for milestone | P3 |
| `GET /live_data/batch` | Batch live data | P3 |

**Impact:** Low - Used for real-time event tracking

### 6. Order Management Advanced (6 endpoints) - P2

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `POST /portfolio/orders/batched` | Batch create up to 20 orders | **P2** |
| `POST /portfolio/orders/{id}/decrease` | Decrease order size | P2 |
| `GET /portfolio/orders/{id}` | Single order details | P2 |
| `GET /portfolio/orders/{id}/queue_position` | Queue position for one order | P2 |
| `GET /portfolio/orders/queue_positions` | Queue positions for multiple | P2 |
| `GET /portfolio/summary/total_resting_order_value` | Total resting order value | P3 |

**Impact:** Medium - Batch orders are 10x more efficient for market making

### 7. Order Groups (5 endpoints) - P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /portfolio/order_groups` | List order groups | P3 |
| `POST /portfolio/order_groups/create` | Create order group | P3 |
| `GET /portfolio/order_groups/{id}` | Get order group details | P3 |
| `DELETE /portfolio/order_groups/{id}` | Delete order group | P3 |
| `PUT /portfolio/order_groups/{id}/reset` | Reset order group | P3 |

**Impact:** Low - Advanced order management

### 8. RFQ / Communications System (11 endpoints) - P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /communications/id` | Get communications ID | P3 |
| `POST /communications/rfqs` | Create RFQ | P3 |
| `GET /communications/rfqs` | List RFQs | P3 |
| `GET /communications/rfqs/{id}` | RFQ details | P3 |
| `DELETE /communications/rfqs/{id}` | Delete RFQ | P3 |
| `POST /communications/quotes` | Create quote | P3 |
| `GET /communications/quotes` | List quotes | P3 |
| `GET /communications/quotes/{id}` | Quote details | P3 |
| `DELETE /communications/quotes/{id}` | Delete quote | P3 |
| `PUT /communications/quotes/{id}/accept` | Accept quote | P3 |
| `PUT /communications/quotes/{id}/confirm` | Confirm quote | P3 |

**Impact:** Low for research use - RFQ is for large block trades

### 9. Multivariate Event Collections (5 endpoints) - P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /multivariate_event_collections` | List collections | P3 |
| `GET /multivariate_event_collections/{ticker}` | Collection details | P3 |
| `POST /multivariate_event_collections/{ticker}` | Create/update | P3 |
| `GET /multivariate_event_collections/{ticker}/lookup` | Lookup tickers | P3 |
| `PUT /multivariate_event_collections/{ticker}/lookup` | Update lookup | P3 |

**Impact:** Low - Sports parlay combinations

### 10. API Key Management (4 endpoints) - P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /api_keys` | List API keys | P3 |
| `POST /api_keys` | Create API key | P3 |
| `POST /api_keys/generate` | Generate new key | P3 |
| `DELETE /api_keys/{id}` | Delete API key | P3 |

**Impact:** Low - Can manage via web UI

### 11. FCM (2 endpoints) - P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /fcm/orders` | FCM orders | P3 |
| `GET /fcm/positions` | FCM positions | P3 |

**Impact:** Low - Institutional only

### 12. Event Metadata (2 endpoints) - P3

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `GET /events/{ticker}/metadata` | Event metadata | P3 |
| `GET /events/multivariate` | Multivariate events only | P3 |

**Impact:** Low - Specialized queries

---

## Recommended Implementation Order

### Phase 1: Category Discovery (P2) - High Value
1. `GET /search/tags_by_categories` - Enable proper category browsing
2. `GET /series` - Kalshi's intended filtering pattern
3. `GET /series/{ticker}` - Series details

### Phase 2: Order Efficiency (P2)
4. `POST /portfolio/orders/batched` - 10x more efficient
5. `GET /portfolio/orders/{id}/queue_position` - Market making
6. `POST /portfolio/orders/{id}/decrease` - Order management

### Phase 3: Everything Else (P3)
- Implement as needed

---

## Relationship to Other Debt/Bugs

- **DEBT-014 Section C1**: Already tracks "Missing `/series` endpoint" as blocked
- **BUG-064**: Missing order safety parameters (different issue - params vs endpoints)

---

## Cross-References

| Item | Relationship |
|------|--------------|
| DEBT-014 C1 | Series endpoint subset |
| BUG-064 | Order params (not endpoints) |
| `docs/_vendor-docs/kalshi-api-reference.md` | SSOT for API |
