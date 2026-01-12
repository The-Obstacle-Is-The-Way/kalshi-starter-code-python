# BUG-064: Missing Order Safety Parameters in `create_order()`

**Priority:** P1
**Status:** Open
**Found:** 2026-01-12

---

## Summary

The `create_order()` method is missing critical safety parameters documented in the Kalshi API. These are essential for:
- Preventing accidental position increases when closing
- Controlling order execution behavior
- Avoiding self-trades
- Managing order lifecycle

---

## Current State

**Location:** `src/kalshi_research/api/client.py` (create_order method)

**Currently supported parameters:**
- `ticker`, `side`, `action`, `count`, `price` (as yes_price in cents)
- `client_order_id` (optional)
- `expiration_ts` (optional)

**Missing safety-critical parameters:**

| Parameter | Type | Purpose | Severity |
|-----------|------|---------|----------|
| `reduce_only` | bool | **CRITICAL:** Only reduce position, never increase | P0 |
| `post_only` | bool | Maker-only order (avoid taker fees, reject if would cross) | P1 |
| `time_in_force` | enum | `fill_or_kill`, `good_till_canceled`, `immediate_or_cancel` | P1 |
| `buy_max_cost` | int | Max cost in cents (enables FOK behavior) | P2 |
| `cancel_order_on_pause` | bool | Auto-cancel if trading paused | P2 |
| `self_trade_prevention_type` | enum | `taker_at_cross` or `maker` | P2 |
| `order_group_id` | string | Link order to a group for grouped operations | P3 |

---

## Evidence from Vendor Docs

From `docs/_vendor-docs/kalshi-api-reference.md` lines 857-869:

```markdown
## Create Order Safety Parameters

`POST /portfolio/orders` supports several safety-critical parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `reduce_only` | bool | **SAFETY:** Only reduce position, never increase. Use for closing trades. |
| `post_only` | bool | Maker-only order (avoid taker fees, reject if would cross) |
| `time_in_force` | enum | `fill_or_kill`, `good_till_canceled`, `immediate_or_cancel` |
```

---

## Risk

**Without `reduce_only`:**
- A "close position" order could accidentally INCREASE the position if side is wrong
- User intends to sell 10 contracts to close, but ends up buying 10 more
- Real money loss potential

**Without `post_only`:**
- No way to ensure maker-only execution
- Unexpected taker fees on orders meant to provide liquidity

**Without `time_in_force`:**
- No FOK/IOC support for time-sensitive strategies
- Orders may rest indefinitely when immediate execution was intended

---

## Fix Required

1. Add all missing parameters to `create_order()` method signature
2. Pass them through to API request body
3. Add validation for enum types (`time_in_force`, `self_trade_prevention_type`)
4. Update type hints and docstrings
5. Add tests for new parameters

---

## Test Plan

- [ ] Add `reduce_only` parameter and test with mock
- [ ] Add `post_only` parameter and test
- [ ] Add `time_in_force` enum and parameter
- [ ] Add remaining parameters
- [ ] Integration test with demo environment

---

## Related

- BUG-065: `amend_order()` missing required fields
- DEBT-014 Section C1: Missing `/series` endpoint (part of order ecosystem)
