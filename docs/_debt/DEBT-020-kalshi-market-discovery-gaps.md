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

## Proposed Fixes

### Phase 1: Diagnostic (P2)

Add `kalshi market search` command that:
1. Searches local DB cache by title keyword
2. Warns if market not found and suggests sync

```bash
kalshi market search "Jony Ive OpenAI"
# Returns: KXOAIHARDWARE (if in local DB)
# Or: "Not found in local DB. Run 'kalshi data sync-markets' first."
```

### Phase 2: API Coverage (P2-P3)

Per SPEC-029, add missing endpoints:
- `GET /events/multivariate` - for multivariate events
- `GET /series` - for series-based discovery
- Full `GET /markets` filter support (status, category, etc.)

### Phase 3: External Search (P3)

If Kalshi never adds keyword search:
- Index market titles in local SQLite with FTS5
- Build local full-text search over synced markets

---

## Acceptance Criteria

- [ ] Can find `KXOAIHARDWARE` via CLI given only "Jony Ive OpenAI" as input
- [ ] Scanner doesn't miss markets due to API gaps
- [ ] Clear error messages when market exists on web but not via API

---

## Cross-References

| Item | Relationship |
|------|--------------|
| SPEC-029 | Kalshi endpoint coverage - addresses multivariate events |
| SPEC-031 | Scanner quality profiles - affected by discovery gaps |
| DEBT-015 | Missing API endpoints - overlapping concerns |
| `_vendor-docs/kalshi-api-reference.md` | SSOT for available endpoints |

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
