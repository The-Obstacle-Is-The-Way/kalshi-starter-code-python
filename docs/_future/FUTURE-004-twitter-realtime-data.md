# FUTURE-004: Twitter/X Real-Time Data

**Status:** Idea (not started)
**Priority:** Medium-High (high value, high cost)
**Effort:** Medium
**Cost:** High ($100+/month for useful access)

---

## Problem

Breaking news appears on Twitter/X before it's indexed by Exa or traditional news sources. This latency gap represents information arbitrage opportunity.

For time-sensitive markets (politics, breaking events), Twitter is often the first signal.

## Proposed Solution

Add a Twitter/X data provider that:

1. Monitors key accounts for breaking news
2. Filters by relevant keywords/topics
3. Surfaces tweets that may affect tracked markets

### MVP Scope

```bash
# Track tweets from key accounts relevant to a market
kalshi twitter track <TICKER> --accounts @user1,@user2

# Collect recent tweets for tracked markets
kalshi twitter collect --hours 24

# Show tweets relevant to a thesis
kalshi twitter context <THESIS_ID>
```

## Cost Analysis

| Tier | Price | Features |
|------|-------|----------|
| Twitter API Basic | $100/mo | 10k tweets/mo read, limited search |
| Twitter API Pro | $5000/mo | Full archive search, higher limits |
| Third-party (e.g., SocialData.tools) | $50-200/mo | Varies, often better value |

**Recommendation:** Start with a third-party aggregator or defer until manual validation confirms value.

## Why Medium-High Priority

**Pros:**
- Real-time breaking news
- Key person monitoring (insiders, officials)
- Sentiment signal

**Cons:**
- Expensive
- Noisy (requires filtering)
- Rate limits
- API stability concerns (X policy changes)

## Implementation Notes

- Consider third-party APIs: SocialData, Apify, RapidAPI aggregators
- Need curated list of accounts per market category
- Keyword filtering essential to reduce noise
- May integrate with existing Exa research flow

## Dependencies

- ResearchProvider interface (SPEC-033) for clean integration

## Validation Strategy

Before building:
1. Manually monitor Twitter for 2 weeks during active trading
2. Log instances where Twitter gave signal before other sources
3. Quantify the latency advantage

## Open Questions

- Which third-party provider offers best value?
- How to curate key accounts per category (politics, crypto, sports)?
- Store tweets in DB or ephemeral?

---

## Acceptance Criteria

_To be defined when promoted to spec._
