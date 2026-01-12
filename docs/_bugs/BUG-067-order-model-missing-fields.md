# BUG-067: Order Model Missing Fields

**Priority:** P2
**Status:** Open
**Found:** 2026-01-12

---

## Summary

The Order model is missing several fields documented in the Kalshi API. These are important for:
- Understanding order fill history
- Tracking fees by maker/taker
- Monitoring order modifications

---

## Current State

**Location:** `src/kalshi_research/api/models/portfolio.py` (Order class)

**Missing fields:**

| Field | Type | Description | Importance |
|-------|------|-------------|------------|
| `initial_count` | int | Original order size before fills/amendments | P2 |
| `fill_count` | int | Contracts filled so far | P2 |
| `remaining_count` | int | Contracts still resting | P2 |
| `taker_fees_dollars` | string | Fees paid on taker fills (dollars) | P2 |
| `maker_fees_dollars` | string | Fees paid on maker fills (dollars) | P2 |
| `taker_fill_cost` | int | Cost of taker fills in cents | P3 |
| `maker_fill_cost` | int | Cost of maker fills in cents | P3 |
| `taker_fill_cost_dollars` | string | Cost of taker fills in dollars | P3 |
| `maker_fill_cost_dollars` | string | Cost of maker fills in dollars | P3 |
| `last_update_time` | datetime | Last modification timestamp | P3 |
| `client_order_id` | string | Client-specified order ID | P2 |

---

## Evidence from Vendor Docs

From `docs/_vendor-docs/kalshi-api-reference.md` lines 917-932:

```markdown
### Order Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | string | Unique order identifier |
| `initial_count` | int | Original order size (before any fills or amendments) |
| `taker_fees_dollars` | string | Fees paid on taker fills (dollars) |
| `maker_fees_dollars` | string | Fees paid on maker fills (dollars) |
| `fill_count` | int | Contracts filled so far |
| `remaining_count` | int | Contracts still resting |
| `last_update_time` | datetime | Last modification timestamp |
```

---

## Impact

- Can't track partial fills properly without `fill_count`/`remaining_count`
- Can't analyze maker vs taker fees
- Can't track order modifications without `last_update_time`

---

## Fix Required

1. Add all missing fields to Order model
2. Update test fixtures
3. Verify parsing from live API

---

## Test Plan

- [ ] Add missing fields to Order model
- [ ] Update test fixtures
- [ ] Run full test suite

---

## Related

- BUG-066: Fill model missing fields
- BUG-064: Missing order safety parameters
