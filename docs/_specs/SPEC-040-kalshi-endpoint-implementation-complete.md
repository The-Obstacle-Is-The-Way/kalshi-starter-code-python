# SPEC-040: Complete Kalshi Endpoint Implementation (TDD, SSOT-Driven)

**Status:** Draft (Ready for Implementation)
**Priority:** P1 (Foundation for Agent System)
**Created:** 2026-01-14
**Owner:** Solo
**Supersedes:** SPEC-029 (strategy), SPEC-037 (partial)
**Effort:** ~5-7 days total across 4 phases

---

## Executive Summary

This spec consolidates ALL remaining Kalshi API endpoint work into a single, ordered implementation plan. It follows Uncle Bob's Clean Architecture principles:

1. **Dependency Rule**: Code points inward (models → client → CLI)
2. **TDD First**: Every endpoint gets a golden fixture before any client code
3. **SSOT Enforcement**: `scripts/validate_models_against_golden.py` must pass
4. **Interface Segregation**: Small, focused Pydantic models per endpoint

**Implementation Order:**
```
Phase 1: Market Filters       → Enables efficient queries (no more "fetch all")
Phase 2: Order Operations     → Foundation for TradeExecutor
Phase 3: Discovery Endpoints  → Complete market browsing
Phase 4: Operational Endpoints → Nice-to-have observability
```

---

## Current State (SSOT: What We Have)

### Implemented Endpoints (29/74 ≈ 39%)
<!-- AUDIT FIX: Updated to 29/74 after Phase 1+2 implementation (2026-01-14). -->

**Source:** `src/kalshi_research/api/client.py`

| Category | Endpoint | Client Method | Golden Fixture |
|----------|----------|---------------|----------------|
| **Markets** | `GET /markets` | `get_markets_page()`, `get_markets()`, `get_all_markets()` | ✅ `markets_list_response.json` |
| | `GET /markets/{ticker}` | `get_market()` | ✅ `market_single_response.json` |
| | `GET /markets/{ticker}/orderbook` | `get_orderbook()` | ✅ `orderbook_response.json` |
| | `GET /markets/trades` | `get_trades()` | ✅ `trades_list_response.json` |
| | `GET /markets/candlesticks` | `get_candlesticks()` | ✅ `candlesticks_batch_response.json` |
| **Series** | `GET /series` | `get_series_list()` | ✅ `series_list_response.json` |
| | `GET /series/{ticker}` | `get_series()` | ✅ `series_single_response.json` |
| | `GET /series/fee_changes` | `get_series_fee_changes()` | ✅ `series_fee_changes_response.json` |
| | `GET /series/{s}/markets/{m}/candlesticks` | `get_series_candlesticks()` | ✅ `series_candlesticks_response.json` |
| **Events** | `GET /events` | `get_events_page()`, `get_events()`, `get_all_events()` | ✅ `events_list_response.json` |
| | `GET /events/{ticker}` | `get_event()` | ✅ `event_single_response.json` |
| | `GET /events/multivariate` | `get_multivariate_events_page()`, `get_multivariate_events()`, `get_all_multivariate_events()` | ✅ `events_multivariate_list_response.json` |
| **Search** | `GET /search/tags_by_categories` | `get_tags_by_categories()` | ✅ `tags_by_categories_response.json` |
| **Exchange** | `GET /exchange/status` | `get_exchange_status()` | ✅ `exchange_status_response.json` |
| **Portfolio** | `GET /portfolio/balance` | `get_balance()` | ✅ `portfolio_balance_response.json` |
| | `GET /portfolio/positions` | `get_positions()` | ✅ `portfolio_positions_response.json` |
| | `GET /portfolio/orders` | `get_orders()` | ✅ `portfolio_orders_response.json` |
| | `GET /portfolio/fills` | `get_fills()` | ✅ `portfolio_fills_response.json` |
| | `GET /portfolio/settlements` | `get_settlements()` | ✅ `portfolio_settlements_response.json` |
| **Trading** | `POST /portfolio/orders` | `create_order()` | ✅ `create_order_response.json` |
| | `DELETE /portfolio/orders/{id}` | `cancel_order()` | ✅ `cancel_order_response.json` |
| | `POST /portfolio/orders/{id}/amend` | `amend_order()` | ✅ `amend_order_response.json` |
| | `GET /portfolio/orders/{id}` | `get_order()` | ✅ `portfolio_order_single_response.json` |
| | `POST /portfolio/orders/batched` | `batch_create_orders()` | ✅ `batch_create_orders_response.json` (SYNTHETIC) |
| | `DELETE /portfolio/orders/batched` | `batch_cancel_orders()` | ✅ `batch_cancel_orders_response.json` (SYNTHETIC) |
| | `POST /portfolio/orders/{id}/decrease` | `decrease_order()` | ✅ `decrease_order_response.json` (SYNTHETIC) |
| | `GET /portfolio/orders/{id}/queue_position` | `get_order_queue_position()` | ✅ `order_queue_position_response.json` (SYNTHETIC) |
| | `GET /portfolio/orders/queue_positions` | `get_orders_queue_positions()` | ✅ `order_queue_positions_response.json` (SYNTHETIC) |
| **Portfolio Read** | `GET /portfolio/summary/total_resting_order_value` | `get_total_resting_order_value()` | ✅ `portfolio_total_resting_order_value_response.json` (SYNTHETIC) |

### Implemented Filter Parameters (GET /markets) ✅ COMPLETE

**All parameters implemented (Phase 1 - 2026-01-14):**
| Parameter | Type | Description | Status |
|-----------|------|-------------|--------|
| `status` | string | Market status filter | ✅ Implemented |
| `event_ticker` | string | Filter by event | ✅ Implemented |
| `series_ticker` | string | Filter by series | ✅ Implemented |
| `mve_filter` | string | Multivariate filtering | ✅ Implemented |
| `tickers` | string | Comma-separated market tickers (batch lookup) | ✅ Implemented |
| `min_created_ts` | int | Unix timestamp filter (markets created after) | ✅ Implemented |
| `max_created_ts` | int | Unix timestamp filter (markets created before) | ✅ Implemented |
| `min_close_ts` | int | Unix timestamp filter (markets closing after) | ✅ Implemented |
| `max_close_ts` | int | Unix timestamp filter (markets closing before) | ✅ Implemented |
| `min_settled_ts` | int | Unix timestamp filter (markets settled after) | ✅ Implemented |
| `max_settled_ts` | int | Unix timestamp filter (markets settled before) | ✅ Implemented |

**Note:** Only one timestamp family allowed per request (created_ts OR close_ts OR settled_ts).

---

## Not Implemented (Deliberate)

These endpoints are explicitly NOT planned:

| Category | Endpoints | Reason |
|----------|-----------|--------|
| **RFQ/Communications** | 11 endpoints | Institutional block trades - not relevant for solo research |
| **API Keys** | 4 endpoints | Better managed via Kalshi web UI |
| **FCM** | 2 endpoints | Institutional clearing members only |
| **Multivariate Collections** | 5 endpoints | Sports parlay combinations - low priority |

---

## Phase 1: Market Filter Parity

**Goal:** Stop the "fetch all then filter locally" anti-pattern.

**Why First:** Every scan, discovery, and sync operation benefits from server-side filtering.

### 1.1 Add `tickers` Parameter

**Priority:** P2
**Effort:** 30 min

**OpenAPI Definition:**
```yaml
parameters:
  - name: tickers
    in: query
    schema:
      type: string
    description: Comma-separated list of market tickers
```

**Client Changes:**
```python
# src/kalshi_research/api/client.py

async def get_markets_page(
    self,
    status: MarketFilterStatus | str | None = None,
    event_ticker: str | None = None,
    series_ticker: str | None = None,
    tickers: list[str] | None = None,  # NEW
    limit: int = 100,
    cursor: str | None = None,
    mve_filter: Literal["only", "exclude"] | None = None,
) -> tuple[list[Market], str | None]:
```

**TDD Test (write FIRST):**
```python
# tests/unit/api/test_client_filters.py

@respx.mock
async def test_get_markets_with_tickers_filter():
    """GET /markets with tickers param sends comma-separated list."""
    route = respx.get("https://api.elections.kalshi.com/trade-api/v2/markets").mock(
        return_value=httpx.Response(200, json={"markets": [], "cursor": None})
    )

    async with KalshiPublicClient() as client:
        await client.get_markets_page(tickers=["TICKER-A", "TICKER-B"])

    assert route.called
    assert route.calls[0].request.url.params["tickers"] == "TICKER-A,TICKER-B"
```

**Acceptance Criteria:**
- [ ] Test written and failing (TDD red)
- [ ] Client method updated
- [ ] Test passing (TDD green)
- [ ] `uv run python scripts/validate_models_against_golden.py` passes

### 1.2 Add Timestamp Filters

**Priority:** P2-P3
**Effort:** 1 hour

**OpenAPI Constraint (IMPORTANT):**
```
Only one timestamp filter family may be used at a time:
- min_created_ts / max_created_ts: Compatible with status=unopened, open, or empty
- min_close_ts / max_close_ts: Compatible with status=closed or empty
- min_settled_ts / max_settled_ts: Compatible with status=settled or empty
```
<!-- AUDIT FIX: OpenAPI `GET /markets` description omits `paused` from the compatibility table even though `status` enum includes it; prefer enforcing timestamp-family mutual exclusivity (and consider treating `paused` like `open` only after verifying behavior). -->

**Client Changes:**
```python
async def get_markets_page(
    self,
    status: MarketFilterStatus | str | None = None,
    event_ticker: str | None = None,
    series_ticker: str | None = None,
    tickers: list[str] | None = None,
    # NEW: Timestamp filters
    min_created_ts: int | None = None,
    max_created_ts: int | None = None,
    min_close_ts: int | None = None,
    max_close_ts: int | None = None,
    min_settled_ts: int | None = None,
    max_settled_ts: int | None = None,
    limit: int = 100,
    cursor: str | None = None,
    mve_filter: Literal["only", "exclude"] | None = None,
) -> tuple[list[Market], str | None]:
    # Client-side validation
    ts_families_used = sum([
        min_created_ts is not None or max_created_ts is not None,
        min_close_ts is not None or max_close_ts is not None,
        min_settled_ts is not None or max_settled_ts is not None,
    ])
    if ts_families_used > 1:
        raise ValueError(
            "Only one timestamp filter family allowed at a time "
            "(created_ts OR close_ts OR settled_ts)"
        )
```

**TDD Tests:**
```python
async def test_get_markets_with_created_ts_filter():
    """GET /markets with min_created_ts/max_created_ts."""
    # ...

async def test_get_markets_rejects_mixed_timestamp_families():
    """Cannot mix created_ts and close_ts filters."""
    async with KalshiPublicClient() as client:
        with pytest.raises(ValueError, match="Only one timestamp filter family"):
            await client.get_markets_page(
                min_created_ts=1700000000,
                min_close_ts=1700100000,  # Invalid: mixing families
            )
```

**Acceptance Criteria:**
- [ ] Client-side validation rejects invalid combinations
- [ ] All 6 timestamp params wired to query string
- [ ] Unit tests cover valid and invalid cases

---

## Phase 2: Order Operations (TradeExecutor Foundation)

**Goal:** Enable efficient, safe order management for automation.

**Why Second:** TradeExecutor (SPEC-034) depends on these for real order lifecycle management.

### 2.1 GET /portfolio/orders/{order_id} (Single Order Detail)

**Priority:** P2
**Effort:** 30 min

**Why Needed:** After create/amend/decrease, fetch authoritative order state without relying on local DB.

**OpenAPI Response:**
```yaml
GetOrderResponse:
  properties:
    order:
      $ref: '#/components/schemas/Order'
```

**Fixture Recording:**
```bash
# Record to tests/fixtures/golden/portfolio_order_single_response.json
# Requires: an existing order ID from demo environment
```

**Client Method:**
```python
async def get_order(self, order_id: str) -> Order:
    """Fetch a single order by ID."""
    data = await self._auth_get(f"/portfolio/orders/{order_id}")
    return Order.model_validate(data["order"])
```

**TDD Test:**
```python
# tests/unit/api/test_client_extended.py

import pytest
import respx
from httpx import Response

from kalshi_research.api.client import KalshiClient
from tests.golden_fixtures import load_golden_response


@pytest.mark.asyncio
@respx.mock
async def test_get_order_single(mock_auth):
    """GET /portfolio/orders/{order_id} returns single Order."""
    response_json = load_golden_response("portfolio_order_single_response.json")
    route = respx.get(
        "https://api.elections.kalshi.com/trade-api/v2/portfolio/orders/abc123"
    ).mock(return_value=Response(200, json=response_json))

    async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
        order = await client.get_order("abc123")

    assert route.called
    assert order.order_id == response_json["order"]["order_id"]
```

**Acceptance Criteria:**
- [ ] Golden fixture recorded from demo API
- [ ] Fixture added to `validate_models_against_golden.py` mapping
- [ ] Client method implemented
- [ ] Unit test passes

### 2.2 POST /portfolio/orders/batched (Batch Create)

**Priority:** P2
**Effort:** 1-2 hours

**Why Needed:** 10x more efficient for scanning multiple opportunities. Rate limit cost: 1 transaction per order item.

**OpenAPI Request:**
```yaml
BatchCreateOrdersRequest:
  required:
    - orders
  properties:
    orders:
      type: array
      items:
        $ref: '#/components/schemas/CreateOrderRequest'
```
<!-- AUDIT FIX: OpenAPI does not declare `maxItems`; the `/portfolio/orders/batched` description caps batches at 20 orders. -->

**OpenAPI Response:**
```yaml
BatchCreateOrdersResponse:
  required:
    - orders
  properties:
    orders:
      type: array
      items:
        $ref: '#/components/schemas/BatchCreateOrdersIndividualResponse'

BatchCreateOrdersIndividualResponse:
  properties:
    client_order_id:
      type: string
    order:
      $ref: '#/components/schemas/Order'        # nullable
    error:
      $ref: '#/components/schemas/ErrorResponse'  # nullable
```
<!-- AUDIT FIX: Response items are per-order results (`order` OR `error`), not raw `Order` objects. -->

**Models (new):**
<!-- AUDIT FIX: `CreateOrderRequest` already exists in `src/kalshi_research/api/models/order.py`; extend it to match the full OpenAPI optional fields as needed. -->
```python
# src/kalshi_research/api/models/error.py

class ErrorResponse(BaseModel):
    """Per-item error returned inside batch endpoints (OpenAPI ErrorResponse)."""
    model_config = ConfigDict(frozen=True)

    code: str | None = None
    message: str | None = None
    details: str | None = None
    service: str | None = None


# src/kalshi_research/api/models/portfolio.py

class BatchCreateOrdersIndividualResponse(BaseModel):
    """Per-order result from POST /portfolio/orders/batched."""
    model_config = ConfigDict(frozen=True)

    client_order_id: str | None = None
    order: Order | None = None
    error: ErrorResponse | None = None


class BatchCreateOrdersResponse(BaseModel):
    """Response from POST /portfolio/orders/batched."""
    model_config = ConfigDict(frozen=True)

    orders: list[BatchCreateOrdersIndividualResponse]
```

**Client Method:**
```python
async def batch_create_orders(
    self,
    orders: list[CreateOrderRequest],
    *,
    dry_run: bool = False,
) -> BatchCreateOrdersResponse:
    """
    Create multiple orders in a single request.

    Args:
        orders: List of order requests (max 20)
        dry_run: If True, validate but don't execute

    Returns:
        Parsed response with one result per order (either `order` or `error`).

    Note:
        Rate limit cost: 1 transaction per order in the batch.
    """
    if len(orders) > 20:
        raise ValueError("Maximum 20 orders per batch request")

    if dry_run:
        logger.info("DRY RUN: batch_create_orders", count=len(orders))
        return BatchCreateOrdersResponse(orders=[])

    # ... implementation
```

**Fixture Recording:**
```bash
# Environment: demo (write operation)
# Steps:
# 1. Create 2-3 small orders via batch endpoint
# 2. Record response to tests/fixtures/golden/batch_create_orders_response.json
# 3. Immediately cancel the created orders
```

**TDD Tests:**
```python
async def test_batch_create_orders_max_20():
    """Batch create rejects more than 20 orders."""
    async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
        with pytest.raises(ValueError, match="Maximum 20"):
            # Build 21 CreateOrderRequest objects (each with a unique client_order_id).
            await client.batch_create_orders([...], dry_run=True)

@respx.mock
async def test_batch_create_orders_success():
    """Batch create sends correct payload and parses response."""
    response_json = load_golden_response("batch_create_orders_response.json")
    route = respx.post("https://api.elections.kalshi.com/trade-api/v2/portfolio/orders/batched").mock(
        return_value=Response(201, json=response_json)
    )

    async with KalshiClient(key_id="test", private_key_path="test.pem") as client:
        result = await client.batch_create_orders([...])

    assert route.called
    assert len(result.orders) == len(response_json["orders"])
```

**Acceptance Criteria:**
- [ ] `CreateOrderRequest` model updated for OpenAPI parity (optional fields)
- [ ] `ErrorResponse` model added
- [ ] `BatchCreateOrdersResponse` models added
- [ ] Golden fixture recorded from demo
- [ ] Client method with dry_run support
- [ ] Unit tests cover validation and success path

### 2.3 DELETE /portfolio/orders/batched (Batch Cancel)

**Priority:** P2
**Effort:** 1 hour

**Why Needed:** Efficient cleanup after batch create or when exiting positions.

**OpenAPI Request:**
```yaml
BatchCancelOrdersRequest:
  required:
    - ids
  properties:
    ids:
      type: array
      items:
        type: string
```
<!-- AUDIT FIX: OpenAPI uses `ids` (not `order_ids`). -->

**OpenAPI Response:**
```yaml
BatchCancelOrdersResponse:
  required:
    - orders
  properties:
    orders:
      type: array
      items:
        $ref: '#/components/schemas/BatchCancelOrdersIndividualResponse'

BatchCancelOrdersIndividualResponse:
  required:
    - order_id
    - reduced_by
  properties:
    order_id:
      type: string
    reduced_by:
      type: integer
    order:
      $ref: '#/components/schemas/Order'        # nullable
    error:
      $ref: '#/components/schemas/ErrorResponse'  # nullable
```
<!-- AUDIT FIX: Batch cancel returns per-order results (with partial failures), not raw `Order` objects. -->

**Models (new):**
```python
# src/kalshi_research/api/models/portfolio.py

class BatchCancelOrdersIndividualResponse(BaseModel):
    """Per-order result from DELETE /portfolio/orders/batched."""
    model_config = ConfigDict(frozen=True)

    order_id: str
    reduced_by: int
    order: Order | None = None
    error: ErrorResponse | None = None


class BatchCancelOrdersResponse(BaseModel):
    """Response from DELETE /portfolio/orders/batched."""
    model_config = ConfigDict(frozen=True)

    orders: list[BatchCancelOrdersIndividualResponse]
```

**Client Method:**
```python
async def batch_cancel_orders(
    self,
    order_ids: list[str],
    *,
    dry_run: bool = False,
) -> BatchCancelOrdersResponse:
    """
    Cancel multiple orders in a single request.

    Args:
        order_ids: List of order IDs to cancel
        dry_run: If True, validate but don't execute

    Returns:
        Parsed response with one result per id (either `order` or `error`).

    Note:
        Rate limit cost: 0.2 transactions per cancel (batch is cheaper).
    """
```

### 2.4 POST /portfolio/orders/{order_id}/decrease

**Priority:** P2
**Effort:** 45 min

**Why Needed:** Reduce resting order size without cancel+recreate (preserves queue position).

**OpenAPI Request:**
```yaml
DecreaseOrderRequest:
  properties:
    reduce_by:
      type: integer
      description: Number of contracts to remove
    reduce_to:
      type: integer
      description: Target remaining contracts (alternative to reduce_by)
```

**OpenAPI Response:**
```yaml
DecreaseOrderResponse:
  properties:
    order:
      $ref: '#/components/schemas/Order'
```

**Client Method:**
```python
async def decrease_order(
    self,
    order_id: str,
    *,
    reduce_by: int | None = None,
    reduce_to: int | None = None,
    dry_run: bool = False,
) -> Order:
    """
    Decrease an existing order's size.

    Args:
        order_id: Order to decrease
        reduce_by: Number of contracts to remove (mutually exclusive with reduce_to)
        reduce_to: Target remaining contracts (mutually exclusive with reduce_by)
        dry_run: If True, validate but don't execute

    Returns:
        Updated Order object

    Note:
        Unlike cancel+recreate, decrease preserves queue position.
    """
    if reduce_by is None and reduce_to is None:
        raise ValueError("Must provide reduce_by or reduce_to")
    if reduce_by is not None and reduce_to is not None:
        raise ValueError("Provide only one of reduce_by or reduce_to")
```

### 2.5 GET /portfolio/orders/{order_id}/queue_position

**Priority:** P2
**Effort:** 30 min

**Why Needed:** Market making intelligence - know where you are in the queue.

**OpenAPI Response:**
```yaml
GetOrderQueuePositionResponse:
  properties:
    queue_position:
      type: integer
```

**Client Method:**
```python
async def get_order_queue_position(self, order_id: str) -> int:
    """
    Get queue position for a resting order.

    Returns:
        Number of contracts ahead in queue (0 = front of queue)

    Note:
        The deprecated `queue_position` field on Order always returns 0.
        Use this dedicated endpoint for accurate queue position.
    """
    data = await self._auth_get(f"/portfolio/orders/{order_id}/queue_position")
    return data["queue_position"]
```

### 2.6 GET /portfolio/orders/queue_positions (Batch)

**Priority:** P2
**Effort:** 30 min

**OpenAPI Parameters:**
| Parameter | Type | Description |
|----------|------|-------------|
| `market_tickers` | string | Comma-separated list of market tickers to filter by |
| `event_ticker` | string | Event ticker to filter by |

**OpenAPI Response:**
```yaml
GetOrderQueuePositionsResponse:
  required:
    - queue_positions
  properties:
    queue_positions:
      type: array
      items:
        $ref: '#/components/schemas/OrderQueuePosition'

OrderQueuePosition:
  required:
    - order_id
    - market_ticker
    - queue_position
  properties:
    order_id:
      type: string
    market_ticker:
      type: string
    queue_position:
      type: integer
```
<!-- AUDIT FIX: This endpoint returns queue positions for *all resting orders* (optionally filtered by market tickers / event), not an `order_ids` lookup. -->

**Models (new):**
```python
# src/kalshi_research/api/models/portfolio.py

class OrderQueuePosition(BaseModel):
    """Queue position for a single resting order (OpenAPI OrderQueuePosition)."""
    model_config = ConfigDict(frozen=True)

    order_id: str
    market_ticker: str
    queue_position: int


class GetOrderQueuePositionsResponse(BaseModel):
    """Response wrapper from GET /portfolio/orders/queue_positions."""
    model_config = ConfigDict(frozen=True)

    queue_positions: list[OrderQueuePosition]
```

**Client Method:**
```python
async def get_orders_queue_positions(
    self,
    *,
    market_tickers: list[str] | None = None,
    event_ticker: str | None = None,
) -> list[OrderQueuePosition]:
    """
    Get queue positions for all resting orders (optionally filtered).

    Args:
        market_tickers: Optional list of market tickers to filter by.
        event_ticker: Optional event ticker to filter by.

    Returns:
        List of queue positions (order_id, market_ticker, queue_position).
    """
```

### 2.7 GET /portfolio/summary/total_resting_order_value

**Priority:** P3
**Effort:** 20 min

**Why Needed:** Risk monitoring - total capital tied up in resting orders.

**Client Method:**
```python
async def get_total_resting_order_value(self) -> int:
    """
    Get total value of all resting orders in cents.

    Useful for TradeExecutor budget guardrails.
    """
    data = await self._auth_get("/portfolio/summary/total_resting_order_value")
    return data["total_resting_order_value"]
```

---

## Phase 3: Discovery Endpoints

**Goal:** Complete market browsing capabilities.

### 3.1 GET /events/{event_ticker}/metadata

**Priority:** P3
**Effort:** 30 min

**Why Needed:** Structured event context (optional enhancement).

**New Model:**
```python
# src/kalshi_research/api/models/event.py

class MarketMetadata(BaseModel):
    """Per-market metadata from GET /events/{event_ticker}/metadata."""
    model_config = ConfigDict(frozen=True)

    market_ticker: str
    image_url: str
    color_code: str


class SettlementSource(BaseModel):
    """Settlement source metadata from GET /events/{event_ticker}/metadata."""
    model_config = ConfigDict(frozen=True)

    name: str | None = None
    url: str | None = None


class EventMetadataResponse(BaseModel):
    """Response from GET /events/{event_ticker}/metadata (OpenAPI GetEventMetadataResponse)."""
    model_config = ConfigDict(frozen=True)

    image_url: str
    featured_image_url: str | None = None
    market_details: list[MarketMetadata]
    settlement_sources: list[SettlementSource]
    competition: str | None = None
    competition_scope: str | None = None
```
<!-- AUDIT FIX: OpenAPI response is a flat object (not nested under `metadata`). -->

### 3.2 GET /structured_targets and GET /structured_targets/{id}

**Priority:** P3
**Effort:** 1 hour

**Why Needed:** Sports prop betting discovery (lower priority for research focus).

**New Model:**
```python
# src/kalshi_research/api/models/structured_target.py

class StructuredTargetSummary(BaseModel):
    """Summary from GET /structured_targets list."""
    model_config = ConfigDict(frozen=True)

    id: str
    type: str | None = None
    competition: str | None = None
    # Additional fields TBD from OpenAPI

class StructuredTarget(BaseModel):
    """Full detail from GET /structured_targets/{id}."""
    model_config = ConfigDict(frozen=True)

    # Fields TBD from OpenAPI
```

### 3.3 GET /search/filters_by_sport

**Priority:** P3
**Effort:** 30 min

**Why Needed:** Discovery UX for sports markets (pairs with structured targets).

**New Models (OpenAPI GetFiltersBySportsResponse):**
```python
# src/kalshi_research/api/models/search.py

class ScopeList(BaseModel):
    model_config = ConfigDict(frozen=True)

    scopes: list[str]


class SportFilterDetails(BaseModel):
    model_config = ConfigDict(frozen=True)

    scopes: list[str]
    competitions: dict[str, ScopeList]


class FiltersBySportsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    filters_by_sports: dict[str, SportFilterDetails]
    sport_ordering: list[str]
```

### 3.4 GET /series/{series_ticker}/events/{ticker}/candlesticks

**Priority:** P3
**Effort:** 30-45 min

**Why Needed:** Event-level historical price/volume context (public endpoint; auth not required).

**Notes:**
- Response uses `market_tickers` + `market_candlesticks` (array-of-arrays aligned by index).
- Candlestick item schema matches `Candlestick` (end_period_ts, price, yes_bid, yes_ask, volume, open_interest).
- Suggested method: `KalshiPublicClient.get_event_candlesticks(...)`

### 3.5 GET /series/{series_ticker}/events/{ticker}/forecast_percentile_history

**Priority:** P3
**Effort:** 45-60 min

**Why Needed:** Optional (mostly for deeper analytics); requires signed headers (auth required).
- Suggested method: `KalshiClient.get_forecast_percentile_history(...)`

---

## Phase 4: Operational Endpoints (Nice-to-Have)

**Goal:** Operational awareness for automation.

### 4.1 Exchange (3 endpoints)

**Priority:** P3
**Effort:** 20 min

**Why Needed:** Know when trading is active/paused.

**Endpoints:**
- `GET /exchange/schedule`
- `GET /exchange/announcements`
- `GET /exchange/user_data_timestamp`

### 4.2 Order Groups (5 endpoints)

**Priority:** P3
**Effort:** 2 hours

**Why Needed:** Grouped order management (cancel all related orders atomically).

### 4.3 Subaccounts (4 endpoints)

**Priority:** P3
**Effort:** 1-2 hours

**Why Needed:** Optional; useful only if you actually use subaccounts for accounting/segmentation.

### 4.4 Milestones & Live Data (4 endpoints)

**Priority:** P3
**Effort:** 1-2 hours

**Why Needed:** Optional real-time event tracking (likely overkill for a solo research CLI unless building alerts).

### 4.5 Incentive Programs (1 endpoint)

**Priority:** P3
**Effort:** 15-20 min

**Why Needed:** Informational only.

---

## TDD Implementation Pattern (Mandatory)

For **every** endpoint, follow this exact sequence:

### Step 1: Record Golden Fixture

```bash
# For read endpoints (prod OK):
# 1) Add the endpoint to `scripts/record_api_responses.py` (public or authenticated section)
# 2) Record fixtures:
uv run python scripts/record_api_responses.py --endpoint public
# or:
uv run python scripts/record_api_responses.py --endpoint authenticated

# For write endpoints (demo ONLY):
# Manually capture via curl or script, save to tests/fixtures/golden/
```
<!-- AUDIT FIX: `scripts/record_api_responses.py --endpoint ...` records predefined endpoint groups (`public|phase3|phase4|authenticated|order_ops|all`), not arbitrary per-endpoint names. -->

### Step 2: Add to Validation Script

```python
# scripts/validate_models_against_golden.py

MODEL_MAPPING: Final[dict[str, list[tuple[str, type[BaseModel]]]]] = {
    # ... existing mappings ...
    "new_endpoint_response.json": [("response.wrapper_key", NewModel)],
}
```

### Step 3: Write Failing Test (TDD Red)

```python
# tests/unit/api/test_client_*.py

@respx.mock
async def test_new_endpoint():
    """Description of what we're testing."""
    from httpx import Response
    from tests.golden_fixtures import load_golden_response

    response_json = load_golden_response("new_endpoint_response.json")
    route = respx.get("...").mock(return_value=Response(200, json=response_json))

    async with KalshiPublicClient() as client:
        result = await client.new_method()

    assert result.some_field == expected_value
```

### Step 4: Implement Client Method

```python
# src/kalshi_research/api/client.py

async def new_method(self, ...) -> NewModel:
    """Docstring with Args/Returns."""
    data = await self._get("/new/endpoint", params)
    return NewModel.model_validate(data["wrapper_key"])
```

### Step 5: Verify (TDD Green)

```bash
# Must ALL pass:
uv run pytest tests/unit/api/test_client_*.py -v
uv run python scripts/validate_models_against_golden.py
uv run pre-commit run --all-files
```

---

## Acceptance Criteria (Per Phase)

### Phase 1: Market Filters ✅ COMPLETE (2026-01-14)
- [x] `tickers` parameter implemented and tested
- [x] All 6 timestamp parameters implemented
- [x] Client-side validation for incompatible filter combinations
- [x] All existing tests still pass (738 tests)

### Phase 2: Order Operations ✅ COMPLETE (2026-01-14)
- [x] `get_order(order_id)` implemented with golden fixture
- [x] `batch_create_orders()` implemented with golden fixture (SYNTHETIC - demo auth unavailable)
- [x] `batch_cancel_orders()` implemented with golden fixture (SYNTHETIC - demo auth unavailable)
- [x] `decrease_order()` implemented with golden fixture (SYNTHETIC)
- [x] `get_order_queue_position()` implemented with golden fixture (SYNTHETIC)
- [x] `get_orders_queue_positions()` implemented with golden fixture (SYNTHETIC)
- [x] `get_total_resting_order_value()` implemented with golden fixture (SYNTHETIC)
- [x] All methods have dry_run support where applicable
- [x] `validate_models_against_golden.py` passes (755 tests)

### Phase 3: Discovery ✅ COMPLETE (2026-01-15, except optional auth-only forecast history)
- [x] `get_event_metadata()` implemented with golden fixture
- [x] Structured targets list/detail implemented with golden fixtures
- [x] `get_filters_by_sport()` implemented with golden fixture
- [x] Event candlesticks implemented with golden fixture
- [ ] Forecast percentile history implemented with golden fixture (auth required; optional)

### Phase 4: Operational ✅ COMPLETE (2026-01-15, excluding optional subaccounts)
- [x] Exchange schedule/announcements/user_data_timestamp implemented
- [x] Order groups implemented
- [ ] Subaccounts endpoints implemented (if needed; not implemented)
- [x] Milestones/live data implemented
- [x] Incentive programs implemented

---

## Cross-References

| Item | Relationship |
|------|--------------|
| **SPEC-029** | Superseded - strategy now consolidated here |
| **SPEC-037** | Superseded - Phase 1 complete, remaining phases here |
| **SPEC-034** | Depends on Phase 2 (order operations) |
| **SPEC-032** | Depends on this spec (agent needs complete API) |
| **DEBT-015** | Tracks missing endpoints (update as implemented) |
| `kalshi-api-reference.md` | SSOT vendor docs |
| `kalshi-openapi-coverage.md` | Coverage tracking |

---

## Notes for Implementation

### Environment Requirements

- **Read endpoints:** Record from prod (public data)
- **Write endpoints:** Record from demo only (avoid real money)
- **Authenticated reads:** Record from prod with sanitization

### Fixture Sanitization Rules

1. Remove any PII (email, name)
2. Keep order IDs, tickers, timestamps (needed for testing)
3. Add `_metadata.environment` field to track source

### Rate Limit Awareness

| Operation | Cost |
|-----------|------|
| `create_order` | 1 transaction |
| `batch_create_orders` | 1 per order |
| `cancel_order` | 1 transaction |
| `batch_cancel_orders` | 0.2 per cancel |
| `amend_order` | 1 transaction |
| `decrease_order` | 1 transaction |

---

## Definition of Done

This spec is complete when:

1. All Phase 1-2 endpoints implemented (Phase 3-4 optional)
2. `uv run python scripts/validate_models_against_golden.py` passes with all new fixtures
3. `uv run pytest` passes (727+ tests)
4. `uv run pre-commit run --all-files` passes
5. Coverage in `kalshi-openapi-coverage.md` updated
6. DEBT-015 updated to reflect resolved items
