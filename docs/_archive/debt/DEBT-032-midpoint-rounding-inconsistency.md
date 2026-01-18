# DEBT-032: Midpoint Rounding Inconsistency

**Status:** ✅ Archived - Documented half-up midpoint rounding
**Priority:** P3 (Low)
**Created:** 2026-01-17
**Archived:** 2026-01-18
**Component:** `portfolio/syncer.py`, `analysis/scanner.py`, `cli/scan.py`

## Summary

Midpoint price calculation uses different rounding strategies across the codebase:
- `syncer.py`: `(bid + ask + 1) // 2` (integer midpoint; half-up when midpoint is `x.5`)
- `scanner.py` / `cli/scan.py`: `(bid + ask) / 2` (true division, float result)

## Locations

### Half-up integer pattern (`portfolio/syncer.py`)
```python
# Mark price = midpoint of bid/ask (integer cents, rounded half-up)
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

The `+1` trick in `syncer.py` is a common idiom for **round half-up** when converting an integer midpoint to an integer:
- `(50 + 51 + 1) // 2 = 51` (rounds up)
- `(50 + 52 + 1) // 2 = 51` (no effect on even sums)

This differs from `Market.midpoint` / scanner display because those flows keep midpoint as a `float` (e.g., `50.5¢`).

### Impact

- **Financial:** Only affects unrealized P&L display (mark-to-market), not realized P&L.
- **Magnitude:** Mark price differs from the true midpoint by at most **0.5¢**. When multiplied by contract count,
  unrealized P&L can shift by up to `0.5¢ * quantity` per position.

## Options

### Option A: Document as intentional (Chosen)
`PortfolioSyncer` stores mark prices as integer cents, so half-cent midpoints must be rounded. This repo's pricing policy
is **round-to-cent half-up** (DEBT-025), so `update_mark_prices()` uses half-up midpoint rounding and documents it.

### Option B: Standardize representation (Not needed)
Store midpoint prices as fixed-point dollars or sub-cent integers (larger migration; out of scope for this repo's goals).

### Option C: Create shared helper (Optional)
If additional integer-midpoint conversions appear, a small helper could reduce duplication; currently only
`PortfolioSyncer.update_mark_prices()` needs an integer midpoint.

## Recommendation

**Option A** - Document as intentional. Scanner/CLI can keep float midpoints for analysis/display, while portfolio mark
prices remain integer cents (rounded half-up) for storage + P&L math.

## Testing

Covered by `tests/unit/portfolio/test_syncer.py::test_update_mark_prices_rounds_half_up_for_half_cent_midpoints`.
