# BUG-070: `cancel_order()` Drops `reduced_by` From Cancel Response (API Completeness)

**Priority:** P3 (Completeness - order cancel still succeeds)
**Status:** ✅ Fixed
**Found:** 2026-01-12
**Fixed:** 2026-01-12
**Verified:** 2026-01-12 (code audit + live OpenAPI spec)

---

## Summary

Kalshi's OpenAPI spec defines `DELETE /portfolio/orders/{order_id}` (Cancel Order) as returning a
top-level object containing:
- `order`: an `Order` object
- `reduced_by`: integer count of contracts canceled

Our `KalshiClient.cancel_order()` currently extracts and validates only the nested `order` object,
discarding `reduced_by` if it exists at the top level.

This does not break cancellation, but it loses useful information for audit logging and correctness.

---

## Evidence (Live OpenAPI Spec)

**Source:** `https://docs.kalshi.com/openapi.yaml` (fetched 2026-01-12)

```yaml
CancelOrderResponse:
  required:
    - order
    - reduced_by
  properties:
    order:
      $ref: '#/components/schemas/Order'
    reduced_by:
      type: integer
```

---

## Current Code (Drops Field)

**Location:** `src/kalshi_research/api/client.py` (`cancel_order()`)

Current logic selects only `data["order"]` (or `data` if no `order` key), then validates:
- `order_id`
- `status` / `order_status` (alias-handled)
- `reduced_by` (optional field)

But when the response shape is:

```json
{
  "order": { "order_id": "oid-123", "status": "canceled", "...": "..." },
  "reduced_by": 10
}
```

we currently discard `reduced_by` before validating, so callers see `reduced_by=None`.

---

## Fix Implemented

Preserve `reduced_by` if present when flattening the response shape for `CancelOrderResponse`.

Implementation:
- `src/kalshi_research/api/client.py`: merge top-level `reduced_by` into the payload dict before
  calling `CancelOrderResponse.model_validate(...)`

---

## Test Plan

- [x] Update `tests/unit/api/test_trading.py::test_cancel_order_rate_limit` to include `reduced_by`
- [x] Update `tests/integration/api/test_trading_integration.py::test_cancel_order_flow` to include
  `reduced_by` in the mocked response
- [x] Ensure `cancel_order()` returns `CancelOrderResponse.reduced_by == 10`

---

## Related

- `src/kalshi_research/api/models/portfolio.py:CancelOrderResponse` already models `reduced_by`
