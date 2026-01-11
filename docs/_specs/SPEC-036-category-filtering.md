# SPEC-036: Category Filtering for Markets

**Status:** Draft
**Priority:** P2 (Research Quality)
**Created:** 2026-01-10
**Source:** `friction.md` - "Missing Category Filter"

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
# Add event_category to markets table (denormalized for query speed)
class Market(Base):
    # ... existing fields ...
    event_category: Mapped[str | None]  # Populated from parent event

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

**Pattern Library (from `friction.md`):**
```python
CATEGORY_PATTERNS = {
    "politics": ["KXTRUMP", "KXBIDEN", "KXCONGRESS", "KXSENATE", "KXHOUSE", "KXGOV"],
    "economics": ["KXFED", "KXCPI", "KXGDP", "KXJOBS", "KXUNEMPLOY", "KXRECESSION"],
    "crypto": ["KXBTC", "KXETH", "KXCRYPTO"],
    "ai": ["KXOAI", "KXANTH", "KXGOOGLE", "KXAI"],
    "sports": ["KXNFL", "KXNBA", "KXMLB", "KXNCAA", "KXSB", "KXMVE"],
    "entertainment": ["KXOSCAR", "KXEMMY", "KXGOLDEN"],
}

def categorize_market(event_ticker: str) -> str:
    for category, patterns in CATEGORY_PATTERNS.items():
        if any(event_ticker.startswith(p) for p in patterns):
            return category
    return "other"
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

```python
async def sync_events(self, max_pages: int = 10) -> int:
    """Sync events with category data."""
    events = []
    async with KalshiPublicClient() as client:
        cursor = None
        for _ in range(max_pages):
            page, cursor = await client.get_events(cursor=cursor)
            events.extend(page)
            if not cursor:
                break

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

**File:** `src/kalshi_research/data/models.py`

```python
class Market(Base):
    # ... existing fields ...

    # Denormalized from parent event for fast filtering
    event_category: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
```

**Migration:** `alembic revision --autogenerate -m "add market event_category"`

### Phase 3: CLI Filter Support

**File:** `src/kalshi_research/cli/market.py`

```python
@app.command("list")
def market_list(
    # ... existing params ...
    category: Annotated[
        str | None,
        typer.Option(
            "--category", "-c",
            help="Filter by category: politics, economics, crypto, ai, sports, entertainment"
        ),
    ] = None,
    exclude_category: Annotated[
        str | None,
        typer.Option(
            "--exclude-category", "-X",
            help="Exclude category (e.g., --exclude-category sports)"
        ),
    ] = None,
) -> None:
```

**File:** `src/kalshi_research/cli/scan.py`

```python
@app.command("opportunities")
def scan_opportunities(
    # ... existing params ...
    category: Annotated[
        str | None,
        typer.Option("--category", "-c", help="Filter by category"),
    ] = None,
    no_sports: Annotated[
        bool,
        typer.Option("--no-sports", help="Exclude sports markets"),
    ] = False,
) -> None:
```

### Phase 4: Pattern-Based Quick Filter

**File:** `src/kalshi_research/analysis/categories.py` (new)

```python
"""Market category classification."""

from __future__ import annotations

CATEGORY_PATTERNS: dict[str, list[str]] = {
    "politics": [
        "KXTRUMP", "KXBIDEN", "KXCONGRESS", "KXSENATE", "KXHOUSE",
        "KXGOV", "KXPRES", "KXELECT", "KXPOTUS", "KXVP",
    ],
    "economics": [
        "KXFED", "KXCPI", "KXGDP", "KXJOBS", "KXUNEMPLOY",
        "KXRECESSION", "KXRATE", "KXINFLATION", "KXSP500",
    ],
    "crypto": ["KXBTC", "KXETH", "KXCRYPTO", "KXBITCOIN"],
    "ai": ["KXOAI", "KXANTH", "KXGOOGLE", "KXAI", "KXCHATGPT"],
    "sports": [
        "KXNFL", "KXNBA", "KXMLB", "KXNCAA", "KXSB", "KXMVE",
        "KXNHL", "KXSOCCER", "KXTENNIS", "KXGOLF",
    ],
    "entertainment": ["KXOSCAR", "KXEMMY", "KXGOLDEN", "KXMOVIE"],
    "tech": ["KXAPPL", "KXGOOG", "KXMETA", "KXMSFT", "KXTSLA"],
    "weather": ["KXWEATHER", "KXHURRICANE", "KXTEMP"],
}


def classify_by_event_ticker(event_ticker: str) -> str:
    """Classify market category by event ticker pattern."""
    upper = event_ticker.upper()
    for category, patterns in CATEGORY_PATTERNS.items():
        if any(upper.startswith(p) for p in patterns):
            return category
    return "other"


def get_category_patterns(category: str) -> list[str]:
    """Get event ticker patterns for a category."""
    return CATEGORY_PATTERNS.get(category.lower(), [])


def list_categories() -> list[str]:
    """List available categories."""
    return list(CATEGORY_PATTERNS.keys())
```

### Phase 5: Sync Integration

**File:** `src/kalshi_research/cli/data.py`

```python
@app.command("sync-events")
def sync_events(
    db_path: Annotated[Path, ...] = DEFAULT_DB_PATH,
    max_pages: Annotated[int, ...] = 10,
) -> None:
    """Sync events with category data."""
    # ... implementation ...
```

Update `sync-markets` to also populate `event_category`:
```python
async def _sync_markets():
    # After syncing markets, join with events to populate category
    await session.execute(
        update(Market)
        .where(Market.event_category.is_(None))
        .values(
            event_category=select(Event.category)
            .where(Event.event_ticker == Market.event_ticker)
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

-- Add denormalized category to markets table
ALTER TABLE markets ADD COLUMN event_category TEXT;
CREATE INDEX ix_markets_event_category ON markets(event_category);

-- Populate from events
UPDATE markets
SET event_category = (
    SELECT category FROM events WHERE events.event_ticker = markets.event_ticker
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
| `data/models.py` | Add `event_category` to Market model |
| `data/fetcher.py` | Enhance event sync with category |
| `cli/data.py` | Add `sync-events` command |
| `cli/market.py` | Add `--category`, `--exclude-category` |
| `cli/scan.py` | Add `--category`, `--no-sports` |
| `alembic/versions/` | Migration for new column |
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
