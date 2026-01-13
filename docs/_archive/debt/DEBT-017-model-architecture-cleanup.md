# DEBT-017: Model Architecture Cleanup (Duplicate Order Models + Validation Gaps)

**Priority:** P3 (Code clarity, not functional)
**Status:** ✅ Resolved
**Found:** 2026-01-12
**Resolved:** 2026-01-13
**Source:** SSOT fixture validation review

---

## Summary

This debt tracked two model/validation issues:

1. **Duplicate `Order` models** - Two different `Order` classes exist with different field sets
2. **Incomplete fixture validation** - `amend_order` response has `old_order` field not separately validated

---

## Issue 1: Duplicate Order Models

### Problem

Previously, two `Order` classes existed in the codebase:

| Location | Fields | Used By |
|----------|--------|---------|
| `src/kalshi_research/api/models/order.py` | Minimal (~12 fields) | ⚠️ Dead code (removed) |
| `src/kalshi_research/api/models/portfolio.py` | Full (31 fields) | ✅ Portfolio + trading fixtures |

### Resolution

- Deleted the unused minimal `Order` model (and its unused `OrderStatus` enum) from
  `src/kalshi_research/api/models/order.py`.
- The single authoritative `Order` model now lives in
  `src/kalshi_research/api/models/portfolio.py` and is used for portfolio + trading fixtures.

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

### Resolution

- Updated `scripts/validate_models_against_golden.py` to validate BOTH:
  - `amend_order_response.json (response.order)`
  - `amend_order_response.json (response.old_order)`

---

## Acceptance Criteria

- [x] Single authoritative `Order` model (in `api/models/portfolio.py`)
- [x] `amend_order` validates both `order` and `old_order`
- [x] No import confusion between order modules (dead model removed)

---

## Cross-References

| Item | Relationship |
|------|--------------|
| `api/models/order.py` | Contains minimal Order |
| `api/models/portfolio.py` | Contains full Order |
| `scripts/validate_models_against_golden.py` | Uses portfolio.Order |
| DEBT-016 | Related fixture validation work |
