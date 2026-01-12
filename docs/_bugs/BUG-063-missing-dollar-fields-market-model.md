# BUG-063: Missing Dollar Fields in Market Model (Jan 15, 2026 Breaking Change)

**Priority:** P0
**Status:** Open
**Found:** 2026-01-12
**Deadline:** 2026-01-15 (3 DAYS)

---

## Summary

The Market model is missing `liquidity_dollars` and `notional_value_dollars` fields. These fields REMAIN in the Kalshi API after the Jan 15, 2026 breaking change, but we have no way to capture them.

When Kalshi removes the cent-denominated `liquidity` and `notional_value` fields on Jan 15, we will **lose access to liquidity and notional value data entirely**.

---

## Current State

**Location:** `src/kalshi_research/api/models/market.py`

**What we have:**
- `liquidity: int | None` (DEPRECATED, being removed Jan 15)
- `notional_value: int | None` (DEPRECATED, being removed Jan 15)

**What we're missing:**
- `liquidity_dollars: str | None` - Liquidity in dollars (e.g., `"1234.56"`)
- `notional_value_dollars: str | None` - Notional value in dollars

---

## Evidence from Vendor Docs

From `docs/_vendor-docs/kalshi-api-reference.md` lines 959-968:

```markdown
| REMOVED (Jan 15) | REMAINS (Use This) | Format |
|------------------|-------------------|--------|
| `liquidity` | `liquidity_dollars` | String (current offer value) |
| `notional_value` | `notional_value_dollars` | String |
```

---

## Impact

**After Jan 15, 2026:**
- `market.liquidity` will return `None` (field removed from API)
- `market.notional_value` will return `None` (field removed from API)
- No alternative to get this data (missing dollar fields)

**Features affected:**
- Liquidity filtering in market scans
- Market health indicators
- Position sizing calculations

---

## Fix Required

1. Add `liquidity_dollars: str | None = None` field to Market model
2. Add `notional_value_dollars: str | None = None` field to Market model
3. Add computed properties `liquidity_cents` and `notional_value_cents` that convert dollars to cents
4. Update any code using `liquidity` to use the new dollar field

---

## Test Plan

- [ ] Add `liquidity_dollars` and `notional_value_dollars` to Market model
- [ ] Verify parsing from live API response
- [ ] Add computed property tests
- [ ] Update scanner.py if using liquidity field
- [ ] Run full test suite

---

## Related

- DEBT-014 Section C2: Jan 15, 2026 deprecation cleanup (scheduled)
- `docs/_future/TODO-00A-api-verification-post-deadline.md`
