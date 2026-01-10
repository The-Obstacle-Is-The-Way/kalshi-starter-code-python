# Codebase Bloat Analysis

**Date:** 2026-01-10
**Analyzer:** Vulture + manual inspection
**Trigger:** External code review criticism (ex-Databricks engineer)

---

## Executive Summary

| Metric | Value | Assessment |
|--------|-------|------------|
| Total Python files | 82 | Moderate |
| Total source LOC | 15,059 | Significant for scope |
| Test LOC | 15,644 | Good test coverage |
| Unused methods/functions/classes | 116 | **HIGH - needs cleanup** |
| Unused imports | 3 | Low |
| Dead code confidence | 60%+ | Many confirmed |

### Verdict

**Julian's criticism has merit.** There is measurable bloat:
- ~116 unused methods/functions/classes (Vulture 60% confidence)
- Multiple dead modules (EdgeDetector, unused notifiers, WebSocket client)
- Boilerplate duplication (16 `create_tables()` calls)
- Three data modeling patterns (dataclasses + Pydantic + SQLAlchemy)

**However:**
- Some "unused" code is intentional (notebook support, future trading features)
- The core CLI functionality works correctly
- Test coverage is good (1:1 test-to-source ratio)
- Not "absolute AI slop" - there's genuine complexity in Kalshi integration

---

## Dead Code Inventory

### TIER 1: Definitely Dead (Safe to Delete)

These have zero usage paths and provide no value.

#### `analysis/edge.py` - EdgeDetector (246 lines)
```
src/kalshi_research/analysis/edge.py:76: unused method 'detect_thesis_edge'
src/kalshi_research/analysis/edge.py:123: unused method 'detect_spread_edge'
src/kalshi_research/analysis/edge.py:163: unused method 'detect_volume_edge'
src/kalshi_research/analysis/edge.py:210: unused method 'detect_volatility_edge'
```
**Action:** Delete entire `EdgeDetector` class. Keep only `Edge` dataclass if used by notebooks.

#### `alerts/notifiers.py` - Unused Notifiers (67 lines)
```
src/kalshi_research/alerts/notifiers.py:46: unused class 'FileNotifier'
src/kalshi_research/alerts/notifiers.py:71: unused class 'WebhookNotifier'
```
**Action:** Delete `FileNotifier` and `WebhookNotifier`. Only `ConsoleNotifier` is used.

#### `research/thesis.py` - TemporalValidator (40+ lines)
```
src/kalshi_research/research/thesis.py:41: unused class 'TemporalValidator'
src/kalshi_research/research/thesis.py:56: unused method 'validate'
```
**Action:** Delete `TemporalValidator` class entirely.

#### Unused Analysis Methods
```
src/kalshi_research/analysis/metrics.py:63: unused method 'compute_spread_stats'
src/kalshi_research/analysis/metrics.py:105: unused method 'compute_volatility'
src/kalshi_research/analysis/metrics.py:171: unused method 'compute_volume_profile'
src/kalshi_research/analysis/liquidity.py:438: unused method 'max_safe_buy_size'
src/kalshi_research/analysis/scanner.py:390: unused method 'scan_all'
```
**Action:** Delete these unused methods.

### TIER 2: Intentionally Reserved (Keep with Documentation)

These exist for future features or notebook support.

#### API Trading Methods
```
src/kalshi_research/api/client.py:647: unused method 'create_order'
src/kalshi_research/api/client.py:746: unused method 'cancel_order'
src/kalshi_research/api/client.py:809: unused method 'amend_order'
```
**Decision:** KEEP - These are intentionally available for future trading features. Add comment marking them as reserved.

#### WebSocket Client (281 lines)
```
src/kalshi_research/api/websocket/client.py - Entire module unused
```
**Decision:** KEEP but document - Reserved for real-time features. Consider extracting to optional package.

#### Notebook Utilities (289 lines)
```
src/kalshi_research/research/notebook_utils.py - All functions unused in CLI
```
**Decision:** KEEP - Used by Jupyter notebooks in `notebooks/` directory.

### TIER 3: Gray Area (Evaluate Case-by-Case)

#### Exa Client Methods
```
src/kalshi_research/exa/client.py:349: unused method 'find_similar'
src/kalshi_research/exa/client.py:403: unused method 'create_research_task'
src/kalshi_research/exa/client.py:426: unused method 'wait_for_research'
```
**Decision:** These wrap Exa API endpoints that exist but aren't integrated into CLI. Either integrate or delete.

#### Unused Repository Methods
```
src/kalshi_research/data/repositories/events.py:22: unused method 'get_by_series'
src/kalshi_research/data/repositories/events.py:28: unused method 'get_by_category'
src/kalshi_research/data/repositories/markets.py:39: unused method 'get_expiring_before'
src/kalshi_research/data/repositories/prices.py:58: unused method 'get_latest_batch'
src/kalshi_research/data/repositories/prices.py:92: unused method 'delete_older_than'
src/kalshi_research/data/repositories/settlements.py:55: unused method 'get_by_result'
src/kalshi_research/data/repositories/settlements.py:71: unused method 'count_by_result'
```
**Decision:** Delete unused repository methods unless they're part of an upcoming feature.

---

## Structural Bloat

### 1. Triple Data Modeling (High Impact)

The codebase uses THREE different patterns for data models:

| Pattern | File Count | Purpose |
|---------|------------|---------|
| `@dataclass` | 19 files | Internal DTOs, analysis results |
| Pydantic `BaseModel` | 15 files | API response models |
| SQLAlchemy `Mapped[]` | 15 files | Database ORM |

**Problem:** Potential redundancy when same concept is modeled multiple times.

**Example:** Market data exists as:
- `api/models/market.py` (Pydantic) - API response
- `data/models.py` (SQLAlchemy) - DB table
- Various dataclasses in analysis modules

**Recommendation:** Audit for redundant models. Consider using Pydantic for API + dataclasses for internal, with explicit conversion.

### 2. Repeated Boilerplate (Medium Impact)

**16 calls to `await db.create_tables()`** scattered across CLI commands:
- `cli/portfolio.py`: 6 calls
- `cli/news.py`: 5 calls
- `cli/data.py`: 5 calls

```python
# Repeated pattern in every CLI command:
async with get_db() as db:
    await db.create_tables()  # Why here?
    async with db.session() as session:
        ...
```

**Recommendation:** Create a `@db_command` decorator or use CLI lifecycle hooks.

### 3. Over-Abstracted Repository Layer (Low-Medium Impact)

Repository pattern adds abstraction but many methods are unused:
- `BaseRepository` provides generic CRUD
- Specialized repositories add custom queries
- Many custom queries never called

**Recommendation:** Simplify to direct SQLAlchemy usage where repository abstraction isn't needed.

---

## Size Analysis

### Largest Files (Potential Simplification Targets)

| File | LOC | Assessment |
|------|-----|------------|
| `api/client.py` | 886 | Contains ~200 lines of unused trading methods |
| `cli/research.py` | 849 | Legitimate complexity - thesis tracking UI |
| `cli/portfolio.py` | 608 | 6x repeated `create_tables()` pattern |
| `cli/scan.py` | 564 | OK - scanner has legitimate complexity |
| `research/thesis.py` | 482 | Contains unused TemporalValidator |
| `exa/client.py` | 449 | ~100 lines of unused methods |
| `analysis/liquidity.py` | 448 | Some unused methods |
| `analysis/scanner.py` | 410 | Some unused methods |
| `analysis/correlation.py` | 393 | OK - legitimate complexity |

### Module-Level LOC

| Module | LOC | % of Total |
|--------|-----|------------|
| `cli/` | 3,357 | 22% |
| `analysis/` | 2,257 | 15% |
| `api/` | 2,100 | 14% |
| `research/` | 1,700 | 11% |
| `data/` | 1,400 | 9% |
| `exa/` | 690 | 5% |
| `portfolio/` | 600 | 4% |
| `news/` | 600 | 4% |
| `alerts/` | 400 | 3% |

---

## Recommended Cleanup Actions

### Phase 1: Quick Wins (Est. 500 LOC reduction)

1. [ ] Delete `EdgeDetector` class (keep `Edge` dataclass)
2. [ ] Delete `FileNotifier`, `WebhookNotifier` classes
3. [ ] Delete `TemporalValidator` class
4. [ ] Delete unused analysis methods (`compute_spread_stats`, etc.)
5. [ ] Delete unused repository methods
6. [ ] Remove 3 unused imports

### Phase 2: Refactoring (Est. 300 LOC reduction)

1. [ ] Create `@db_command` decorator to eliminate 16 repeated `create_tables()` calls
2. [ ] Consolidate Exa client methods (delete or integrate)
3. [ ] Review data model redundancy

### Phase 3: Strategic Decisions

1. [ ] WebSocket module - Keep as optional extra or delete?
2. [ ] Trading methods - Document as "reserved for future" or delete?
3. [ ] Notebook utils - Keep in main package or extract?

---

## False Positives (NOT Bloat)

These appear in Vulture but are **correctly** flagged as used:

### CLI Functions
All CLI functions (`@app.command()`) appear unused to Vulture because Typer's decorator pattern isn't recognized:
```
src/kalshi_research/cli/data.py:15: unused function 'data_init'
```
**Reality:** These ARE used - Typer registers them via decorator.

### Pydantic Validators
```
src/kalshi_research/api/models/event.py:29: unused method '_empty_str_to_none'
src/kalshi_research/api/models/order.py:58: unused method 'validate_limit_price'
```
**Reality:** These ARE used - Pydantic calls them via `@field_validator`.

### Model Fields
All Pydantic/dataclass field definitions appear "unused" to Vulture:
```
src/kalshi_research/api/models/candlestick.py:20: unused variable 'open_dollars'
```
**Reality:** These ARE used - they're data attributes.

---

## External Critic's Points - Assessment

| Julian's Claim | Our Assessment |
|----------------|----------------|
| "Codebase is the size of a full startup" | **Partially valid** - 15K LOC is significant but includes tests (15K) |
| "Majority is inefficient bloat" | **Exaggerated** - ~10-15% is dead code, not "majority" |
| "Using a shotgun to kill a spider" | **Partially valid** - Some over-engineering exists |
| "Low ceiling for AI-only approach" | **Fair point** - Dead code accumulated from AI generation |
| "Could do same with 1/10th complexity" | **Unlikely** - Core Kalshi integration is genuinely complex |

### What's Legitimate Complexity (NOT Bloat)

- Kalshi API client with pagination, rate limiting, auth
- Database persistence with proper async SQLite
- Multiple CLI commands with rich output
- Portfolio P&L calculations with FIFO
- Thesis tracking with state management
- News sentiment analysis pipeline

### What's Actually Bloat

- EdgeDetector never integrated
- Multiple unused notifier classes
- Unused API methods accumulating
- Repeated boilerplate patterns
- Some over-abstracted layers

---

## Next Steps

1. Run `vulture src/ --min-confidence 80` to get high-confidence dead code list
2. Create branch `cleanup/dead-code`
3. Delete Tier 1 items (safe deletions)
4. Run full test suite to verify
5. Document Tier 2 items with `# RESERVED:` comments
6. Create debt item for Phase 2 refactoring

---

## Vulture Command Reference

```bash
# High confidence dead code (safe to delete)
vulture src/ --min-confidence 80

# All potential dead code
vulture src/ --min-confidence 60

# Count by type
vulture src/ --min-confidence 60 2>&1 | grep -E "unused (method|function|class)" | wc -l
```
