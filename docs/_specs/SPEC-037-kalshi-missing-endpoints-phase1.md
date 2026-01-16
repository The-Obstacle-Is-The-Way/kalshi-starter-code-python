# SPEC-037: Kalshi Missing Endpoints (Discovery + Order Ops Parity)

**Status:** 🔀 Superseded by [SPEC-040](../_archive/specs/SPEC-040-kalshi-endpoint-implementation-complete.md) (complete)
**Priority:** P1 (Foundation robustness for discovery + safe automation)
**Created:** 2026-01-12
**Owner:** Solo
**Related:** `docs/_debt/DEBT-015-missing-api-endpoints.md`, `docs/_archive/future/TODO-00A-api-verification-post-deadline.md`

---

## Summary

Kalshi’s OpenAPI spec contains many endpoints that we do not currently implement. Some are required for “first-class”
discovery (category → series → markets) and safe automation (batch orders, queue position, exchange schedule).

This spec defines an **ironclad, SSOT-driven** way to add the missing endpoints we actually need soon:

- **Discovery parity**: categories/tags, series listing/detail, MVEs, structured browsing primitives.
- **Order-ops parity** (for the TradeExecutor + future agents): batched orders, queue position, decrease, order groups.
- **SSOT enforcement**: every endpoint we add must ship with:
  - **golden fixture(s)** captured from the real API (prod when safe; demo only when the endpoint is write-only),
  - `scripts/validate_models_against_golden.py` coverage,
  - unit tests that load fixtures rather than hand-written mock dicts.

---

## SSOT

1. Kalshi OpenAPI spec: `https://docs.kalshi.com/openapi.yaml`
2. Local vendor reference: `docs/_vendor-docs/kalshi-api-reference.md`
3. Code: `src/kalshi_research/api/client.py`, `src/kalshi_research/api/models/`
4. Golden fixtures: `tests/fixtures/golden/*.json` + `_recording_summary.json`

---

## Current State (What We Already Cover)

We already have golden fixtures + model validation for:

- Markets: `GET /markets`, `GET /markets/{ticker}`, `GET /markets/{ticker}/orderbook`
- Time series: `GET /markets/trades`, `GET /markets/candlesticks`, `GET /series/{series_ticker}/markets/{ticker}/candlesticks`
- Events: `GET /events`, `GET /events/{event_ticker}`
- Exchange: `GET /exchange/status`
- Portfolio (core): `GET /portfolio/balance`, `GET /portfolio/positions`, `GET /portfolio/orders`, `GET /portfolio/fills`,
  `GET /portfolio/settlements`
- Orders (core): `POST /portfolio/orders`, `DELETE /portfolio/orders/{order_id}`, `POST /portfolio/orders/{order_id}/amend`

SSOT check: `uv run python scripts/validate_models_against_golden.py`

---

## Scope (What We Add Next)

This spec focuses on missing endpoints from Kalshi OpenAPI that directly support:

1. **Category/series-first discovery** (unblocks proper browsing + topic discovery without “fetch everything then filter”).
2. **Order lifecycle operations** needed for TradeExecutor + future agent safety rails.

Everything else remains P3 unless/until a workflow demands it.

---

## Key Constraint: Jan 15, 2026 Deprecations

Kalshi has a known deadline (Jan 15, 2026) for removing cent-denominated price fields. Do not treat pre-deadline data
as proof that post-deadline parsing is correct.

Follow: `docs/_archive/future/TODO-00A-api-verification-post-deadline.md`

This spec is **endpoint parity**, not the cent→dollar migration itself. Still, any new models must follow the same
“dollars-first with cents fallback” conventions used elsewhere.

---

## Implementation Strategy (Repeatable Pattern)

For each endpoint added:

1. Add/extend Pydantic models in `src/kalshi_research/api/models/` (match OpenAPI schema names/fields).
2. Add `KalshiClient` method(s) in `src/kalshi_research/api/client.py`:
   - unwrap the documented response wrapper key (SSOT: OpenAPI schema),
   - return typed models (never raw dicts).
3. Record golden fixture(s):
   - Prefer **prod** for read-only endpoints.
   - For write-only endpoints, use **demo** (or a dedicated “fixture account”) with explicit, reversible actions.
4. Update `scripts/validate_models_against_golden.py` mapping for the new fixture(s).
5. Add/extend unit tests:
   - model-validate fixtures (`tests/unit/api/test_golden_fixtures.py`),
   - client uses correct wrapper keys (`tests/unit/api/test_client*.py` using `respx` + fixtures).

Acceptance is purely SSOT-based: fixtures + model validation must pass.

---

## Phase 1 (P2): Category + Series Discovery (High Leverage) - ✅ COMPLETE

**Implemented:** 2026-01-12

### 1.1 `GET /search/tags_by_categories` ✅

Purpose: discover valid Kalshi categories and their tags (enables a real category UI).

- OpenAPI response schema: `GetTagsForSeriesCategoriesResponse`
  - wrapper key: `tags_by_categories` (object)
- ✅ Model: `src/kalshi_research/api/models/search.py`
- ✅ Client method: `get_tags_by_categories()` in `src/kalshi_research/api/client.py`
- ✅ Fixture: `tests/fixtures/golden/tags_by_categories_response.json`
- ✅ Tests: golden fixture validation + client unit test

### 1.2 `GET /series` and `GET /series/{series_ticker}` ✅

Purpose: implement Kalshi's intended browse pattern:

1) `GET /search/tags_by_categories` → categories/tags
2) `GET /series?category=...` → series
3) `GET /markets?series_ticker=...` → markets

- ✅ Models: `src/kalshi_research/api/models/series.py`
  - `Series`, `SeriesListResponse`, `SeriesResponse`
- ✅ Client methods:
  - `get_series_list()` in `src/kalshi_research/api/client.py`
  - `get_series()` in `src/kalshi_research/api/client.py`
- ✅ Fixtures:
  - `tests/fixtures/golden/series_list_response.json`
  - `tests/fixtures/golden/series_single_response.json`
- ✅ Tests: golden fixture validation + client unit tests

### 1.3 `GET /series/fee_changes` ✅

Useful for fee-aware backtests and avoiding surprise changes.

- ✅ Model: `SeriesFeeChange`, `SeriesFeeChangesResponse`
- ✅ Client method: `get_series_fee_changes()`
- ✅ Fixture: `tests/fixtures/golden/series_fee_changes_response.json`
- ⚠️ Note: Fixture has empty array (no fee changes at recording time)

---

## Phase 2 (P2): Multivariate/Metadata Completeness (Discovery correctness)

### 2.1 `GET /events/multivariate`

Purpose: MVEs are excluded from `GET /events`; this endpoint restores coverage.

- Add `get_multivariate_events_page(...)`
- Decide whether it returns `Event` or a dedicated `MultivariateEvent` model (OpenAPI-driven).
- Fixture: `tests/fixtures/golden/events_multivariate_list_response.json`

### 2.2 `GET /events/{event_ticker}/metadata`

Purpose: metadata contains structured info used by some event types.

- Model: `EventMetadata` (new file or in `event.py`)
- Fixture: `tests/fixtures/golden/event_metadata_response.json`

---

## Phase 3 (P2): Advanced Order Ops (TradeExecutor foundation)

These endpoints are the difference between “toy trading” and safe, scalable execution.

### 3.1 `POST/DELETE /portfolio/orders/batched`

Purpose:
- Create up to N orders per request (market-making / scanning many opportunities).
- Cancel many orders efficiently.

OpenAPI schemas:
- requests: `BatchCreateOrdersRequest`, `BatchCancelOrdersRequest`
- responses: `BatchCreateOrdersResponse` (wrapper key: `orders`), `BatchCancelOrdersResponse` (wrapper key: `orders`)

Client methods:
- `batch_create_orders(orders: list[CreateOrderRequest]) -> list[Order]`
- `batch_cancel_orders(order_ids: list[str]) -> list[Order]`

Fixture recording:
- **Demo-only**, because this is inherently a write operation.
- Record raw responses, then immediately clean up any created resting orders.
- Fixtures:
  - `tests/fixtures/golden/batch_create_orders_response.json` (env: demo)
  - `tests/fixtures/golden/batch_cancel_orders_response.json` (env: demo)

### 3.2 Queue position

Endpoints:
- `GET /portfolio/orders/queue_positions`
- `GET /portfolio/orders/{order_id}/queue_position`

OpenAPI schema:
- single: `GetOrderQueuePositionResponse` → `queue_position`

Client methods:
- `get_order_queue_position(order_id: str) -> int`
- `get_orders_queue_positions(order_ids: list[str]) -> dict[str, int]` (OpenAPI-driven)

Fixtures:
- demo (best) or prod if it’s read-only and doesn’t leak sensitive identifiers after sanitization.

### 3.3 `POST /portfolio/orders/{order_id}/decrease`

Purpose: reduce resting order size without cancel+recreate.

- OpenAPI response wrapper: `DecreaseOrderResponse` → `order` (Order object)
- Client method:
  - `decrease_order(order_id: str, *, reduce_by: int | None = None, reduce_to: int | None = None) -> Order`
- Fixtures: demo-only

### 3.4 Order groups (P3 but near TradeExecutor)

Endpoints:
- `GET /portfolio/order_groups`
- `POST /portfolio/order_groups/create`
- `GET /portfolio/order_groups/{order_group_id}`
- `DELETE /portfolio/order_groups/{order_group_id}`
- `PUT /portfolio/order_groups/{order_group_id}/reset`

Implementation is deferred unless/until TradeExecutor needs it for “group cancel” semantics.

### 3.5 `GET /portfolio/orders/{order_id}` (Single order details)

Purpose: retrieve authoritative order status/details after create/amend/decrease, without relying on local DB state.

- OpenAPI response wrapper: `GetOrderResponse` → `order`
- Client method: `get_order(order_id: str) -> Order`
- Fixture: `tests/fixtures/golden/portfolio_order_single_response.json` (env: prod, sanitized)

### 3.6 `GET /portfolio/summary/total_resting_order_value` (P3)

Purpose: compute portfolio risk / exposure to resting orders (useful for TradeExecutor guardrails).

- OpenAPI response wrapper: `GetTotalRestingOrderValueResponse` → `total_resting_order_value`
- Client method: `get_total_resting_order_value() -> int`
- Fixture: `tests/fixtures/golden/portfolio_total_resting_order_value_response.json` (env: prod, sanitized)

---

## Phase 4 (P3): Subaccounts

Endpoints:
- `POST /portfolio/subaccounts` → `CreateSubaccountResponse` (`subaccount_number`)
- `GET /portfolio/subaccounts/balances`
- `POST /portfolio/subaccounts/transfer`
- `GET /portfolio/subaccounts/transfers`

This is lower priority unless/until you actively trade with multiple isolated strategies.

---

## Fixtures, Sanitization, and “No Fake SSOT” Rules

1. Fixtures must contain **raw API responses** under the `response` key.
2. `_metadata.environment` must reflect where it came from (`prod` vs `demo`).
3. For write endpoints, demo fixtures are acceptable SSOT for **shape**, but must be recorded with an explicit,
   reversible workflow and documented in `_recording_summary.json`.

---

## Acceptance Criteria

- [ ] SPEC-037 endpoints implemented incrementally (one endpoint family at a time).
- [ ] Every added endpoint has at least one golden fixture recorded.
- [ ] `uv run python scripts/validate_models_against_golden.py` passes.
- [ ] Unit tests for client unwrapping + model validation exist (fixtures-based).
- [ ] Vendor docs updated when OpenAPI placeholders/paths drift (no silent inconsistencies).
