# BUG-060: Duplicate Realized P&L Computation (Ignores Kalshi's Value)

**Priority:** P2 (Medium - inefficient and potentially inaccurate)
**Status:** ✅ Fixed
**Found:** 2026-01-10
**Fixed:** 2026-01-10
**Owner:** Platform

---

## Summary

We sync `realized_pnl` from Kalshi's `/portfolio/positions` API (which is accurate and includes settlements), but then **ignore it** and recompute our own FIFO from local trades. This is:

1. **Wasteful** - duplicate computation
2. **Inaccurate** - our FIFO lacks settlements (BUG-059)
3. **Fragile** - crashes on incomplete history (BUG-058)

---

## Root Cause

### What Kalshi Provides

From `/portfolio/positions` response:
```json
{
  "market_positions": [{
    "ticker": "KXMARKET",
    "position": 34,
    "realized_pnl": 1500,        // <-- Kalshi computes this!
    "realized_pnl_dollars": "15.00",
    ...
  }]
}
```

### What We Do

**Step 1 (syncer.py):** We correctly sync this value:
```python
# syncer.py:165
existing.realized_pnl_cents = pos_data.realized_pnl or 0
```

**Step 2 (pnl.py):** We IGNORE it and recompute:
```python
# pnl.py:162 (calculate_summary_with_trades)
closed_trades = self._get_closed_trade_pnls_fifo(trades)  # <-- Recomputes!
realized = sum(closed_trades)
```

### The Problem

| Source | Includes Settlements? | Includes All History? | Crashes on Gaps? |
|--------|----------------------|----------------------|------------------|
| Kalshi's `realized_pnl` | ✅ Yes | ✅ Yes | ❌ No |
| Our FIFO computation | ❌ No (BUG-059) | ❌ No | ✅ Yes (BUG-058) |

**We're using the worse option.**

---

## Impact

1. **BUG-058 crash**: Our FIFO throws on incomplete history
2. **Inaccurate totals**: Missing settled position P&L
3. **Wasted computation**: Computing what Kalshi already provides
4. **Test complexity**: Have to mock complex FIFO scenarios

---

## Fix Plan (Implemented)

### Use Kalshi's `realized_pnl` + Settlement Records for Totals

For total realized P&L, use the value from positions (already synced):

```python
# pnl.py - calculate_summary_with_trades
def calculate_summary_with_trades(
    self, positions: list[Position], trades: list[Trade]
) -> PnLSummary:
    # For TOTAL realized P&L, use Kalshi's authoritative value
    realized_from_positions = sum(pos.realized_pnl_cents for pos in positions)

    # For per-trade STATS (win rate, avg win/loss), still use FIFO
    # but with graceful degradation (BUG-058 fix)
    try:
        closed_trades = self._get_closed_trade_pnls_fifo(trades)
    except ValueError:
        # Incomplete history - can't compute per-trade stats
        closed_trades = []
        logger.warning("Incomplete trade history; per-trade stats unavailable")

    # Stats from closed_trades, total from positions
    ...
```

For resolved markets, include `/portfolio/settlements` P&L as well (BUG-059).

---

## Acceptance Criteria

- [x] `calculate_summary_with_trades` uses `positions.realized_pnl_cents` for totals
- [x] Settlement P&L is added when `/portfolio/settlements` is synced
- [x] Per-trade FIFO no longer crashes on incomplete history (BUG-058)
- [x] `PnLSummary` includes `orphan_sells_skipped: int` for transparency
- [x] Unit tests updated
- [x] `uv run pre-commit run --all-files` passes

---

## Test Plan

```bash
uv run pytest tests/unit/portfolio/test_pnl.py -v
uv run kalshi portfolio pnl  # Should not crash
```

---

## References

- **Related:** BUG-058 (FIFO crash), BUG-059 (missing settlements)
- **API Docs:** https://docs.kalshi.com/api-reference/portfolio/get-positions
- **Key insight:** Kalshi's `realized_pnl` includes settlements; ours doesn't
