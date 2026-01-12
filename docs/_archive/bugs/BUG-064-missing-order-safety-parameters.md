# BUG-064: Missing Order Safety Parameters in `create_order()`

**Priority:** P2 (was P1 - downgraded after verification)
**Status:** ✅ Fixed
**Found:** 2026-01-12
**Fixed:** 2026-01-12
**Verified:** 2026-01-12

---

## Summary

The `create_order()` method was missing server-enforced safety parameters documented in the Kalshi API:
- `reduce_only`, `post_only`, `time_in_force`, etc.

**CONTEXT:** After verification:
1. **No CLI commands place orders** - the functionality exists but isn't exposed
2. **TradeExecutor wrapper exists** with client-side safety (dry-run default, limits, confirmation)
3. The missing params are API-level (server-enforced) safety which is still valuable

---

## Verification Results

**Is order placement exposed to users?**

```bash
grep -r "executor\|create_order\|place.*order" src/kalshi_research/cli/
# Result: No matches found
```

**Existing safety measures:**
- `src/kalshi_research/execution/executor.py` provides:
  - `live=False` default (dry-run mode)
  - `allow_production=False` default
  - `max_order_risk_usd=200.0` limit
  - `max_orders_per_day=25` limit
  - `require_confirmation=True`
  - Audit logging

---

## Current State

**Location:** `src/kalshi_research/api/client.py:create_order()`

**Currently supported:**
- `ticker`, `side`, `action`, `count`, `price` (as yes_price in cents)
- `client_order_id` (optional)
- `expiration_ts` (optional)
- `dry_run` (local-only, doesn't go to API)

**Added API-level parameters:**

| Parameter | Type | Purpose | Severity |
|-----------|------|---------|----------|
| `reduce_only` | bool | Only reduce position, never increase | P1 |
| `post_only` | bool | Maker-only order (avoid taker fees) | P2 |
| `time_in_force` | enum | `fill_or_kill`, `good_till_canceled`, `immediate_or_cancel` | P2 |
| `buy_max_cost` | int | Max cost in cents (enables FOK behavior) | P3 |
| `cancel_order_on_pause` | bool | Auto-cancel if trading paused | P3 |
| `self_trade_prevention_type` | enum | `taker_at_cross` or `maker` | P3 |
| `order_group_id` | string | Link order to a group | P3 |

---

## Risk Assessment

**Why P2 instead of P1:**
- No CLI commands expose order placement
- Developer-only API usage (direct client instantiation required)
- TradeExecutor provides client-side safety measures
- API-level safety is still valuable but not urgent for research platform

**When this becomes P1:**
- If/when CLI commands for trading are added
- If the platform evolves beyond research into active trading

---

## Fix Required (When Needed)

✅ Completed:
1. Added parameters to `create_order()` signature
2. Passed them through to the API request payload **only when explicitly set** (not `None`)
3. Used `Literal[...]` for `time_in_force` and `self_trade_prevention_type` (schema-aligned)
4. Updated docstrings and unit tests

---

## Fix Implemented

**Code changes:**
- `src/kalshi_research/api/client.py`
  - Added optional safety parameters to `create_order(...)`.
  - Payload now uses an `optional_fields` dict and includes keys only when the value is not `None`
    (preserves explicit `False`).

**Test coverage:**
- `tests/unit/api/test_trading.py`
  - Verifies `reduce_only`, `post_only`, `time_in_force` are passed through when provided.
  - Verifies safety params are omitted when not specified.

---

## Evidence from Vendor Docs

From `docs/_vendor-docs/kalshi-api-reference.md` lines 857-869.

**OpenAPI Verification (2026-01-12):** All 7 parameters confirmed to exist in Kalshi's live OpenAPI
spec as OPTIONAL fields on `POST /portfolio/orders`.

Example excerpt (from the request schema):
```yaml
time_in_force:
  type: string
  enum: ['fill_or_kill', 'good_till_canceled', 'immediate_or_cancel']
buy_max_cost:
  type: integer
post_only:
  type: boolean
reduce_only:
  type: boolean
self_trade_prevention_type:
  $ref: '#/components/schemas/SelfTradePreventionType'
order_group_id:
  type: string
cancel_order_on_pause:
  type: boolean
```

---

## Test Plan

- [x] Add parameters to method signature
- [x] Add unit tests for payload pass-through + omission when unset
- [ ] Add integration test with demo environment (when trading CLI is added)

---

## Related

- BUG-065: `amend_order()` missing required fields
- `src/kalshi_research/execution/executor.py` - existing client-side safety wrapper
