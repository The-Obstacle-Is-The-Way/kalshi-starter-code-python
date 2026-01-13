# DEBT-020: Kalshi Market Discovery Gaps (Keyword Search, Special States)

**Priority:** P2 (Blocks market research workflows)
**Status:** Open
**Found:** 2026-01-12
**Source:** Live testing - failed to find `KXOAIHARDWARE` market via API

---

## Summary

When attempting to find the "What kind of device will Jony Ive and OpenAI announce?" market (`KXOAIHARDWARE`), the following issues were observed:

1. **Direct ticker lookup returned 404** - Market exists on web UI but not via API
2. **Keyword search not possible** - No way to search markets by title/description
3. **Event pagination didn't surface it** - Market not found in any event listing

The market URL works in browser (`kalshi.com/markets/kxoaihardware/...`) but the API returns no results.

---

## Root Cause Analysis

### Issue 1: No Keyword Search Endpoint

**Current state:** To find a market, you must know either:
- The exact ticker (e.g., `KXOAIHARDWARE`)
- The event ticker
- The series ticker

**Missing:** There is no `/search` or keyword-based market lookup endpoint exposed in our client.

**SSOT:** `src/kalshi_research/api/client.py` - no `search_markets(query: str)` method

### Issue 2: Market State Filtering

Some markets may be in special states not returned by default API queries:
- Markets with `status != "open"` (but not yet `settled`)
- Markets in specific categories excluded from default listings
- Markets only accessible via specific event/series paths

**SSOT:** `docs/_vendor-docs/kalshi-api-reference.md` - need to verify available status filters

### Issue 3: Incomplete Event/Market Pagination

When paginating through events and markets, we may be missing markets that:
- Are in "multivariate" events (excluded from `/events`, require `/events/multivariate`)
- Have no recent activity (sorted to end of pagination)
- Are in categories we don't query

**Related spec:** SPEC-029 (Kalshi Endpoint Coverage) addresses multivariate events

---

## Impact

- **Research friction:** User sees market on Kalshi website but can't analyze it via CLI
- **Thesis tracking:** Can't track theses on markets we can't look up
- **Scanner gaps:** Scanner can't find markets that API doesn't surface

---

## Workarounds (Current)

1. **Manual URL parsing:** Extract ticker from Kalshi web URL, construct API path manually
2. **Web scraping:** Not recommended, violates ToS
3. **Broader pagination:** Fetch more pages (expensive, slow)

---

## Fix Path

### The Real Fix: SPEC-029 / SPEC-037 (API Coverage)

**This is already planned.** The root cause is incomplete API coverage, not missing local search.

Per SPEC-029 and SPEC-037:
- `GET /events/multivariate` - for multivariate events (excluded from `/events`)
- `GET /series` - for series-based discovery
- Full `GET /markets` filter support (status, category, etc.)
- Structured targets browsing

Once we sync comprehensive data, local keyword search becomes trivially useful.

### Why "Local DB Search" Alone is NOT the Fix

```
Problem: KXOAIHARDWARE wasn't in local DB because API never returned it.
         Local search on incomplete data = useless workaround.

Fix:     Get comprehensive data FIRST (SPEC-029/037), then local search works.
```

### Optional Enhancement: Local Keyword Search (Post-SPEC-029)

After SPEC-029 is implemented and we have comprehensive synced data:
- Simple `SELECT * FROM markets WHERE title LIKE '%keyword%'` is sufficient
- FTS5 only needed if performance becomes an issue (unlikely)

---

## Acceptance Criteria

- [ ] Can find `KXOAIHARDWARE` via CLI given only "Jony Ive OpenAI" as input
- [ ] Scanner doesn't miss markets due to API gaps
- [ ] Clear error messages when market exists on web but not via API

---

## Cross-References

| Item | Relationship |
|------|--------------|
| **SPEC-029** | **THE FIX** - Kalshi endpoint coverage strategy |
| **SPEC-037** | **THE FIX** - Series discovery (Phase 1 of SPEC-029) |
| SPEC-031 | Scanner quality profiles - affected by discovery gaps |
| DEBT-015 | Missing API endpoints - overlapping concerns |
| `_vendor-docs/kalshi-api-reference.md` | SSOT for available endpoints |

**Resolution:** This debt is resolved by implementing SPEC-029/037. No separate fix needed.

---

## Investigation Notes (2026-01-12)

```python
# Direct lookup - 404
GET /markets/KXOAIHARDWARE -> 404

# Event search - not found
GET /events?status=open (paginated 20 pages) -> no KXOAIHARDWARE-related event

# The market EXISTS on kalshi.com/markets/kxoaihardware
# But API doesn't return it - possible causes:
# 1. Special market state
# 2. Category exclusion
# 3. API bug
# 4. Regional restriction
```
