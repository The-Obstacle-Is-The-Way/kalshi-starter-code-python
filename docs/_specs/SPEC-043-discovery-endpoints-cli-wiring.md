# SPEC-043: Discovery Endpoints CLI Wiring (Resolve DEBT-042)

**Status:** 🟡 Ready for implementation (Senior Reviewed)
**Priority:** P2 (Research UX - unlocks proper market discovery)
**Created:** 2026-01-19
**Owner:** Solo
**Effort:** ~2-3 days
**Resolves:** DEBT-042 (partial - Category A methods)

---

## Summary

Wire 12 implemented-but-unused API client methods into CLI commands to enable proper market discovery workflows.

These methods are **already implemented and tested** in `src/kalshi_research/api/client.py` but have **no CLI exposure**. This is a wiring task, not an implementation task.

This spec also covers a small amount of **UX glue**: some endpoints require non-obvious parameters (e.g.,
event candlesticks require `series_ticker`). The CLI should hide those footguns where reasonable, without
inventing new abstractions.

---

## Problem Statement

The Kalshi API client has 12 discovery/research methods that are:
- ✅ Implemented with full error handling
- ✅ Tested with golden fixtures
- ❌ **Not wired into any CLI command**

Users cannot access these capabilities without writing Python code. This defeats the purpose of having a CLI research tool.

### Affected Methods (SSOT: `src/kalshi_research/api/client.py`)

| Method | Line | What It Does | Current CLI Access |
|--------|------|--------------|-------------------|
| `get_events` | 500 | List/filter events (single page) | **None** |
| `get_event_metadata` | 574 | Event description, history, context | **None** |
| `get_event_candlesticks` | 579 | OHLC price history for event markets | **None** |
| `get_multivariate_events` | 630 | List multivariate events (single page) | **None** |
| `get_multivariate_event_collections` | 676 | List MVE collections | **None** |
| `get_multivariate_event_collection` | 708 | Single MVE collection details | **None** |
| `get_tags_by_categories` | 718 | Category → tags mapping | **None** |
| `get_filters_by_sport` | 727 | Sport-specific discovery filters | **None** |
| `get_series_list` | 765 | List all series (browse pattern step 2) | **None** |
| `get_series` | 792 | Single series details | **None** |
| `get_exchange_schedule` | 816 | Exchange hours, maintenance windows | **None** |
| `get_exchange_announcements` | 821 | System alerts, rule changes | **None** |

---

## Senior Review Decisions (SSOT-Driven)

These replace the prior “Open Questions” section.

1. **Command grouping:** Use `kalshi browse` for category/tag/series discovery.
   - Rationale: Matches the Kalshi “browse pattern” in vendor docs and avoids confusion with `kalshi market search`
     (local DB search).

2. **Multivariate events:** Keep a dedicated `kalshi mve` group (not nested).
   - Rationale: Direct mapping to Kalshi’s “multivariate” concepts; keeps `kalshi event` focused on the common case.

3. **Status command placement:** Keep `kalshi status` top-level, but convert it into a subcommand group.
   - Backwards compatible behavior: `kalshi status` (no subcommand) continues to show `GET /exchange/status`.
   - Add: `kalshi status schedule` and `kalshi status announcements`.

4. **Candlestick intervals:** Use the existing CLI convention `--interval {1m,1h,1d}` (default `1h`).
   - SSOT: `period_interval` is **1, 60, or 1440 minutes** for series/event candlesticks.

5. **Pagination:** No auto-pagination in Phase 1.
   - Principle of least surprise: list commands fetch a single page.
   - Users control result size via `--limit` (matching existing `market list` conventions).

## Goals

1. **Complete the discovery workflow**: Enable the official Kalshi browse pattern via CLI:
   ```
   get_tags_by_categories → get_series_list → get_markets
   ```

2. **Enable event-level research**: Access event metadata and candlesticks for technical analysis.

3. **Surface operational info**: Exchange schedule and announcements for trading awareness.

4. **Multivariate market support**: Enable discovery of complex prop bets (sports, ranked outcomes).

5. **No new API implementation**: This is purely CLI wiring of existing, tested methods.

---

## Non-Goals

- No changes to API client implementation (already complete)
- No new API endpoints (everything exists)
- No database persistence for discovery data (read-only CLI)
- No trading/execution features (that's SPEC-034)

---

## Design

### CLI Command Structure

Add new commands under existing groups where logical, create new groups where needed.

#### 1. New `kalshi browse` Command Group

For category/series discovery (the official Kalshi browse pattern).

```bash
# Step 1: See what categories exist
uv run kalshi browse categories
uv run kalshi browse categories --json

# Step 2: List series in a category
uv run kalshi browse series --category "Politics"
uv run kalshi browse series --tags "US Elections"
uv run kalshi browse series --json

# Step 3: Sports-specific filters
uv run kalshi browse sports
uv run kalshi browse sports --json
```

**Implementation:**

```python
# src/kalshi_research/cli/browse.py (new file)

@app.command("categories")
def browse_categories(output_json: bool = False):
    """List all categories and their tags (Kalshi browse pattern step 1)."""
    # Calls: client.get_tags_by_categories()

@app.command("series")
def browse_series(
    category: str | None = None,
    tags: str | None = None,
    include_product_metadata: bool = False,
    include_volume: bool = False,
    output_json: bool = False,
):
    """List series, optionally filtered by category/tags (browse pattern step 2)."""
    # Calls: client.get_series_list(
    #   category=category,
    #   tags=tags,
    #   include_product_metadata=include_product_metadata,
    #   include_volume=include_volume,
    # )

@app.command("sports")
def browse_sports(output_json: bool = False):
    """List sport-specific discovery filters."""
    # Calls: client.get_filters_by_sport()
```

#### 2. Extend `kalshi event` Command Group

Currently `kalshi event` doesn't exist. Add it for event-level operations.

```bash
# List events with filters
uv run kalshi event list --status open
uv run kalshi event list --series KXBTC --limit 50 --json

# Get event details
uv run kalshi event get EVENT_TICKER
uv run kalshi event get EVENT_TICKER --json

# Get event candlesticks (OHLC for all markets in event)
uv run kalshi event candlesticks EVENT_TICKER --interval 1h
uv run kalshi event candlesticks EVENT_TICKER --interval 1d --json
```

**Implementation:**

```python
# src/kalshi_research/cli/event.py (new file)

@app.command("list")
def list_events(
    status: str | None = None,
    series: str | None = None,
    limit: int = 50,
    with_markets: bool = False,
    output_json: bool = False,
):
    """List events with optional filters."""
    # Calls: client.get_events(
    #   status=status,
    #   series_ticker=series,
    #   limit=limit,
    #   with_nested_markets=with_markets,
    # )

@app.command("get")
def get_event(ticker: str, output_json: bool = False):
    """Get event details + metadata (best-effort)."""
    # Calls:
    #   client.get_event(ticker)            # event fundamentals
    #   client.get_event_metadata(ticker)   # enrichment (images, sources)

@app.command("candlesticks")
def event_candlesticks(
    ticker: str,
    series: str | None = None,
    interval: str = "1h",  # 1m, 1h, 1d
    days: int = 7,
    start_ts: int | None = None,
    end_ts: int | None = None,
    output_json: bool = False,
):
    """Get OHLC candlesticks for all markets in an event."""
    # Calls: client.get_event_candlesticks(series_ticker=..., event_ticker=ticker, ...)
    #
    # Notes:
    # - The API path includes `series_ticker`. If not provided, derive it via client.get_event(ticker).
    # - `interval` maps to `period_interval` minutes: 1m->1, 1h->60, 1d->1440 (SSOT vendor docs).
```

#### 3. Extend `kalshi series` Command Group

Add series detail lookup.

```bash
# Get series details
uv run kalshi series get SERIES_TICKER
uv run kalshi series get SERIES_TICKER --include-volume --json
```

**Implementation:**

```python
# Add to src/kalshi_research/cli/market.py or new series.py

@app.command("get")
def get_series(
    ticker: str,
    include_volume: bool = False,
    output_json: bool = False,
):
    """Get series details."""
    # Calls: client.get_series(ticker, include_volume=include_volume)
```

#### 4. New `kalshi mve` Command Group (Multivariate Events)

For complex prop bets and ranked outcomes.

```bash
# List multivariate events
uv run kalshi mve list --limit 50
uv run kalshi mve list --json

# List MVE collections
uv run kalshi mve collections --status open
uv run kalshi mve collections --series SPORTS --json

# Get single MVE collection
uv run kalshi mve collection MVE_TICKER
uv run kalshi mve collection MVE_TICKER --json
```

**Implementation:**

```python
# src/kalshi_research/cli/mve.py (new file)

@app.command("list")
def list_mve(
    limit: int = 50,
    output_json: bool = False,
):
    """List multivariate events."""
    # Calls: client.get_multivariate_events(limit=limit)

@app.command("collections")
def list_mve_collections(
    status: str | None = None,
    associated_event_ticker: str | None = None,
    series: str | None = None,
    output_json: bool = False,
):
    """List multivariate event collections."""
    # Calls: client.get_multivariate_event_collections(
    #   status=status,
    #   associated_event_ticker=associated_event_ticker,
    #   series_ticker=series,
    # )

@app.command("collection")
def get_mve_collection(ticker: str, output_json: bool = False):
    """Get single MVE collection details."""
    # Calls: client.get_multivariate_event_collection(ticker)
```

#### 5. Extend `kalshi status` with Subcommands

For operational awareness.

```bash
# Exchange operational status (already exists; must remain backwards compatible)
uv run kalshi status
uv run kalshi status --json

# Just schedule
uv run kalshi status schedule
uv run kalshi status schedule --json

# Just announcements
uv run kalshi status announcements
uv run kalshi status announcements --json
```

**Implementation:**

```python
# src/kalshi_research/cli/status.py (new file)

#
# NOTE: `kalshi status` currently lives in src/kalshi_research/cli/__init__.py.
# To avoid a name conflict, move the existing implementation into this module and register it as a Typer sub-app:
#
#   from kalshi_research.cli.status import app as status_app
#   app.add_typer(status_app, name="status")
#
# Use a callback with invoke_without_command=True so `kalshi status` retains the existing behavior.

@app.callback(invoke_without_command=True)
def status(ctx: typer.Context, output_json: bool = False):
    """Show exchange operational status."""
    # Calls: client.get_exchange_status()

@app.command("schedule")
def show_schedule(output_json: bool = False):
    """Show exchange schedule and maintenance windows."""
    # Calls: client.get_exchange_schedule()

@app.command("announcements")
def show_announcements(output_json: bool = False):
    """Show exchange announcements."""
    # Calls: client.get_exchange_announcements()
```

---

## CLI Summary Table

| New Command | API Method | Purpose |
|-------------|------------|---------|
| `kalshi browse categories` | `get_tags_by_categories` | Browse pattern step 1 |
| `kalshi browse series` | `get_series_list` | Browse pattern step 2 |
| `kalshi browse sports` | `get_filters_by_sport` | Sports discovery |
| `kalshi event list` | `get_events` | List/filter events |
| `kalshi event get TICKER` | `get_event_metadata` (+ `get_event`) | Event fundamentals + enrichment |
| `kalshi event candlesticks TICKER` | `get_event_candlesticks` | Technical analysis |
| `kalshi series get TICKER` | `get_series` | Series details |
| `kalshi mve list` | `get_multivariate_events` | List MVEs |
| `kalshi mve collections` | `get_multivariate_event_collections` | List MVE collections |
| `kalshi mve collection TICKER` | `get_multivariate_event_collection` | Single MVE details |
| `kalshi status` | `get_exchange_status` | Operational status (existing) |
| `kalshi status schedule` | `get_exchange_schedule` | Exchange hours |
| `kalshi status announcements` | `get_exchange_announcements` | System alerts |

---

## Implementation Plan

### Phase 1: Core Discovery (Priority)

1. **`kalshi browse` commands** - Enable the official Kalshi browse pattern
   - `browse categories`
   - `browse series`
   - `browse sports`

2. **`kalshi status` subcommands** - Exchange schedule/announcements
   - Move existing `kalshi status` into a Typer sub-app (no behavior change)
   - `status schedule`
   - `status announcements`

### Phase 2: Event-Level Research

3. **`kalshi event` commands** - Event-level operations
   - `event list`
   - `event get`
   - `event candlesticks`

4. **`kalshi series get`** - Series detail lookup

### Phase 3: Multivariate Markets

5. **`kalshi mve` commands** - Complex prop bets
   - `mve list`
   - `mve collections`
   - `mve collection`

---

## Testing Strategy

Since API methods are already tested with golden fixtures, CLI tests focus on:

1. **Command registration** - Commands exist and have correct signatures
2. **Output formatting** - Table and JSON modes work correctly
3. **Error handling** - Missing tickers, API errors handled gracefully
4. **Integration** - End-to-end tests with mocked API responses

Test files:
- `tests/unit/cli/test_browse.py`
- `tests/unit/cli/test_event.py`
- `tests/unit/cli/test_mve.py`
- `tests/unit/cli/test_status.py`

---

## Acceptance Criteria

### Phase 1

- [ ] `kalshi browse categories` returns category→tags mapping
- [ ] `kalshi browse series --category X` filters correctly
- [ ] `kalshi browse sports` returns sport filters
- [ ] `kalshi status schedule` shows schedule + maintenance windows
- [ ] `kalshi status announcements` shows recent exchange announcements
- [ ] All commands support `--json` output
- [ ] Unit tests pass for all Phase 1 commands

### Phase 2

- [ ] `kalshi event list` returns events (single page)
- [ ] `kalshi event get TICKER` returns event details + metadata
- [ ] `kalshi event candlesticks TICKER` returns OHLC data (interval: 1m/1h/1d)
- [ ] `kalshi series get TICKER` returns series details
- [ ] Unit tests pass for all Phase 2 commands

### Phase 3

- [ ] `kalshi mve list` returns multivariate events
- [ ] `kalshi mve collections` returns MVE collections
- [ ] `kalshi mve collection TICKER` returns single collection
- [ ] Unit tests pass for all Phase 3 commands

### Documentation

- [ ] CLI skill doc updated with new commands
- [ ] `--help` text is clear and accurate for all commands
- [ ] Examples added to relevant docs

---

## Related Cleanup (Separate PR)

DEBT-042 also identified 9 methods to **remove** (Category C - institutional garbage):

- `get_structured_targets`, `get_structured_target`
- `get_series_fee_changes`, `get_user_data_timestamp`
- `get_milestones`, `get_milestone`, `get_milestone_live_data`, `get_live_data_batch`
- `get_incentive_programs`

This cleanup should be a separate PR after SPEC-043 is complete, to keep changes focused.

---

## Risk Assessment

**Low risk** - This is purely CLI wiring of existing, tested methods:

- No new API implementation
- No database changes
- No authentication changes
- All underlying methods have golden fixture tests

**Potential issues:**

1. **Rate limiting** - Some commands may hit rate limits if called rapidly. Mitigation: existing rate limiter in client.
2. **Large responses** - List endpoints can return many results. Mitigation: conservative default `--limit` and no
   auto-pagination.

---

## References

- DEBT-042: Unused API Client Methods
- `src/kalshi_research/api/client.py` (implementation)
- `tests/unit/api/test_client*.py` (existing tests)
- Kalshi API Reference: `docs/_vendor-docs/kalshi-api-reference.md`

---

## Notes

- `GET /events` does **not** support category filtering. Category discovery is:
  `browse categories` → `browse series --category ...` → `market list --series ...`.
- Candlestick period support for series/event endpoints is limited to `period_interval` of 1, 60, or 1440 minutes.
