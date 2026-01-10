# BUG-060: Duplicate Realized P&L Computation (Ignores Kalshi's Value)

**Priority:** P2 (Medium - inefficient and potentially inaccurate)
**Status:** 🟡 Closed (Not a bug / not provable from SSOT)
**Found:** 2026-01-10
**Fixed:** 2026-01-10
**Owner:** Platform

---

## Summary

This report was based on the assumption that Kalshi’s `/portfolio/positions.realized_pnl` can be treated as a complete,
authoritative “all time realized P&L” feed. That assumption is **not supported by the SSOT**:

- The OpenAPI schema defines `realized_pnl` as market-level “locked in P&L”, but does not specify whether
  `/portfolio/positions` returns closed markets (`position = 0`) or provides complete historical coverage.
- Settlements are surfaced via a separate endpoint (`GET /portfolio/settlements`) with cost basis + revenue fields.

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

We compute **realized P&L totals** from synced history (`fills + settlements`) because there is no SSOT-backed guarantee
that `market_positions[].realized_pnl` is available for all closed markets.

### The Problem

The *actual* problems were:

- Missing settlement sync (BUG-059)
- Strict FIFO that crashed on incomplete history (BUG-058)

---

## Impact

- Portfolio P&L was missing settled-market results and could crash on incomplete fills history.

---

## Resolution (Implemented Elsewhere)

See BUG-058 and BUG-059. The implementation now:

- Syncs `/portfolio/settlements` into `portfolio_settlements`
- Computes realized P&L from synced fills + settlements
- Degrades gracefully on gaps (orphan sells are skipped and surfaced as a count)

---

## Acceptance Criteria

- [x] BUG-058 fixed (no crash on incomplete fills history)
- [x] BUG-059 fixed (settlements synced and included)
- [x] Docs updated to avoid unverified claims about `realized_pnl` coverage

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
