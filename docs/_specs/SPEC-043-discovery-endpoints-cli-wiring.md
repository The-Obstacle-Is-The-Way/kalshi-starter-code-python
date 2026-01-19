# SPEC-043: Discovery Endpoints CLI Wiring (Resolve DEBT-042)

**Status:** Draft (Pending Senior Review)
**Priority:** P2 (Research UX - unlocks proper market discovery)
**Created:** 2026-01-19
**Owner:** Solo
**Effort:** ~2-3 days
**Resolves:** DEBT-042 (partial - Category A methods)

---

## Summary

Wire 12 implemented-but-unused API client methods into CLI commands to enable proper market discovery workflows.

These methods are **already implemented and tested** in `src/kalshi_research/api/client.py` but have **no CLI exposure**. This is a wiring task, not an implementation task.

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
| `get_events` | 500 | List/filter events with pagination | **None** |
| `get_event_metadata` | 574 | Event description, history, context | **None** |
| `get_event_candlesticks` | 579 | OHLC price history for event markets | **None** |
| `get_multivariate_events` | 630 | List multivariate event markets | **None** |
| `get_multivariate_event_collections` | 676 | List MVE collections | **None** |
| `get_multivariate_event_collection` | 708 | Single MVE collection details | **None** |
| `get_tags_by_categories` | 718 | Category → tags mapping | **None** |
| `get_filters_by_sport` | 727 | Sport-specific discovery filters | **None** |
| `get_series_list` | 765 | List all series (browse pattern step 2) | **None** |
| `get_series` | 792 | Single series details | **None** |
| `get_exchange_schedule` | 816 | Exchange hours, maintenance windows | **None** |
| `get_exchange_announcements` | 821 | System alerts, rule changes | **None** |

---

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
uv run kalshi browse series --tag "US Elections"
uv run kalshi browse series --json

# Step 3: Sports-specific filters
uv run kalshi browse sports
uv run kalshi browse sports --json
```

**Implementation:**

```python
# src/kalshi_research/cli/browse.py (new file)

@app.command("categories")
def browse_categories(json_output: bool = False):
    """List all categories and their tags (Kalshi browse pattern step 1)."""
    # Calls: client.get_tags_by_categories()

@app.command("series")
def browse_series(
    category: str | None = None,
    tag: str | None = None,
    status: str | None = None,
    json_output: bool = False,
):
    """List series, optionally filtered by category/tag (browse pattern step 2)."""
    # Calls: client.get_series_list(category=category, tag=tag, status=status)

@app.command("sports")
def browse_sports(json_output: bool = False):
    """List sport-specific discovery filters."""
    # Calls: client.get_filters_by_sport()
```

#### 2. Extend `kalshi event` Command Group

Currently `kalshi event` doesn't exist. Add it for event-level operations.

```bash
# List events with filters
uv run kalshi event list --status open --category "Politics"
uv run kalshi event list --series-ticker KXBTC --json

# Get event details
uv run kalshi event get EVENT_TICKER
uv run kalshi event get EVENT_TICKER --json

# Get event candlesticks (OHLC for all markets in event)
uv run kalshi event candlesticks EVENT_TICKER --period 1h
uv run kalshi event candlesticks EVENT_TICKER --period 1d --json
```

**Implementation:**

```python
# src/kalshi_research/cli/event.py (new file)

@app.command("list")
def list_events(
    status: str | None = None,
    series_ticker: str | None = None,
    category: str | None = None,
    limit: int = 50,
    json_output: bool = False,
):
    """List events with optional filters."""
    # Calls: client.get_events(status=status, series_ticker=series_ticker, ...)

@app.command("get")
def get_event(ticker: str, json_output: bool = False):
    """Get event metadata and details."""
    # Calls: client.get_event_metadata(ticker)

@app.command("candlesticks")
def event_candlesticks(
    ticker: str,
    period: str = "1h",  # 1m, 5m, 15m, 1h, 4h, 1d
    json_output: bool = False,
):
    """Get OHLC candlesticks for all markets in an event."""
    # Calls: client.get_event_candlesticks(ticker, period=period)
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
    json_output: bool = False,
):
    """Get series details."""
    # Calls: client.get_series(ticker, include_volume=include_volume)
```

#### 4. New `kalshi mve` Command Group (Multivariate Events)

For complex prop bets and ranked outcomes.

```bash
# List multivariate events
uv run kalshi mve list --status open
uv run kalshi mve list --json

# List MVE collections
uv run kalshi mve collections --status open
uv run kalshi mve collections --series-ticker SPORTS --json

# Get single MVE collection
uv run kalshi mve collection MVE_TICKER
uv run kalshi mve collection MVE_TICKER --json
```

**Implementation:**

```python
# src/kalshi_research/cli/mve.py (new file)

@app.command("list")
def list_mve(
    status: str | None = None,
    limit: int = 50,
    json_output: bool = False,
):
    """List multivariate events."""
    # Calls: client.get_multivariate_events(status=status, limit=limit)

@app.command("collections")
def list_mve_collections(
    status: str | None = None,
    series_ticker: str | None = None,
    json_output: bool = False,
):
    """List multivariate event collections."""
    # Calls: client.get_multivariate_event_collections(...)

@app.command("collection")
def get_mve_collection(ticker: str, json_output: bool = False):
    """Get single MVE collection details."""
    # Calls: client.get_multivariate_event_collection(ticker)
```

#### 5. New `kalshi status` Command

For operational awareness.

```bash
# Exchange status (schedule + announcements)
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

@app.command()
def status(json_output: bool = False):
    """Show exchange status (schedule + recent announcements)."""
    # Calls: client.get_exchange_schedule() + client.get_exchange_announcements()

@app.command("schedule")
def show_schedule(json_output: bool = False):
    """Show exchange schedule and maintenance windows."""
    # Calls: client.get_exchange_schedule()

@app.command("announcements")
def show_announcements(json_output: bool = False):
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
| `kalshi event get TICKER` | `get_event_metadata` | Event fundamentals |
| `kalshi event candlesticks TICKER` | `get_event_candlesticks` | Technical analysis |
| `kalshi series get TICKER` | `get_series` | Series details |
| `kalshi mve list` | `get_multivariate_events` | List MVEs |
| `kalshi mve collections` | `get_multivariate_event_collections` | List MVE collections |
| `kalshi mve collection TICKER` | `get_multivariate_event_collection` | Single MVE details |
| `kalshi status` | `get_exchange_schedule` + `get_exchange_announcements` | Operational status |
| `kalshi status schedule` | `get_exchange_schedule` | Exchange hours |
| `kalshi status announcements` | `get_exchange_announcements` | System alerts |

---

## Implementation Plan

### Phase 1: Core Discovery (Priority)

1. **`kalshi browse` commands** - Enable the official Kalshi browse pattern
   - `browse categories`
   - `browse series`
   - `browse sports`

2. **`kalshi status` command** - Operational awareness
   - Combined status view
   - Schedule subcommand
   - Announcements subcommand

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
- [ ] `kalshi status` shows schedule + announcements
- [ ] All commands support `--json` output
- [ ] Unit tests pass for all Phase 1 commands

### Phase 2

- [ ] `kalshi event list` returns paginated events
- [ ] `kalshi event get TICKER` returns event metadata
- [ ] `kalshi event candlesticks TICKER` returns OHLC data
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
2. **Large responses** - `get_events` without filters could return many results. Mitigation: default limits + pagination.

---

## References

- DEBT-042: Unused API Client Methods
- `src/kalshi_research/api/client.py` (implementation)
- `tests/unit/api/test_client*.py` (existing tests)
- Kalshi API Reference: `docs/_vendor-docs/kalshi-api-reference.md`

---

## Open Questions for Senior Review

1. **Command grouping**: Is `kalshi browse` the right name, or should it be `kalshi discover` / `kalshi find`?

2. **MVE commands**: Should multivariate events be under `kalshi mve` or nested under `kalshi event mve`?

3. **Status command**: Should `kalshi status` be top-level or under `kalshi exchange status`?

4. **Candlestick periods**: What periods should we support? Kalshi API supports: `1m`, `5m`, `15m`, `1h`, `4h`, `1d`. Default to `1h`?

5. **Pagination**: For list commands, should we auto-paginate (fetch all) or require explicit `--limit` / `--cursor`?
