# FUTURE-006: Alternative News Sources (HN, Reddit, RSS)

**Status:** Idea (not started)
**Priority:** Low (Exa already covers most)
**Effort:** Low
**Cost:** Free

---

## Problem

Exa indexes many sources but may miss niche communities or have latency on certain platforms. Alternative sources could provide:

- **Hacker News** - Tech industry sentiment, startup news
- **Reddit** - Community-specific signals (r/politics, r/wallstreetbets, r/sportsbook)
- **RSS feeds** - Direct from authoritative sources (Fed, official blogs)

## Proposed Solution

Add alternative news providers as optional research sources:

```bash
# Search Hacker News for topic
kalshi research hn "prediction markets"

# Get Reddit sentiment for a topic
kalshi research reddit "Trump election" --subreddits politics,conservative

# Add RSS feed to tracking
kalshi news add-feed "https://federalreserve.gov/feeds/press_all.xml"
```

## Why Low Priority

1. **Exa already indexes these** - HN, Reddit, major RSS are in Exa's index
2. **Latency is acceptable** - These aren't real-time sources anyway
3. **Effort vs value** - Direct API integration adds maintenance burden

## When This Becomes Higher Priority

- If Exa pricing becomes prohibitive
- If specific subreddit/HN signals prove valuable in manual testing
- If you need real-time Reddit/HN monitoring (WebSocket)

## Implementation Notes

### Hacker News
- Official API: `https://hacker-news.firebaseio.com/v0/`
- Algolia search: `https://hn.algolia.com/api/v1/search`
- Free, no auth required

### Reddit
- Official API requires OAuth app registration
- Rate limited (60 req/min authenticated)
- Consider Pushshift for historical data (if still available)

### RSS
- Standard RSS/Atom parsing (feedparser library)
- Store in existing news tables
- Scheduled collection like Exa news

## Dependencies

- Could integrate with existing `news` module
- Optional: ResearchProvider interface for unified queries

## Open Questions

- Is the marginal value over Exa worth the maintenance?
- Which specific subreddits/HN topics are most predictive?
- Store full content or just metadata?

---

## Acceptance Criteria

_To be defined when promoted to spec._
