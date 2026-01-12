# BUG-066: Fill Model Missing Fields

**Priority:** P2
**Status:** Open
**Found:** 2026-01-12

---

## Summary

The Fill model in `api/models/portfolio.py` is missing several fields documented in the Kalshi API. These fields are important for:
- Proper fill identification and tracking
- Maker/taker fee analysis
- Dollar-denominated price access
- Order correlation

---

## Current State

**Location:** `src/kalshi_research/api/models/portfolio.py` (Fill class)

**Missing fields:**

| Field | Type | Description | Importance |
|-------|------|-------------|------------|
| `fill_id` | string | Unique fill identifier | P1 - Primary key |
| `order_id` | string | Parent order ID | P1 - Order correlation |
| `yes_price_fixed` | string | YES price in dollars (e.g., `"0.48"`) | P2 - Post Jan 15 |
| `no_price_fixed` | string | NO price in dollars (e.g., `"0.52"`) | P2 - Post Jan 15 |
| `is_taker` | bool | True if removed liquidity | P2 - Fee analysis |
| `client_order_id` | string | Client-provided order ID (if set) | P3 - Tracking |

---

## Evidence from Vendor Docs

From `docs/_vendor-docs/kalshi-api-reference.md` lines 421-438:

```markdown
**Response fields (per fill):**

| Field | Type | Description |
|-------|------|-------------|
| `fill_id` | string | Unique fill identifier |
| `trade_id` | string | Legacy field (same as fill_id) |
| `order_id` | string | Parent order ID |
| ...
| `yes_price_fixed` | string | YES price in dollars (e.g., `"0.48"`) |
| `no_price_fixed` | string | NO price in dollars (e.g., `"0.52"`) |
| `is_taker` | bool | True if removed liquidity |
| `client_order_id` | string | Client-provided order ID (if set) |
```

---

## Impact

- Can't uniquely identify fills (missing `fill_id`)
- Can't correlate fills to orders (missing `order_id`)
- Can't determine maker/taker status for fee analysis
- Will need dollar prices post Jan 15 deprecation

---

## Fix Required

1. Add `fill_id: str` field (primary identifier)
2. Add `order_id: str | None` field
3. Add `yes_price_fixed: str | None` and `no_price_fixed: str | None`
4. Add `is_taker: bool | None` field
5. Add `client_order_id: str | None` field
6. Update any code using fills

---

## Test Plan

- [ ] Add missing fields to Fill model
- [ ] Update test fixtures to include new fields
- [ ] Verify parsing from live API
- [ ] Update portfolio syncer if needed
- [ ] Run full test suite

---

## Related

- BUG-063: Missing dollar fields in Market model
- BUG-067: Order model missing fields
