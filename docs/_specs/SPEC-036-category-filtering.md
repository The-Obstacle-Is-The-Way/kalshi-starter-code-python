# SPEC-036: Category Filtering for Markets

**Status:** ✅ Implemented
**Priority:** P2 (Research Quality)
**Created:** 2026-01-10
**Implemented:** 2026-01-11
**Source:** `friction.md` - "Missing Category Filter"

---

## Implementation (SSOT)

Implemented category filtering + denormalized categories with:

- `src/kalshi_research/analysis/categories.py` (category aliases + event-ticker classification)
- `src/kalshi_research/cli/market.py` (`--category/-c`, `--exclude-category/-X`, `--event-prefix`)
- `src/kalshi_research/cli/scan.py` (`--category/-c`, `--no-sports`, `--event-prefix`)
- `src/kalshi_research/data/fetcher.py` (`sync_markets()` denormalizes `Event.category` onto `Market.category`)
- Tests:
  - `tests/unit/analysis/test_categories.py`
  - `tests/unit/cli/test_market.py`
  - `tests/unit/cli/test_scan.py`

**DB note:** We reuse the existing `markets.category` column to store the *event category* (denormalized).
No schema migration was required.

---

## Problem Statement

The market scanner is overwhelmed by sports parlay markets, making it hard to find interesting political/economics/AI markets.

**From `friction.md`:**
```
### Scanner Shows Illiquid Garbage
- `kalshi scan opportunities` returns multivariate sports markets with 0 volume and 98¢ spreads
- Need better filtering to exclude KXMVE (multivariate) markets
- Should prioritize by volume AND spread quality

### Database Sync Dominated by Sports Parlays
- `data sync-markets --max-pages 10` syncs 10,000 markets
- ~15,000 are KXMVE (multivariate sports parlays)
- Interesting political/economic markets not captured in default sync
- **Workaround:** Query API directly with `mve_filter=exclude`

### Missing Category Filter
- `markets` table has `category` column but it's empty
- Cannot filter by Politics/Economics/AI in database
- Need to use event_ticker patterns (KXFED, KXTRUMP, KXBTC, etc.)
```

**Root Cause:** The `category` field was **REMOVED** from Market responses (Jan 8, 2026). Markets no longer carry category data.

---

## API Reference

**From `docs/_vendor-docs/kalshi-api-reference.md`:**

### Breaking Change (Jan 8, 2026)
```
### Market response field removals (release Jan 8, 2026)
- `category`, `risk_limit_cents` removed from Market responses.
```

### Available Filtering Options

| Endpoint | Filter | Description |
|----------|--------|-------------|
| `GET /markets` | `mve_filter=exclude` | Exclude multivariate (sports parlays) |
| `GET /markets` | `event_ticker` | Filter by event (up to 10 comma-separated) |
| `GET /markets` | `series_ticker` | Filter by series |
| `GET /events` | - | Returns events with `category` field |
| `GET /search/tags` | - | Search tags (undocumented structure) |

### Event Model (Has Category)
```python
class Event(BaseModel):
    event_ticker: str
    series_ticker: str
    title: str
    category: str | None = None  # <-- Events still have category!
```

---

## Three Implementation Approaches

### Approach A: Event-Based Category Resolution (RECOMMENDED)

**How it works:**
1. Fetch events via `GET /events` (they have `category`)
2. Build a mapping: `event_ticker -> category`
3. Apply to markets via `market.event_ticker`
4. Cache in database for offline filtering

**Pros:**
- Uses official API data
- Categories are accurate (Kalshi-defined)
- Works offline after initial sync
- Can filter in database queries

**Cons:**
- Requires extra API call to sync events
- Category not directly on market

**Implementation:**
```python
# 1. Sync events with category
async def sync_events(client: KalshiPublicClient) -> dict[str, str]:
    events = await client.get_events()
    return {e.event_ticker: e.category or "Unknown" for e in events}

# 2. Apply to markets in DB
# Reuse existing markets.category column to store the parent event's category (denormalized).
class Market(Base):
    # ... existing fields ...
    category: Mapped[str | None]  # Populated from parent event

# 3. CLI filter
@app.command("list")
def market_list(
    category: Annotated[
        str | None,
        typer.Option("--category", "-c", help="Filter by category (politics, economics, ai, sports)"),
    ] = None,
):
    ...
```

---

### Approach B: Event Ticker Pattern Matching

**How it works:**
1. Define known patterns for categories
2. Filter markets by matching `event_ticker` prefix
3. No API calls needed - pure pattern matching

**Pros:**
- No additional API calls
- Works immediately
- Simple implementation
- Already used as workaround

**Cons:**
- Patterns may become stale
- Not exhaustive (new patterns need updates)
- User must know patterns

**Pattern Library (aligned with Kalshi's actual category names from API):**

**Verified Kalshi categories (from `GET /events`):**
- `World`
- `Climate and Weather`
- `Science and Technology`
- `Politics`
- `Economics`
- `Financials`
- `Sports`
- `Entertainment`

```python
# Keys match Kalshi's official category names exactly
CATEGORY_PATTERNS: dict[str, list[str]] = {
    "Politics": ["KXTRUMP", "KXBIDEN", "KXCONGRESS", "KXSENATE", "KXHOUSE", "KXGOV", "KXELECT"],
    "Economics": ["KXFED", "KXCPI", "KXGDP", "KXJOBS", "KXUNEMPLOY", "KXRECESSION", "KXRATE"],
    "Financials": ["KXBTC", "KXETH", "KXCRYPTO", "KXBITCOIN"],
    "Science and Technology": ["KXOAI", "KXANTH", "KXGOOGLE", "KXAI", "KXCHATGPT"],
    "Sports": [
        "KXNFL", "KXNBA", "KXMLB", "KXNCAA", "KXSB", "KXMVE",
        "KXNHL", "KXSOCCER", "KXTENNIS", "KXGOLF",
    ],
    "Entertainment": ["KXOSCAR", "KXEMMY", "KXGOLDEN", "KXMOVIE"],
    "Climate and Weather": ["KXWEATHER", "KXHURRICANE", "KXTEMP", "KXWARMING"],
    "World": ["KXWAR", "KXCONFLICT", "KXGEOPOL", "KXELONMARS", "KXNEWPOPE"],
}

# Aliases for CLI convenience (case-insensitive lookup)
CATEGORY_ALIASES: dict[str, str] = {
    "politics": "Politics",
    "pol": "Politics",
    "economics": "Economics",
    "econ": "Economics",
    "financials": "Financials",
    "finance": "Financials",
    "crypto": "Financials",
    "tech": "Science and Technology",
    "science": "Science and Technology",
    "ai": "Science and Technology",
    "sports": "Sports",
    "entertainment": "Entertainment",
    "climate": "Climate and Weather",
    "weather": "Climate and Weather",
    "world": "World",
}


def normalize_category(user_input: str) -> str:
    """Normalize user input to official Kalshi category name."""
    lower = user_input.lower()
    return CATEGORY_ALIASES.get(lower, user_input)


def classify_by_event_ticker(event_ticker: str) -> str:
    """Classify market category by event ticker pattern."""
    upper = event_ticker.upper()
    for category, patterns in CATEGORY_PATTERNS.items():
        if any(upper.startswith(p) for p in patterns):
            return category
    return "Other"
```

---

### Approach C: Search Tags API

**How it works:**
1. Use `GET /search/tags` to discover available tags
2. Map tags to categories
3. Filter markets by tags

**Pros:**
- Uses official discovery endpoint
- May provide more granular filtering

**Cons:**
- Endpoint structure undocumented
- May not map directly to categories
- Extra complexity

---

## Recommendation: Approach A + B Hybrid

**Best of both worlds:**
1. **Primary:** Sync event categories via `GET /events` (official data)
2. **Fallback:** Use pattern matching for quick local filtering
3. **CLI:** Support both `--category politics` and `--event-prefix KXTRUMP`

---

## Implementation Plan

### Phase 1: Extend Event Sync

**File:** `src/kalshi_research/data/fetcher.py`

**API Client Reference:**
- `get_events(limit=N)` → `list[Event]` (single page, no pagination)
- `get_events_page(cursor=X, limit=N)` → `tuple[list[Event], str | None]` (for manual pagination)
- `get_all_events(max_pages=N)` → `AsyncIterator[Event]` (auto-pagination)

```python
async def sync_events(self, max_pages: int = 10) -> int:
    """Sync events with category data."""
    events: list[Event] = []
    async with KalshiPublicClient() as client:
        # Use get_all_events() for automatic pagination
        page_count = 0
        async for event in client.get_all_events(limit=200, max_pages=max_pages):
            events.append(event)
            # Note: get_all_events handles pagination internally

    # Store events with category
    async with self.db.session() as session:
        for event in events:
            await session.merge(EventModel(
                event_ticker=event.event_ticker,
                series_ticker=event.series_ticker,
                title=event.title,
                category=event.category,
            ))
        await session.commit()

    return len(events)
```

### Phase 2: Add Category Column to Markets (Denormalized)

**Status:** ✅ Complete

We reuse the existing `markets.category` column to store the parent event's category (denormalized).
No migration required.

### Phase 3: CLI Filter Support

**File:** `src/kalshi_research/cli/market.py`

```python
from kalshi_research.analysis.categories import normalize_category, list_categories

@app.command("list")
def market_list(
    # ... existing params ...
    category: Annotated[
        str | None,
        typer.Option(
            "--category", "-c",
            help="Filter by category. Accepts: Politics, Economics, Financials, "
                 "'Science and Technology', Sports, Entertainment, 'Climate and Weather', World. "
                 "Aliases: pol, econ, tech, ai, crypto, climate"
        ),
    ] = None,
    exclude_category: Annotated[
        str | None,
        typer.Option(
            "--exclude-category", "-X",
            help="Exclude category (e.g., --exclude-category Sports)"
        ),
    ] = None,
) -> None:
    # Normalize user input to official category name
    if category:
        category = normalize_category(category)
    if exclude_category:
        exclude_category = normalize_category(exclude_category)
    # ... rest of implementation
```

**File:** `src/kalshi_research/cli/scan.py`

```python
from kalshi_research.analysis.categories import normalize_category

@app.command("opportunities")
def scan_opportunities(
    # ... existing params ...
    category: Annotated[
        str | None,
        typer.Option(
            "--category", "-c",
            help="Filter by category (e.g., --category ai, --category Politics)"
        ),
    ] = None,
    no_sports: Annotated[
        bool,
        typer.Option("--no-sports", help="Exclude Sports category markets"),
    ] = False,
) -> None:
    # Normalize and apply filters
    if category:
        category = normalize_category(category)
    # ... rest of implementation
```

### Phase 4: Pattern-Based Quick Filter

**File:** `src/kalshi_research/analysis/categories.py` (new)

```python
"""Market category classification.

Category names match Kalshi's official API exactly.
Aliases provide CLI convenience for common shorthand.
"""

from __future__ import annotations

# Keys match Kalshi's official category names from GET /events
CATEGORY_PATTERNS: dict[str, list[str]] = {
    "Politics": [
        "KXTRUMP", "KXBIDEN", "KXCONGRESS", "KXSENATE", "KXHOUSE",
        "KXGOV", "KXPRES", "KXELECT", "KXPOTUS", "KXVP",
    ],
    "Economics": [
        "KXFED", "KXCPI", "KXGDP", "KXJOBS", "KXUNEMPLOY",
        "KXRECESSION", "KXRATE", "KXINFLATION", "KXSP500",
    ],
    "Financials": ["KXBTC", "KXETH", "KXCRYPTO", "KXBITCOIN"],
    "Science and Technology": ["KXOAI", "KXANTH", "KXGOOGLE", "KXAI", "KXCHATGPT"],
    "Sports": [
        "KXNFL", "KXNBA", "KXMLB", "KXNCAA", "KXSB", "KXMVE",
        "KXNHL", "KXSOCCER", "KXTENNIS", "KXGOLF",
    ],
    "Entertainment": ["KXOSCAR", "KXEMMY", "KXGOLDEN", "KXMOVIE"],
    "Climate and Weather": ["KXWEATHER", "KXHURRICANE", "KXTEMP", "KXWARMING"],
    "World": ["KXWAR", "KXCONFLICT", "KXGEOPOL", "KXELONMARS", "KXNEWPOPE"],
}

# CLI-friendly aliases (case-insensitive)
CATEGORY_ALIASES: dict[str, str] = {
    "politics": "Politics",
    "pol": "Politics",
    "economics": "Economics",
    "econ": "Economics",
    "financials": "Financials",
    "finance": "Financials",
    "crypto": "Financials",
    "tech": "Science and Technology",
    "science": "Science and Technology",
    "ai": "Science and Technology",
    "sports": "Sports",
    "entertainment": "Entertainment",
    "climate": "Climate and Weather",
    "weather": "Climate and Weather",
    "world": "World",
}


def normalize_category(user_input: str) -> str:
    """Normalize user input to official Kalshi category name."""
    lower = user_input.lower()
    return CATEGORY_ALIASES.get(lower, user_input)


def classify_by_event_ticker(event_ticker: str) -> str:
    """Classify market category by event ticker pattern."""
    upper = event_ticker.upper()
    for category, patterns in CATEGORY_PATTERNS.items():
        if any(upper.startswith(p) for p in patterns):
            return category
    return "Other"


def get_category_patterns(category: str) -> list[str]:
    """Get event ticker patterns for a category (normalized)."""
    normalized = normalize_category(category)
    return CATEGORY_PATTERNS.get(normalized, [])


def list_categories() -> list[str]:
    """List available categories (official Kalshi names)."""
    return list(CATEGORY_PATTERNS.keys())
```

### Phase 5: Sync Integration

**Status:** ✅ Complete

Events are already synced as part of `kalshi data sync-markets` (it runs `sync_events()` before
`sync_markets()`), and market categories are denormalized in `DataFetcher.sync_markets()`.

Denormalize `Event.category` onto `Market.category` during market sync:
```python
async def _sync_markets():
    # After syncing markets, join with events to populate category
    await session.execute(
        update(Market)
        .where(Market.category.is_(None))
        .values(
            category=select(Event.category)
            .where(Event.ticker == Market.event_ticker)
            .scalar_subquery()
        )
    )
```

---

## CLI UX Examples

```bash
# Filter by category
kalshi market list --category politics
kalshi market list --category economics
kalshi scan opportunities --category ai

# Exclude sports (most common use case)
kalshi scan opportunities --no-sports
kalshi market list --exclude-category sports

# Combine with existing filters
kalshi scan opportunities --no-sports --min-volume 1000

# Quick filter by pattern (fallback)
kalshi market list --event-prefix KXFED
```

---

## Database Schema Changes

```sql
-- Add category to events table (if not exists)
ALTER TABLE events ADD COLUMN category TEXT;

-- Populate from events
UPDATE markets
SET category = (
    SELECT category FROM events WHERE events.ticker = markets.event_ticker
);
```

---

## Success Criteria

1. `kalshi scan opportunities --no-sports` excludes sports markets
2. `kalshi market list --category politics` shows only political markets
3. Events table has `category` populated from API
4. Markets have `event_category` for fast database filtering
5. Pattern-based fallback works without DB sync
6. All quality gates pass

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `analysis/categories.py` | **Create** - Category patterns and classification |
| `data/fetcher.py` | Denormalize `Event.category` onto `Market.category` during market sync |
| `cli/market.py` | Add `--category`, `--exclude-category` |
| `cli/scan.py` | Add `--category`, `--no-sports`, `--event-prefix` |
| `tests/unit/analysis/test_categories.py` | **Create** - Category tests |
| `tests/unit/cli/test_market.py` | Add filter tests |
| `tests/unit/cli/test_scan.py` | Add filter tests |

---

## Estimated Effort

- Category module: ~1 hour
- Database migration: ~30 minutes
- Event sync enhancement: ~1 hour
- CLI filters: ~2 hours
- Tests: ~2 hours
- Total: ~6-7 hours

---

## Future Enhancements

1. **Smart defaults:** Auto-exclude sports for research-focused users
2. **Category aliases:** `--cat=pol` expands to `--category politics`
3. **Config persistence:** Save preferred category filters in config file
4. **New market alerts by category:** `kalshi alerts new-markets --category ai`
