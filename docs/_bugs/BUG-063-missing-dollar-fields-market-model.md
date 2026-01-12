# BUG-063: Missing Dollar Fields in Market Model

**Priority:** P3 (was P0 - downgraded after verification)
**Status:** Open
**Found:** 2026-01-12
**Verified:** 2026-01-12

---

## Summary

The Market model has `liquidity: int | None` field but is missing the replacement `liquidity_dollars` and `notional_value_dollars` fields.

**HOWEVER:** After careful verification, the `liquidity` field is **NEVER USED** in the codebase. Our liquidity analysis is computed from orderbook data (spread, depth, volume, open_interest) - NOT from the `market.liquidity` field.

---

## Verification Results

**Is `market.liquidity` used anywhere?**

```bash
grep -r "market\.liquidity" src/
# Result: No matches found
```

**How is liquidity computed?**

`src/kalshi_research/analysis/liquidity.py:326-390` computes a composite liquidity score from:
- Orderbook spread
- Orderbook depth (via `orderbook_depth_score()`)
- `market.volume_24h`
- `market.open_interest`

The `market.liquidity` field is **never accessed**.

---

## Current State

**Location:** `src/kalshi_research/api/models/market.py:93-133`

**What we have (but don't use):**
- `liquidity: int | None` - Field exists with validator for negative values, but NO CODE uses it

**What we're missing (nice-to-have for completeness):**
- `liquidity_dollars: str | None` - Kalshi's replacement field
- `notional_value_dollars: str | None` - Additional market metric

---

## Impact Assessment

**After Jan 15, 2026:**
- The `liquidity` field will return `None` from the API
- **NO FUNCTIONALITY BREAKS** - we don't use this field
- Our liquidity analysis continues to work (orderbook-based)

**Why P3 instead of P0:**
- No runtime breakage
- No feature degradation
- Purely a completeness issue for API parity

---

## Fix (Optional - For API Completeness)

If we want full API field coverage:

1. Add `liquidity_dollars: str | None = None` to Market model
2. Add `notional_value_dollars: str | None = None` to Market model
3. Consider removing unused `liquidity: int | None` field after Jan 15

---

## Test Plan

- [ ] Verify no tests depend on `market.liquidity`
- [ ] (Optional) Add dollar fields for completeness
- [ ] Run full test suite to confirm no breakage

---

## Lessons Learned

This bug was initially marked P0 based on vendor docs analysis without verifying actual code usage. Always grep for actual field usage before declaring a breaking change.
