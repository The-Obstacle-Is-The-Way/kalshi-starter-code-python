# BUG-065: `amend_order()` Missing Required Fields

**Priority:** P2
**Status:** Open
**Found:** 2026-01-12

---

## Summary

The `amend_order()` method has an incomplete signature. Per Kalshi API docs, several fields are **required** that we don't support. The method may work for simple cases but will fail for proper order tracking.

---

## Current State

**Location:** `src/kalshi_research/api/client.py`

**Current signature:**
```python
async def amend_order(
    self,
    order_id: str,
    price: int | None = None,
    count: int | None = None,
    dry_run: bool = False,
) -> OrderResponse
```

**Missing required fields per vendor docs:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ticker` | string | Yes | Market ticker |
| `side` | enum | Yes | `yes` or `no` |
| `action` | enum | Yes | `buy` or `sell` |
| `client_order_id` | string | Yes | Original client-specified order ID |
| `updated_client_order_id` | string | Yes | New client-specified order ID |

**Missing price alternatives:**
- `no_price` (cents) - Alternative to `yes_price`
- `yes_price_dollars` (string) - Dollar-denominated price
- `no_price_dollars` (string) - Dollar-denominated price

---

## Evidence from Vendor Docs

From `docs/_vendor-docs/kalshi-api-reference.md` lines 879-902:

```markdown
### Amend Order Full Schema

**Endpoint:** `POST /portfolio/orders/{order_id}/amend`

#### Request Body

**Required fields:**

| Field | Type | Description |
|-------|------|-------------|
| `ticker` | string | Market ticker |
| `side` | enum | `yes` or `no` |
| `action` | enum | `buy` or `sell` |
| `client_order_id` | string | Original client-specified order ID |
| `updated_client_order_id` | string | New client-specified order ID (must be unique) |
```

---

## Impact

- Order tracking via `client_order_id` won't work properly
- Can't amend using dollar-denominated prices (needed post Jan 15)
- Missing fields may cause API errors or unexpected behavior

---

## Fix Required

1. Add missing required parameters to method signature
2. Add dollar-price alternatives (`yes_price_dollars`, `no_price_dollars`)
3. Update request body construction
4. Add validation for enum types
5. Update docstrings

---

## Test Plan

- [ ] Add `ticker`, `side`, `action` parameters
- [ ] Add `client_order_id`, `updated_client_order_id` parameters
- [ ] Add dollar-price parameters
- [ ] Test with mock API
- [ ] Integration test with demo environment

---

## Related

- BUG-064: Missing order safety parameters
- BUG-067: Order model missing fields
