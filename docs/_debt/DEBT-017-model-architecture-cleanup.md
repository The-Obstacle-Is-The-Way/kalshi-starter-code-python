# DEBT-017: Model Architecture Cleanup (Duplicate Order Models + Validation Gaps)

**Priority:** P3 (Code clarity, not functional)
**Status:** Open
**Found:** 2026-01-12
**Source:** SSOT fixture validation review

---

## Summary

The codebase has model architecture issues that create confusion and incomplete validation:

1. **Duplicate `Order` models** - Two different `Order` classes exist with different field sets
2. **Incomplete fixture validation** - `amend_order` response has `old_order` field not separately validated

---

## Issue 1: Duplicate Order Models

### Problem

Two `Order` classes exist in the codebase:

| Location | Fields | Used By |
|----------|--------|---------|
| `api/models/order.py:73` | Minimal (11 fields) | Internal trading logic |
| `api/models/portfolio.py:185` | Full (28 fields) | Portfolio API responses |

### order.py:Order (Minimal)

```python
class Order(BaseModel):
    order_id: str
    client_order_id: str
    ticker: str
    side: OrderSide
    action: OrderAction
    type: OrderType
    yes_price: int
    count: int
    status: OrderStatus
    created_time: str
    expiration_time: str | None = None
    close_cancel_count: int | None = None
```

### portfolio.py:Order (Full)

```python
class Order(BaseModel):
    order_id: str
    user_id: str | None = None
    client_order_id: str | None = None
    ticker: str
    status: str
    type: str | None = None
    side: str | None = None
    action: str | None = None
    yes_price: int | None = None
    no_price: int | None = None
    yes_price_dollars: str | None = None
    no_price_dollars: str | None = None
    count: int | None = None
    initial_count: int | None = None
    fill_count: int | None = None
    remaining_count: int | None = None
    taker_fees: int | None = None
    maker_fees: int | None = None
    taker_fill_cost: int | None = None
    maker_fill_cost: int | None = None
    # ... more fields
```

### Impact

- **Confusion**: Which `Order` should code import?
- **Import errors**: Wrong import silently uses wrong model
- **Validation gaps**: `order.py:Order` can't validate full API responses

### Current Usage

| Consumer | Import | Correct? |
|----------|--------|----------|
| `validate_models_against_golden.py` | `portfolio.Order` | ✅ |
| `client.py:create_order` | Returns `OrderResponse` | ✅ (but minimal) |
| `client.py:amend_order` | Returns `OrderResponse` | ✅ (but minimal) |

### Recommended Fix

**Option A (Preferred): Consolidate to Single Order Model**

1. Move `portfolio.py:Order` to `order.py:Order` (keep full version)
2. Delete the minimal `order.py:Order` class
3. Update all imports
4. Rename old `OrderResponse` to something more specific if needed

**Option B: Rename for Clarity**

1. Rename `order.py:Order` → `OrderSummary` or `OrderLite`
2. Keep `portfolio.py:Order` as the full model
3. Document which to use where

**Effort:** Small (2-3 files to update)

---

## Issue 2: amend_order Response Validation Gap

### Problem

The `amend_order` API response has TWO Order objects:

```json
{
  "old_order": { /* Order object */ },
  "order": { /* Order object */ }
}
```

The golden fixture validation (`validate_models_against_golden.py`) only validates `response.order`:

```python
"amend_order_response.json": ("response.order", Order),
```

The `old_order` field is NOT validated against the Order model.

### Impact

- **Low**: Both are Order objects, so if `order` validates, `old_order` likely does too
- **Gap**: If API changes `old_order` shape, we won't catch it

### Recommended Fix

Add separate validation for `old_order`:

```python
MODEL_MAPPING = {
    # ... existing entries ...
    "amend_order_response.json": ("response.order", Order),
    # NEW: Also validate old_order
    # (requires script change to support multiple paths per fixture)
}
```

Or add a custom validation step in the script for amend_order.

**Effort:** Small (script enhancement)

---

## Acceptance Criteria

- [ ] Single authoritative `Order` model (or clearly named variants)
- [ ] All Order response fields validated against golden fixtures
- [ ] No import confusion between order modules

---

## Cross-References

| Item | Relationship |
|------|--------------|
| `api/models/order.py` | Contains minimal Order |
| `api/models/portfolio.py` | Contains full Order |
| `scripts/validate_models_against_golden.py` | Uses portfolio.Order |
| DEBT-016 | Related fixture validation work |
