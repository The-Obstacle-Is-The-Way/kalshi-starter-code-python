# BUG-038: `scan arbitrage` inverse-sum noisy for one-sided quotes (P3)

**Priority:** P3 (Noisy/misleading output)
**Status:** ✅ Fixed (2026-01-07)
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Spec:** SPEC-006-event-correlation-analysis.md, SPEC-010-cli-completeness.md
**Checklist Ref:** code-audit-checklist.md Section 15 (Silent Fallbacks)

---

## Summary

`kalshi scan arbitrage` could report `inverse_sum` opportunities for markets that do not have two-sided quotes (e.g.
`yes_bid == 0` but `yes_ask > 0`, or `yes_ask == 100` sentinel), where the bid/ask midpoint is not meaningful.

This produced large “divergence” values dominated by illiquid/no-bid markets.

---

## Evidence / Reproduction (live API)

Example pattern observed in the first page of open markets:

- `yes_bid = 0`, `yes_ask = 40`
- `yes_bid = 0`, `yes_ask = 17`

These were treated as “priced” and included in inverse-sum calculations, producing large deviations.

---

## Root Cause

`CorrelationAnalyzer.find_inverse_markets()` relies on bid/ask **midpoints** as implied probabilities, but
`_is_priced()` only excluded `0/0` and `0/100` placeholder quotes.

One-sided quotes (no-bid / no-ask) still passed the filter, even though midpoint-based price is unreliable when one
side is missing.

---

## Fix Applied

**File:** `src/kalshi_research/analysis/correlation.py`

- Tightened `_is_priced()` to require two-sided quotes:
  - `yes_bid != 0`
  - `yes_ask not in {0, 100}`
  - exclude degenerate `yes_bid == 100`
- Updated `find_arbitrage_opportunities()` to compute midpoint prices only for `_is_priced()` markets (same safety).

---

## Acceptance Criteria

- [x] Inverse-sum detection excludes markets with `yes_bid == 0`
- [x] Inverse-sum detection excludes markets with `yes_ask in {0, 100}`
- [x] Regression tests cover one-sided markets

---

## Regression Tests Added

- `tests/unit/analysis/test_correlation.py::TestFindInverseMarkets::test_excludes_unpriced_and_placeholder_markets`
  (extended to include one-sided quote cases)
- `tests/unit/analysis/test_correlation.py::TestIsPriced::test_is_priced_helper` (extended)
