# BUG-064: Missing Order Safety Parameters in `create_order()`

**Priority:** P2 (was P1 - downgraded after verification)
**Status:** Open
**Found:** 2026-01-12
**Verified:** 2026-01-12

---

## Summary

The `create_order()` method is missing safety parameters documented in the Kalshi API:
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

**Location:** `src/kalshi_research/api/client.py:668-720`

**Currently supported:**
- `ticker`, `side`, `action`, `count`, `price` (as yes_price in cents)
- `client_order_id` (optional)
- `expiration_ts` (optional)
- `dry_run` (local-only, doesn't go to API)

**Missing API-level parameters:**

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

1. Add missing parameters to `create_order()` signature
2. Pass them through to API request payload
3. Add enum types for `time_in_force`, `self_trade_prevention_type`
4. Update docstrings

**Example signature after fix:**
```python
async def create_order(
    self,
    ticker: str,
    side: Literal["yes", "no"],
    action: Literal["buy", "sell"],
    count: int,
    price: int,
    *,
    client_order_id: str | None = None,
    expiration_ts: int | None = None,
    reduce_only: bool = False,
    post_only: bool = False,
    time_in_force: Literal["fill_or_kill", "good_till_canceled", "immediate_or_cancel"] | None = None,
    buy_max_cost: int | None = None,
    cancel_order_on_pause: bool = False,
    self_trade_prevention_type: Literal["taker_at_cross", "maker"] | None = None,
    order_group_id: str | None = None,
    dry_run: bool = False,
) -> OrderResponse:
```

---

## Evidence from Vendor Docs

From `docs/_vendor-docs/kalshi-api-reference.md` lines 857-869.

**OpenAPI Verification (2026-01-12):** All 7 missing parameters confirmed to exist in Kalshi's OpenAPI spec as OPTIONAL fields on `POST /portfolio/orders`. These are pass-through additions - will not break existing code.

---

## Test Plan

- [ ] Add parameters to method signature
- [ ] Unit test with respx mock
- [ ] Integration test with demo environment (when trading CLI added)

---

## Related

- BUG-065: `amend_order()` missing required fields
- `src/kalshi_research/execution/executor.py` - existing client-side safety wrapper
