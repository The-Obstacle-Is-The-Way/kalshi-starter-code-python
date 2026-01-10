# BUG-051: Cancel Order Response Schema Mismatch

**Priority**: Medium
**Status**: Fixed
**Created**: 2026-01-10
**Resolved**: 2026-01-10

## Symptom

`KalshiClient.cancel_order()` raised a Pydantic validation error when the `DELETE /portfolio/orders/{id}` response shape did not match our `CancelOrderResponse` model.

This surfaced as failing integration tests:

- `tests/integration/api/test_trading_integration.py::test_cancel_order_flow`

## Root Cause

The cancel order endpoint response shape can be nested under an `order` key (consistent with other order endpoints like `create_order` and `amend_order`).

Our implementation attempted to validate the entire response object directly against:

```python
CancelOrderResponse(order_id=..., status=...)
```

…which fails when the payload is nested (or if the response omits `order_id`).

## Fix

1. Parse the payload as `data["order"]` when present (fallback to `data`).
2. Default `order_id` to the order id we attempted to cancel when absent in the response.
3. Allow `status` to be populated from either `status` or `order_status`.

## Changes Made

- `src/kalshi_research/api/client.py`: `cancel_order()` now extracts `order` payload, injects missing `order_id`, and validates safely.
- `src/kalshi_research/api/models/portfolio.py`: `CancelOrderResponse.status` accepts `status` or `order_status` via `AliasChoices`.

## Acceptance Criteria

- [x] `cancel_order()` succeeds for both nested and top-level response payloads
- [x] Integration tests for trading flows pass
