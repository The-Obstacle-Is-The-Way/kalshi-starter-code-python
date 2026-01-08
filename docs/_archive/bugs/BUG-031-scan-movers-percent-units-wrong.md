# BUG-031: `kalshi scan movers` percent units wrong (P2)

**Priority:** P2 (Misleading output)
**Status:** ✅ Fixed (2026-01-07)
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Spec:** SPEC-010-cli-completeness.md, SPEC-003-data-layer-storage.md
**Checklist Ref:** CODE_AUDIT_CHECKLIST.md Section 17 (Floating Point)

---

## Summary

`kalshi scan movers` computed price deltas in **cents** (0–100) but formatted them as **percentages**, producing
incorrect output (e.g., a 2¢ move displayed as `200%`) and an effectively-zero threshold for “significant”
moves.

---

## Root Cause

- `PriceSnapshot.midpoint` returns a value in **cents**.
- The CLI treated `midpoint` deltas as probability deltas (0–1) and used percent formatting on them.

---

## Fix Applied

**File:** `src/kalshi_research/cli.py`

- Convert `midpoint` → probability via `PriceSnapshot.implied_probability`
- Compute `price_change` as probability delta
- Store `old_price` / `new_price` as probabilities so `.1%` formatting is correct

---

## Regression Tests Added

- `tests/unit/test_cli_extended.py::test_scan_movers_uses_probability_units`

---

## Acceptance Criteria

- [x] `scan movers` displays change and old/new prices in consistent probability units
- [x] Regression test passes

