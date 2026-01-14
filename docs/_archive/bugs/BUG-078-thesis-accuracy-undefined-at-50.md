# BUG-078: Thesis Accuracy Undefined at Exactly 50% Probability

**Priority:** P3 (Low - Edge Case)
**Status:** ✅ Fixed
**Found:** 2026-01-13
**Verified:** 2026-01-14 - Added unit test
**Fixed:** 2026-01-14
**Affected Code:** `Thesis.was_correct` in `src/kalshi_research/research/thesis.py`

---

## Summary

When `your_probability == 0.5`, `Thesis.was_correct` returned `False` for both YES and NO outcomes. This treated a
neutral “no-view” thesis as wrong and artificially penalized accuracy metrics.

---

## Fix

Return `None` when `your_probability == 0.5` so neutral theses are excluded from accuracy calculations.

---

## Verification

- `tests/unit/research/test_thesis.py::test_was_correct_neutral_probability_returns_none`

---

## Related

- `ThesisTracker.performance_summary()` filters by `t.was_correct is not None`
