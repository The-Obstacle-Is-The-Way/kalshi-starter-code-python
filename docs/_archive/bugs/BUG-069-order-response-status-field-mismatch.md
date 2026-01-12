# BUG-069: Order Response Schema Mismatch (`status` vs `order_status`) Can Orphan Live Orders

**Priority:** P0 (Financial risk - can lose track of live orders)
**Status:** ✅ Fixed
**Found:** 2026-01-12
**Fixed:** 2026-01-12
**Verified:** 2026-01-12 (code audit + live OpenAPI spec)

---

## Summary

Our trading response model expects `order_status`, but Kalshi's canonical OpenAPI spec uses `status` on
the `Order` object.

This mismatch can cause a **Pydantic validation error AFTER the API successfully places an order**,
which is dangerous because it can leave a **live order on the exchange that our system believes
failed** (or cannot identify/cancel later).

---

## Evidence (Live OpenAPI Spec)

**Source:** `https://docs.kalshi.com/openapi.yaml` (fetched 2026-01-12)

### 1) OpenAPI contains no `order_status`

```bash
rg -n "order_status" openapi.yaml
# Result: no matches
```

### 2) The `Order` schema requires `status`

```yaml
Order:
  required:
    - order_id
    - status
  properties:
    status:
      $ref: '#/components/schemas/OrderStatus'

OrderStatus:
  enum: ['resting', 'canceled', 'executed']
```

### 3) Create/amend responses return `Order` objects

```yaml
CreateOrderResponse:
  properties:
    order:
      $ref: '#/components/schemas/Order'

AmendOrderResponse:
  properties:
    order:
      $ref: '#/components/schemas/Order'
```

---

## Current Code (Mismatch)

### Response model expects `order_status`

**Location:** `src/kalshi_research/api/models/order.py`

```python
class OrderResponse(BaseModel):
    order_id: str
    order_status: str
```

### Trading methods parse the API payload into `OrderResponse`

**Location:** `src/kalshi_research/api/client.py`

- `create_order()` parses `data["order"]` into `OrderResponse`
- `amend_order()` parses `data["order"]` into `OrderResponse`

If the API returns `{"order_id": "...", "status": "resting"}`, Pydantic will raise a validation error
because `order_status` is missing.

---

## Why This Is P0

If `dry_run=False` (live trading), the server can successfully accept an order and return 201/200, but
we can still throw after-the-fact due to schema mismatch. That creates a real risk of:
- orphaned/resting live orders we don't capture by ID
- retries placing duplicate orders
- inability to programmatically cancel/inspect the original order

---

## Fix Implemented

Made `OrderResponse` accept `status` as an alias of `order_status` (backwards compatible).

Pattern already used elsewhere:
- `CancelOrderResponse.status` accepts both `status` and `order_status` via `AliasChoices`.

**Implementation:**
- `src/kalshi_research/api/models/order.py`: `OrderResponse.order_status` now uses
  `validation_alias=AliasChoices("order_status", "status")`
- Updated unit + integration tests to mock the canonical `status` field
- Added a unit test confirming the legacy `order_status` key is still accepted

---

## Test Plan (TDD)

- [x] Update `tests/unit/api/test_trading.py` to return `{"status": "resting"}` for create/amend mocks
- [x] Update `tests/integration/api/test_trading_integration.py` similarly (respx mocks)
- [x] Add unit test asserting `order_status` continues to be accepted (legacy compatibility)
- [x] Run `uv run pre-commit run --all-files`

---

## Related

- BUG-065: `amend_order()` request body is missing required fields (separate issue)
- `src/kalshi_research/api/models/portfolio.py:CancelOrderResponse` already handles `status` vs
  `order_status` defensively
