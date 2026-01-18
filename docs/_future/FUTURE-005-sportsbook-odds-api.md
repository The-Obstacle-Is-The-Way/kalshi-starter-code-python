# FUTURE-005: Sportsbook Odds API

**Status:** Idea (not started)
**Priority:** Medium (high value for sports markets only)
**Effort:** Medium
**Cost:** Free to Low (aggregator APIs available)

---

## Problem

Kalshi has sports markets (game outcomes, player props). Legal sportsbooks (DraftKings, FanDuel, BetMGM) price these same events with deep liquidity and sophisticated models.

Sportsbook odds are a strong signal for Kalshi sports market pricing.

## Proposed Solution

Add a sportsbook odds provider that:

1. Fetches odds from major sportsbooks via aggregator API
2. Converts odds formats (American, decimal) to probabilities
3. Compares against Kalshi sports market pricing

### MVP Scope

```bash
# Compare Kalshi sports market to sportsbook consensus
kalshi sportsbook compare <KALSHI_TICKER>

# Show sportsbook odds for an event
kalshi sportsbook odds "Lakers vs Celtics"
```

## Data Sources

| Provider | Cost | Coverage |
|----------|------|----------|
| The Odds API | Free tier (500 req/mo) | Major US sportsbooks |
| Odds API (paid) | $20-80/mo | More sports, historical |
| BetQL, Action Network | Subscription | Analysis + odds |

**Recommendation:** Start with The Odds API free tier for validation.

## Why Medium Priority

**Pros:**
- Sportsbooks have sophisticated pricing models
- Free/cheap aggregator APIs exist
- Direct probability comparison

**Cons:**
- Only useful for sports markets
- Kalshi sports markets may be thin
- Timing differences (sportsbooks update rapidly)

## Implementation Notes

- The Odds API: `https://the-odds-api.com/`
- Need sport/event mapping to Kalshi tickers
- American odds to probability: `prob = 100 / (odds + 100)` for positive odds
- Consider vig removal for fair probability

## Dependencies

- None (can be built independently)
- Optional: integrate with ResearchProvider for unified context

## Open Questions

- Which sports does Kalshi actually have active markets for?
- How to map sportsbook events to Kalshi tickers?
- Store historical odds for line movement analysis?

---

## Acceptance Criteria

_To be defined when promoted to spec._
