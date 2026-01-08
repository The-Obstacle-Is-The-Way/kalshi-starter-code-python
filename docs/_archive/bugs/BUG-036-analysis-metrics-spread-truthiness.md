# BUG-036: `kalshi analysis metrics` spread miscomputed when bid/ask is `0` (P4)

**Priority:** P4 (Incorrect analytics display)
**Status:** ✅ Fixed (2026-01-07)
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Checklist Ref:** CODE_AUDIT_CHECKLIST.md Section 15 (Silent Fallbacks)

---

## Summary

`kalshi analysis metrics <TICKER>` could show `Spread = 0¢` for snapshots where `yes_bid == 0`, even when
`yes_ask > 0`. This silently understates spreads for unpriced / partially priced markets.

---

## Root Cause

In `src/kalshi_research/cli.py`, spread was computed with a truthiness guard:

```python
spread = price.yes_ask - price.yes_bid if price.yes_ask and price.yes_bid else 0
```

Since `0` is falsy, this collapsed valid `0` values into the fallback path.

---

## Fix Applied

- Compute spread unconditionally: `spread = price.yes_ask - price.yes_bid`

---

## Acceptance Criteria

- [x] Spread uses `yes_ask - yes_bid` even when bid or ask is `0`
- [x] Unit test asserts `yes_bid=0, yes_ask=2` renders `Spread = 2¢`

---

## Regression Test

- `tests/unit/test_cli_extended.py::test_analysis_metrics`
