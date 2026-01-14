# BUG-079: Multi-Market Events Missing from Arbitrage Detection

**Priority:** P3 (Low - Feature Gap)
**Status:** ✅ Fixed
**Found:** 2026-01-13
**Verified:** 2026-01-14 - Added unit tests
**Fixed:** 2026-01-14
**Affected Code:** `CorrelationAnalyzer` in `src/kalshi_research/analysis/correlation.py` and `scan arbitrage` in `src/kalshi_research/cli/scan.py`

---

## Summary

`kalshi scan arbitrage` only performed sum-to-100% checks for events with exactly 2 priced markets, missing multi-choice
events with 3+ markets (where the YES prices should sum to ~100%).

---

## Root Cause

`CorrelationAnalyzer.find_inverse_markets()` only emits results when `len(event_markets) == 2`, and the CLI relied on
this method for `inverse_sum` opportunities.

---

## Fix

- Added `CorrelationAnalyzer.find_inverse_market_groups()` (2+ markets) to compute sum deviation for fully-priced events.
- Updated `scan arbitrage` to use grouped results when generating `inverse_sum` opportunities.

Note: The group check skips events where any market is unpriced/placeholder to avoid partial sums.

---

## Verification

- `tests/unit/analysis/test_correlation.py::TestFindInverseMarketGroups`
