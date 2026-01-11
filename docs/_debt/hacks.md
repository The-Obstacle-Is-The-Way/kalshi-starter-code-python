# Hacks, Workarounds & Technical Debt

This document catalogs known hacky implementations, backwards compatibility concerns, and places where we've added complexity that may not be necessary. **This is a living document** - update it as issues are discovered or resolved.

---

## Priority Legend

| Priority | Meaning |
|----------|---------|
| **P0** | Breaking/blocking - fix immediately |
| **P1** | High impact - should fix soon |
| **P2** | Medium impact - fix when convenient |
| **P3** | Low impact - nice to have |

---

## 1. Missing API Features (Unnecessary Complexity)

### 1.1 Missing `/series` Endpoint Implementation [P1]

**Location:** `src/kalshi_research/api/client.py`

**Problem:** We don't implement `GET /series` with its `category` and `tags` query parameters, even though Kalshi provides this as the **intended** way to discover markets by category.

**Current Workaround:**
- `src/kalshi_research/analysis/categories.py` uses hardcoded ticker prefix matching (e.g., "KXTRUMP" → "Politics")
- CLI commands iterate all events and filter client-side by `event.category`

**Why It's Hacky:**
1. Ticker prefixes can change without notice
2. Requires maintaining a manual mapping that can drift from Kalshi's actual categories
3. More API calls than necessary (fetch everything, filter locally)

**Kalshi's Intended Pattern:**
```
GET /search/tags_by_categories     # Discover available categories
GET /series?category=Politics      # Get series in that category
GET /markets?series_ticker=...     # Get markets for those series
```

**Fix:** Implement `get_series()` method in `KalshiPublicClient` with `category`, `tags`, `include_volume` parameters.

**References:**
- [Kalshi Series List Docs](https://docs.kalshi.com/api-reference/market/get-series-list)
- [Tags by Categories Docs](https://docs.kalshi.com/api-reference/search/get-tags-for-series-categories)

---

### 1.2 Missing `/search/tags_by_categories` Endpoint [P2]

**Location:** Not implemented

**Problem:** We don't implement the endpoint that returns all available categories and their tags.

**Current Workaround:** Hardcoded `CATEGORY_ALIASES` dict in `categories.py`.

**Why It's Hacky:** If Kalshi adds/renames categories, we won't know until users report issues.

**Fix:** Implement `get_tags_by_categories()` and optionally cache the result.

---

### 1.3 Missing `/search/filters_by_sport` Endpoint [P3]

**Location:** Not implemented

**Problem:** For sports-specific filtering, Kalshi provides a dedicated endpoint with sport-specific filters.

**Current Workaround:** Using `--no-sports` flag with category filtering or `mve_filter`.

**Why It's Hacky:** Not really hacky, but we're missing sports-specific filtering granularity (e.g., filter by specific sport, league, team).

---

## 2. Backwards Compatibility Concerns

### 2.1 Kalshi API Field Deprecations (Jan 15, 2026) [P0]

**Location:** `src/kalshi_research/api/models/market.py:71-96`

**Problem:** Kalshi is removing cent-denominated fields on Jan 15, 2026:
- `yes_bid`, `yes_ask`, `no_bid`, `no_ask`, `last_price` (use `*_dollars` instead)
- `liquidity` (use `liquidity_dollars`)
- `tick_size` (use `price_level_structure`)

**Current State:** We have computed properties that prefer dollar fields and fall back to legacy fields. After Jan 15, the fallbacks will never trigger.

**Why It's Potentially Confusing:**
1. Code still references deprecated fields
2. Validators handle edge cases (negative liquidity) that won't exist post-deprecation
3. Comments say "DEPRECATED" but the fields still exist in the model

**Fix (Post Jan 15):**
1. Remove deprecated field definitions from `Market` model
2. Remove fallback logic from computed properties
3. Simplify `handle_deprecated_liquidity` validator

---

### 2.2 Orderbook Format Backwards Compatibility [P2]

**Location:** `src/kalshi_research/api/models/orderbook.py:29-95`

**Problem:** Orderbook model supports both cents and dollars formats with complex fallback logic.

**Current State:**
```python
# Each level is [price_cents, quantity] - DEPRECATED Jan 15, 2026
yes: list[tuple[int, int]] | None = None
no: list[tuple[int, int]] | None = None
yes_dollars: list[tuple[str, int]] | None = None
no_dollars: list[tuple[str, int]] | None = None
```

**Why It's Confusing:** Four fields for the same data, with computed properties that pick the "right" one.

**Fix (Post Jan 15):** Remove `yes`/`no` fields, keep only `*_dollars` fields.

---

### 2.3 Portfolio Positions Response Key Fallback [P3]

**Location:** `src/kalshi_research/api/client.py:581-585`

**Problem:**
```python
# NOTE: Kalshi returns `market_positions` (and `event_positions`). Older docs/examples may
# reference `positions`, so keep a fallback for compatibility.
raw = data.get("market_positions") or data.get("positions") or []
```

**Why It's Confusing:** The fallback to `positions` may never be needed if Kalshi consistently returns `market_positions`.

**Fix:** Verify Kalshi always returns `market_positions`, then remove fallback.

---

### 2.4 Thesis Storage Legacy Dict Format [P3]

**Location:** `src/kalshi_research/research/thesis.py:324`

**Problem:**
```python
# Legacy dict format: {"<id>": {...}, ...}
```

**Why It's There:** Migration support for old thesis storage format.

**Fix:** After confirming no users have legacy format, remove migration code.

---

## 3. Hardcoded Patterns That Could Drift

### 3.1 Category Ticker Prefix Mapping [P1]

**Location:** `src/kalshi_research/analysis/categories.py:16-57`

**Problem:** Hardcoded mapping of ticker prefixes to categories:
```python
CATEGORY_PATTERNS: dict[str, list[str]] = {
    "Politics": ["KXTRUMP", "KXBIDEN", "KXCONGRESS", ...],
    "Sports": ["KXNFL", "KXNBA", "KXMLB", ...],
    ...
}
```

**Why It's Hacky:**
1. Kalshi can create new ticker prefixes without notice
2. Categories can be renamed or merged
3. No single source of truth - we're guessing based on observation

**Better Approach:** Use `GET /series?category=...` instead of ticker prefix matching.

---

### 3.2 Category Aliases [P3]

**Location:** `src/kalshi_research/analysis/categories.py:63-79`

**Problem:** Hardcoded CLI aliases:
```python
CATEGORY_ALIASES: dict[str, str] = {
    "pol": "Politics",
    "econ": "Economics",
    ...
}
```

**Why It's Minor:** These are convenience aliases for CLI users, not API integration. Low risk of drift.

---

## 4. Data Sync Strategy Considerations

### 4.1 Events → Markets Category Denormalization [OK - Not Hacky]

**Location:** `src/kalshi_research/data/fetcher.py:112-113, 212-222`

**Current Approach:**
1. Sync events (which have `category` field)
2. Denormalize category onto markets via SQL UPDATE

**Assessment:** This is **NOT hacky** - it's the correct materialized view pattern. Kalshi removed `category` from Market responses but keeps it on Events. Our approach:
- Uses Events as the source of truth (correct)
- Denormalizes for efficient local queries (correct)
- Avoids repeated API calls (correct)

---

### 4.2 Database Stores Cents, API Returns Dollars [P2]

**Location:** `src/kalshi_research/data/fetcher.py:112-113`

**Comment in Code:**
```python
Uses computed properties that prefer new dollar fields over legacy cent fields.
Database continues to store cents for backwards compatibility.
```

**Why It Might Be Confusing:**
- API now primarily uses dollars (strings like "0.45")
- Database stores cents (integers like 45)
- Conversion happens in multiple places

**Fix Consideration:** After Jan 15 deprecation, consider migrating DB to store dollars to match API convention. However, cents are simpler for calculations (no floating point issues).

---

## 5. Things That Look Hacky But Aren't

### 5.1 `mve_filter` Parameter [OK]

Using `mve_filter="exclude"` to filter out multivariate/combo markets is **correct API usage**, not a hack.

### 5.2 Events-Based Category Filtering [OK]

Using `GET /events?with_nested_markets=true` and filtering by `event.category` is a **valid approach** when you want markets with their event context. It's less efficient than `/series` but not wrong.

### 5.3 Local Database for Category Queries [OK]

Building a local materialized view is the **recommended architecture** for this use case. Kalshi expects you to sync and index locally for efficient queries.

---

## 6. Checklist for New Features

Before implementing a complex workaround, verify:

- [ ] Did you check `docs/_vendor-docs/kalshi-api-reference.md`?
- [ ] Did you search the [Kalshi OpenAPI spec](https://docs.kalshi.com/openapi.yaml)?
- [ ] Did you check the [Kalshi Changelog](https://docs.kalshi.com/changelog)?
- [ ] Is there a native API parameter that does what you need?
- [ ] If you're parsing/inferring from data, is there a direct field available?

---

## 7. Resolution Tracking

| Issue | Status | Resolved In |
|-------|--------|-------------|
| 1.1 Missing `/series` endpoint | Open | - |
| 1.2 Missing `/search/tags_by_categories` | Open | - |
| 2.1 Jan 15 field deprecations | Pending (wait for date) | - |
| 3.1 Ticker prefix mapping | Open (blocked by 1.1) | - |

---

## References

- [Kalshi API Docs](https://docs.kalshi.com/welcome)
- [Kalshi OpenAPI Spec](https://docs.kalshi.com/openapi.yaml)
- [Kalshi Changelog](https://docs.kalshi.com/changelog)
- Local vendor docs: `docs/_vendor-docs/kalshi-api-reference.md`
