# BUG-011: API Limit Parameter Exceeds Maximum (P0 - BLOCKING)

**Priority:** P0 (Critical - Blocks core functionality)
**Status:** Open
**Found:** 2026-01-07
**Spec:** SPEC-002-kalshi-api-client.md, SPEC-003-data-layer-storage.md

---

## Summary

The data sync command (`kalshi data sync-markets`) fails with a 400 Bad Request error because the code uses `limit=1000` for the events endpoint, but Kalshi's API only accepts a maximum of 200 for that endpoint.

---

## Root Cause

According to [Kalshi API documentation](https://docs.kalshi.com/api-reference/events/get-events):

| Endpoint | Max Limit |
|----------|-----------|
| `/events` | **200** |
| `/markets` | 1000 |

The code in `src/kalshi_research/data/fetcher.py` uses `limit=1000` for the events endpoint, which exceeds the API's maximum.

---

## Error Message

```
KalshiAPIError: API Error 400: {"error":{"code":"bad_request","message":"bad request"}}
```

---

## Steps to Reproduce

```bash
uv run kalshi data init
uv run kalshi data sync-markets  # FAILS
```

---

## Affected Files

1. `src/kalshi_research/data/fetcher.py` - Uses wrong limit for events
2. `src/kalshi_research/api/client.py` - May have hardcoded limits

---

## Fix Required

Change the events pagination limit from 1000 to 200 (or use cursor-based pagination properly).

```python
# Before (broken)
events = await self._client.get_events(limit=1000)

# After (fixed)
events = await self._client.get_events(limit=200)
```

---

## Acceptance Criteria

- [ ] `kalshi data sync-markets` completes successfully
- [ ] Events are fetched with proper pagination (limit=200)
- [ ] Markets are fetched (can use limit=1000)
- [ ] All data persists to database

---

## Priority Justification

**P0 (Critical)** because:
- Blocks ALL data sync functionality
- Users cannot fetch any market data
- Makes the entire research platform unusable
- Core feature from original requirements

---

## References

- [Kalshi API Events Endpoint](https://docs.kalshi.com/api-reference/events/get-events)
- [Kalshi API Rate Limits](https://docs.kalshi.com/getting_started/rate_limits)
