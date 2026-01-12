# BUG-066: Fill Model Missing Fields (API Completeness)

**Priority:** P3 (was P2 - downgraded after verification)
**Status:** ✅ Fixed
**Found:** 2026-01-12
**Fixed:** 2026-01-12
**Verified:** 2026-01-12

---

## Summary

The Fill model was missing several fields from the Kalshi OpenAPI schema. However, after verification:
1. **`fill_id` = `trade_id`** - Vendor docs say they're the same, we have `trade_id`
2. **Missing fields are not used** - Only `trade_id` is referenced in codebase
3. **API completeness issue** - Not a functional bug

---

## Fix Implemented

- Expanded `Fill` in `src/kalshi_research/api/models/portfolio.py` to include optional OpenAPI fields:
  `fill_id`, `order_id`, `client_order_id`, `market_ticker`, `price`, `yes_price_fixed`,
  `no_price_fixed`, `is_taker`.
- Added unit coverage to ensure these fields parse correctly.

---

## Verification Results

**Which Fill fields are actually used?**

```bash
grep -r "\.trade_id\|\.is_taker\|\.order_id\|\.fill_id" src/
# Result: Only trade_id used in portfolio/syncer.py:235
```

**Usage:** `src/kalshi_research/portfolio/syncer.py:235`
```python
trade_id = fill.trade_id
```

---

## Current State

**Location:** `src/kalshi_research/api/models/portfolio.py:41-69`

**What we have:**
- `trade_id` ✅ (same as `fill_id` per vendor docs)
- `ticker`, `side`, `action`, `yes_price`, `no_price`, `count`, `created_time` ✅

**Missing (for API completeness):**

| Field | Type | Used? | Notes |
|-------|------|-------|-------|
| `fill_id` | string | No | Same as `trade_id` - redundant |
| `order_id` | string | No | Could be useful for order correlation |
| `yes_price_fixed` | string | No | Dollar prices |
| `no_price_fixed` | string | No | Dollar prices |
| `is_taker` | bool | No | Could be useful for fee analysis |
| `client_order_id` | string | No | Only if using client IDs |

---

## Risk Assessment

**Why P3:**
- Core functionality works with existing fields
- `trade_id` serves as `fill_id`
- Missing fields aren't used anywhere
- Pure API completeness for future features

**When to upgrade priority:**
- If implementing maker/taker fee breakdown analysis
- If implementing order→fill correlation views

---

## Fix (Optional - For API Completeness)

```python
class Fill(BaseModel):
    # Existing fields...
    trade_id: str  # Already have this

    # Add for completeness:
    fill_id: str | None = None  # Alias of trade_id
    order_id: str | None = None
    yes_price_fixed: str | None = None  # Dollar price
    no_price_fixed: str | None = None   # Dollar price
    is_taker: bool | None = None
    client_order_id: str | None = None
```

---

## Test Plan

- [x] Add fields to model (optional)
- [x] Fields are optional (None default)
- [x] Existing tests pass unchanged

---

## Related

- BUG-067: Order model missing fields (similar pattern)
