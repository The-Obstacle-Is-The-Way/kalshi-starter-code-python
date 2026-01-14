# BUG-080: Inconsistent Midpoint Calculation Methods

**Priority:** P4 (Cosmetic)
**Status:** ✅ Fixed
**Found:** 2026-01-13
**Verified:** 2026-01-14 - Added unit test
**Fixed:** 2026-01-14
**Affected Code:** `_market_yes_price_display()` in `src/kalshi_research/cli/scan.py`

---

## Summary

`kalshi scan new-markets` displayed midpoint prices as whole cents, which could differ from `Market.midpoint` (which can
be `.5` cents). This was a display inconsistency.

---

## Fix

The display now uses `Market.midpoint` as the source of truth and prints half-cents (`x.5¢`) when needed.

---

## Verification

- `tests/unit/cli/test_scan.py::test_market_yes_price_display_shows_half_cent_midpoints`

---

## Notes

- Market calculations still use `Market.midpoint` (float).
- Orderbook midpoint is computed separately (see `src/kalshi_research/api/models/orderbook.py`), but this change aligns
  the new-markets display with `Market.midpoint`.
