# DEBT-031: Floor Division in P&L Statistics

**Status:** Active
**Priority:** P3 (Low)
**Created:** 2026-01-17
**Component:** `portfolio/pnl.py`

## Summary

The `avg_win_cents` and `avg_loss_cents` statistics in `PnLSummary` use floor division (`//`) instead of `round()`, causing a systematic downward bias in reported averages.

## Location

**File:** `src/kalshi_research/portfolio/pnl.py`
**Lines:** 523-524

```python
avg_win = sum(winning) // len(winning) if winning else 0
avg_loss = abs(sum(losing) // len(losing)) if losing else 0
```

## Problem

Floor division always rounds toward negative infinity, creating a downward bias:
- `7 // 2 = 3` (should round to 4 with half-up)
- `5 // 2 = 2` (should round to 3 with half-up)

This is inconsistent with the rest of the codebase which uses `round()` for cent calculations (e.g., line 349, 366).

## Impact

- **Financial:** Minor - statistics only, doesn't affect actual P&L calculations
- **UX:** Slightly understated average win/loss displayed to user
- **Magnitude:** At most 0.5 cents per average, cumulative effect negligible

## Fix

Replace floor division with `round()`:

```python
avg_win = round(sum(winning) / len(winning)) if winning else 0
avg_loss = abs(round(sum(losing) / len(losing))) if losing else 0
```

## Testing

Add test case in `tests/unit/portfolio/test_pnl.py`:

```python
def test_avg_win_loss_uses_rounding_not_floor():
    """Average win/loss should use round() not floor division."""
    # With values [3, 4], floor gives 3, round gives 4
    # ... test implementation
```

## Risk Assessment

- **Fix Risk:** Low - isolated change, no side effects
- **Regression Risk:** Low - only affects display statistics
