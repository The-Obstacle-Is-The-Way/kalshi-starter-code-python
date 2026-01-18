# DEBT-031: Floor Division in P&L Statistics

**Status:** ✅ Archived - Fixed (half-up rounding)
**Priority:** P3 (Low)
**Created:** 2026-01-17
**Archived:** 2026-01-18
**Component:** `portfolio/pnl.py`

## Summary

The `avg_win_cents` and `avg_loss_cents` statistics in `PnLSummary` used floor division (`//`), which:

- Truncated `avg_win_cents` downward (for positive values).
- Rounded `avg_loss_cents` away from zero (because the mean of negative ints is negative, and `//` floors).

## Location

**File:** `src/kalshi_research/portfolio/pnl.py`
**Lines:** 533-534

```python
avg_win = self._round_div_half_up(sum(winning), len(winning)) if winning else 0
avg_loss = abs(self._round_div_half_up(sum(losing), len(losing))) if losing else 0
```

## Problem

Floor division always rounds toward negative infinity.

For wins (positive), this truncates the average downward:
- `7 // 2 = 3` (should round to 4 with half-up)
- `5 // 2 = 2` (should round to 3 with half-up)

For losses (negative), this can inflate loss magnitude:
- `(-4) // 3 = -2` (true mean is `-1.333...`, should round to `-1` with half-up)

## Impact

- **Financial:** Minor - statistics only, doesn't affect actual P&L calculations
- **UX:** Understated `avg_win_cents` and can overstate `avg_loss_cents` (loss magnitude).
- **Magnitude:** At most 1¢ per reported average (integer output).

## Fix

Replace floor division with half-up rounding on integer division.

```python
avg_win = self._round_div_half_up(sum(winning), len(winning)) if winning else 0
avg_loss = abs(self._round_div_half_up(sum(losing), len(losing))) if losing else 0
```

## Testing

Covered by `tests/unit/portfolio/test_pnl.py::TestPnLCalculatorRealized::test_summary_with_trades_rounds_avg_win_and_loss_half_up`.

## Risk Assessment

- **Fix Risk:** Low - isolated change, no side effects
- **Regression Risk:** Low - only affects display statistics
