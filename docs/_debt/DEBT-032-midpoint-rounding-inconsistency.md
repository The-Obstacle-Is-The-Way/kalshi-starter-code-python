# DEBT-032: Midpoint Rounding Inconsistency

**Status:** Active
**Priority:** P3 (Low)
**Created:** 2026-01-17
**Component:** `portfolio/syncer.py`, `analysis/scanner.py`, `cli/scan.py`

## Summary

Midpoint price calculation uses different rounding strategies across the codebase:
- `syncer.py`: `(bid + ask + 1) // 2` (always rounds up)
- `scanner.py` / `cli/scan.py`: `(bid + ask) / 2` (true division, float result)

## Locations

### Round-up pattern (syncer.py:454,457)
```python
# Mark price = midpoint of bid/ask
if pos.side == "yes":
    mark_price = (yes_bid + yes_ask + 1) // 2
else:
    mark_price = (no_bid + no_ask + 1) // 2
```

### True division pattern (scanner.py:238, cli/scan.py:108)
```python
midpoint = (yes_bid + yes_ask) / 2
midpoint = (bid + ask) / 2
```

## Analysis

The `+1` trick in syncer.py is a common idiom for "round half up" with integers:
- `(50 + 51 + 1) // 2 = 51` (rounds up)
- `(50 + 52 + 1) // 2 = 51` (no effect on even sums)

This creates a **systematic upward bias** in mark prices.

### Intentional or Bug?

**Likely intentional** - for mark-to-market calculations, being slightly conservative (higher mark price = higher unrealized P&L for long positions) provides a buffer. However, this is **undocumented**.

### Impact

- **Financial:** Minor - affects unrealized P&L display only, not realized
- **Magnitude:** At most 0.5 cents per position
- **Direction:** Unrealized P&L slightly overstated for long YES positions

## Options

### Option A: Document as intentional (Recommended)
Add a comment explaining the conservative rounding choice:
```python
# Round up for conservative mark-to-market (avoids understating unrealized P&L)
mark_price = (yes_bid + yes_ask + 1) // 2
```

### Option B: Standardize to banker's rounding
Change to `round()` for consistency with DEBT-025 policy:
```python
mark_price = round((yes_bid + yes_ask) / 2)
```

### Option C: Create shared helper
Add `midpoint_cents(bid: int, ask: int) -> int` to `api/models/pricing.py` and use everywhere.

## Recommendation

**Option A** - Document as intentional. The conservative bias is reasonable for unrealized P&L calculations. No code change needed, just add a comment.

## Testing

No new tests needed if Option A chosen. For Option B/C, verify unrealized P&L calculations don't change unexpectedly.
