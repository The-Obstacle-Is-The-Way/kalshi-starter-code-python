# BUG-021: Notebook Utils Limit Truthiness + Silent Exception Swallowing (P3)

**Priority:** P3 (Medium - Research UX / correctness)
**Status:** ✅ Fixed
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Spec:** SPEC-008-research-notebooks-backtesting.md

---

## Summary

Notebook helpers had two classic Python pitfalls:

- `limit=0` unintentionally loaded *all* markets/events due to truthiness checks.
- `setup_notebook()` swallowed matplotlib/IPython config errors silently.

---

## Root Cause

- `if limit and ...` treats `0` as “not set”.
- Broad exception handling without logging hides failures in interactive workflows.

---

## Fix Applied

- `src/kalshi_research/research/notebook_utils.py`
  - Limit checks now use explicit `is not None` logic and guard before appending results.
  - `setup_notebook()` now logs configuration failures instead of silent `pass`.

---

## Regression Tests Added

- `tests/unit/research/test_notebook_utils.py`
