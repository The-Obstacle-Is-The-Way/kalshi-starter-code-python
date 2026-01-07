# BUG-029: `scan opportunities --filter close-race` returns illiquid/unpriced markets (P2)

**Priority:** P2 (Core feature produces misleading output)
**Status:** 🟡 Open
**Found:** 2026-01-07
**Spec:** SPEC-010-cli-completeness.md

---

## Summary

The “close-race” scanner currently surfaces markets with:

- `volume_24h = 0`
- Extreme spreads (often `100¢`)
- Often placeholder pricing (e.g., `yes_bid=0`, `yes_ask=100`)

This makes the output largely non-actionable and actively misleading for “find interesting markets” workflows.

---

## Reproduction

```bash
uv run kalshi scan opportunities --filter close-race --top 20
```

Example observed result pattern (from live API on 2026-01-07):

- `prob = 0.500`, `spread = 100`, `volume_24h = 0`

---

## Root Cause

`MarketScanner.scan_close_races()` computes probability as the midpoint of bid/ask:

- `(yes_bid + yes_ask) / 200`

For illiquid markets with quotes like `0/100`, the midpoint is exactly `0.5`, so they rank as “closest to 50%”
even though there is no meaningful price discovery.

---

## Impact

- “Opportunities” scans are dominated by dead/unpriced markets.
- Users can waste time and/or make incorrect decisions based on meaningless probabilities.

---

## Proposed Fix

- Add liquidity filters for close-race scanning, e.g.:
  - require `volume_24h >= N` and/or `open_interest > 0`
  - require `spread <= max_spread`
  - ignore markets with `yes_bid == 0 and yes_ask == 100` or `yes_bid == 0 and yes_ask == 0`
- Optionally, add a combined “liquid-close-race” scan preset.

---

## Acceptance Criteria

- Close-race scan returns markets with non-trivial liquidity and reasonable spreads.
- Markets with placeholder quotes (`0/100`, `0/0`) are excluded by default.

