# FUTURE-003: Polymarket Cross-Market Arbitrage

**Status:** Idea (not started)
**Priority:** High (best signal-to-effort ratio)
**Effort:** Low-Medium
**Cost:** Free (public API)

---

## Problem

Kalshi and Polymarket often have markets on the same underlying events with different pricing. These price discrepancies represent potential arbitrage or signal opportunities.

Currently, identifying these opportunities requires manually checking both platforms.

## Proposed Solution

Add a `polymarket` CLI command group that:

1. Fetches Polymarket prices for comparable markets
2. Displays price deltas against Kalshi
3. Flags significant discrepancies

### MVP Scope

```bash
# Compare a Kalshi market to Polymarket equivalent
kalshi polymarket compare <KALSHI_TICKER>

# Scan for cross-platform arbitrage opportunities
kalshi polymarket scan --threshold 0.05
```

### Data Model

Polymarket uses a similar structure to Kalshi:
- Events contain multiple markets
- Markets have yes/no pricing
- Public REST API (no auth required for reads)

## Why High Priority

1. **Free API** - No cost barrier
2. **Direct arbitrage signal** - Price differences are actionable
3. **Similar data model** - Minimal mapping logic
4. **Validation opportunity** - Can manually validate before full integration

## Implementation Notes

- Polymarket API: `https://gamma-api.polymarket.com/`
- Need ticker/event mapping between platforms (may require fuzzy matching or manual mapping)
- Consider caching Polymarket data locally (similar to Kalshi)

## Dependencies

- None (can be built independently)

## Open Questions

- How to handle ticker mapping between platforms?
- Should we store Polymarket data in the same DB or separate?
- Real-time WebSocket vs polling for price updates?

## References

- Polymarket API docs (public)
- Similar projects: prediction-market-aggregators

---

## Acceptance Criteria

When promoted to a spec, the MVP should be considered complete when:

- [ ] `kalshi polymarket compare <KALSHI_TICKER>` prints a comparable yes/no probability snapshot for both venues.
- [ ] `kalshi polymarket scan --threshold 0.05` flags opportunities above the threshold deterministically.
- [ ] Unit tests validate mapping + threshold logic (no network).
