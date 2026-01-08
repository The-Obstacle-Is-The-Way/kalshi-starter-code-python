# BUG-037: `plot_edge_histogram` treats `your_estimate=0.0` as missing (P4)

**Priority:** P4 (Incorrect visualization)
**Status:** ✅ Fixed (2026-01-07)
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Checklist Ref:** CODE_AUDIT_CHECKLIST.md Section 15 (Silent Fallbacks)

---

## Summary

`plot_edge_histogram()` could silently replace a valid `your_estimate=0.0` with a default value, biasing the
edge distribution and the reported mean.

---

## Root Cause

In `src/kalshi_research/analysis/visualization.py`, edge sizes used:

```python
(e.your_estimate or 0.5) - e.market_price
```

Even though the code already filtered `your_estimate is not None`, `0.0` is falsy and was replaced by `0.5`.

---

## Fix Applied

- Use the estimate directly after the `is not None` filter:
  - `e.your_estimate - e.market_price`

---

## Acceptance Criteria

- [x] `your_estimate=0.0` is treated as a real estimate (not replaced)
- [x] Unit test asserts the histogram mean reflects the 0.0 estimate

---

## Regression Test

- `tests/unit/analysis/test_visualization.py::TestPlotEdgeHistogram.test_plot_edge_histogram_allows_zero_estimate`
