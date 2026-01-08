# BUG-034: Portfolio Positions Hides 0¢ Mark Price (P4)

**Priority:** P4 (Low - UX correctness)
**Status:** ✅ Fixed (2026-01-07)
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Checklist Ref:** code-audit-checklist.md Section 15 (Silent Fallbacks)

---

## Summary

`kalshi portfolio positions` rendered `current_price_cents=0` as `-`, implying the price was missing.

---

## Root Cause

`src/kalshi_research/cli.py` used a truthiness check:

- `if pos.current_price_cents` treats `0` as falsy and incorrectly falls back to `-`.

---

## Impact

- Misleading UI for markets priced near 0¢ (or midpoint rounding to 0¢).
- Can hide valid mark prices and confuse users when reviewing positions.

---

## Fix Applied

- `src/kalshi_research/cli.py` now uses an explicit `is not None` check for `current_price_cents`.

---

## Regression Tests Added

- `tests/unit/test_cli_extended.py::test_portfolio_positions_shows_zero_mark_price`
