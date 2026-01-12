# BUG-067: Order Model Missing Fields (API Completeness)

**Priority:** P3 (was P2 - downgraded after verification)
**Status:** ✅ Fixed
**Found:** 2026-01-12
**Fixed:** 2026-01-12
**Verified:** 2026-01-12

---

## Summary

The Order model was missing several fields from the Kalshi OpenAPI schema. However, after verification:
1. **Missing fields are not used** - `get_orders()` is called but result fields aren't processed
2. **No CLI exposure** - `get_orders` isn't used in any CLI command
3. **API completeness issue** - Not a functional bug

---

## Fix Implemented

- Expanded `Order` in `src/kalshi_research/api/models/portfolio.py` to include optional OpenAPI fields:
  `user_id`, `client_order_id`, `type`, `*_dollars`, `initial_count`, `fill_count`, `remaining_count`,
  fee/cost fields, timestamps, and self-trade / order-group fields.
- Added unit coverage to ensure these fields parse correctly.

---

## Verification Results

**Are missing Order fields used anywhere?**

```bash
grep -r "\.fill_count\|\.remaining_count\|\.initial_count\|\.taker_fees\|\.maker_fees" src/
# Result: No matches found
```

**Is get_orders used in CLI?**

```bash
grep -r "get_orders" src/kalshi_research/cli/
# Result: No matches found
```

---

## Current State

**Location:** `src/kalshi_research/api/models/portfolio.py:134-165`

**What we have:**
- `order_id`, `ticker`, `status` ✅ (plus optional side/action/prices/count fields as returned)

**Originally missing (now fixed):**

| Field | Type | Used? | Notes |
|-------|------|-------|-------|
| `initial_count` | int | No | Original size before fills/amendments |
| `fill_count` | int | No | Contracts filled so far |
| `remaining_count` | int | No | Contracts still resting |
| `taker_fees_dollars` | string | No | Taker fees paid |
| `maker_fees_dollars` | string | No | Maker fees paid |
| `taker_fill_cost` | int | No | Cost of taker fills |
| `maker_fill_cost` | int | No | Cost of maker fills |
| `taker_fill_cost_dollars` | string | No | Cost of taker fills (dollars) |
| `maker_fill_cost_dollars` | string | No | Cost of maker fills (dollars) |
| `last_update_time` | datetime | No | Last modification |
| `client_order_id` | string | No | Client-specified ID |

---

## Risk Assessment

**Why P3:**
- `get_orders()` exists but isn't used in any CLI command
- Order list data isn't processed beyond returning the model
- Pure API completeness for future order management features

**When to upgrade priority:**
- If adding order management CLI commands
- If implementing order tracking/monitoring features

---

## Fix (Optional - For API Completeness)

```python
class Order(BaseModel):
    # Existing fields...

    # Add for completeness:
    initial_count: int | None = None
    fill_count: int | None = None
    remaining_count: int | None = None
    taker_fees_dollars: str | None = None
    maker_fees_dollars: str | None = None
    taker_fill_cost: int | None = None
    maker_fill_cost: int | None = None
    taker_fill_cost_dollars: str | None = None
    maker_fill_cost_dollars: str | None = None
    last_update_time: str | None = None
    client_order_id: str | None = None
```

---

## Test Plan

- [x] Add fields to model (optional)
- [x] Fields are optional (None default)
- [x] Existing tests pass unchanged

---

## Related

- BUG-066: Fill model missing fields (similar pattern)
