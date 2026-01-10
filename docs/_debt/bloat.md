# Codebase Bloat Analysis

**Date:** 2026-01-10
**Analyzer:** Vulture, deadcode, radon (complexity + maintainability)
**Trigger:** External code review criticism (ex-Databricks engineer)
**Verified Against:** Kalshi API docs, Exa API docs (vendor SSOT)

---

## Executive Summary

| Metric | Value | Grade |
|--------|-------|-------|
| Total Python files | 82 | - |
| Total source LOC | 15,059 | - |
| Test LOC | 15,644 | **A** (good coverage) |
| Unused methods/functions/classes | ~64 (verified true positives) | **C** (needs cleanup) |
| Total deadcode items | 343 (raw count) | C |
| Average cyclomatic complexity | 2.9 | **A** |
| Maintainability index | All files A | **A** |
| **Overall Grade** | | **B-** |

### Verdict

**Julian's criticism has merit.** There is measurable bloat:
- **116** raw unused candidates (Vulture 60% confidence) -> **~64 verified true positives**
- Multiple dead modules (EdgeDetector, TemporalValidator, etc.) and several halfway implementations (e.g. alert notifiers)
  - ✅ Resolved: DEBT-008 removed the verified-dead code
- Boilerplate duplication (16 `create_tables()` calls)
  - ✅ Resolved: DEBT-010 consolidated to `open_db()` in `src/kalshi_research/cli/db.py`
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

> **Update (2026-01-10):** All TIER 1 items have been deleted under DEBT-008. The snippets below are
> preserved as historical analyzer output.

#### `analysis/edge.py` - EdgeDetector (246 lines)
```
src/kalshi_research/analysis/edge.py:76: unused method 'detect_thesis_edge'
src/kalshi_research/analysis/edge.py:123: unused method 'detect_spread_edge'
src/kalshi_research/analysis/edge.py:163: unused method 'detect_volume_edge'
src/kalshi_research/analysis/edge.py:210: unused method 'detect_volatility_edge'
```
**Action:** ✅ Deleted in DEBT-008 (`cc01a04`). Kept `Edge` dataclass for notebook usage.

#### ~~`alerts/notifiers.py` - Unused Notifiers~~ → MOVED TO TIER 3

**REVISED (2026-01-10):** FileNotifier and WebhookNotifier are **HALFWAY IMPLEMENTATIONS**, not slop. See
"Alert Notifiers" in TIER 3. These are legitimate features that should be wired into `kalshi alerts monitor`
with `--output-file` and `--webhook-url` options.

#### `research/thesis.py` - TemporalValidator (40+ lines)
```
src/kalshi_research/research/thesis.py:41: unused class 'TemporalValidator'
src/kalshi_research/research/thesis.py:56: unused method 'validate'
```
**Action:** ✅ Deleted in DEBT-008 (`654cf50`).

#### Unused Analysis Methods
```
src/kalshi_research/analysis/metrics.py:63: unused method 'compute_spread_stats'
src/kalshi_research/analysis/metrics.py:105: unused method 'compute_volatility'
src/kalshi_research/analysis/metrics.py:171: unused method 'compute_volume_profile'
src/kalshi_research/analysis/liquidity.py:438: unused method 'max_safe_buy_size'
src/kalshi_research/analysis/scanner.py:390: unused method 'scan_all'
```
**Action:** ✅ Deleted in DEBT-008 (`612e66f`, `1658a7b`, `237d52b`).

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

#### Alert Notifiers (Halfway - Wire In)
```
src/kalshi_research/alerts/notifiers.py:46: unused class 'FileNotifier'
src/kalshi_research/alerts/notifiers.py:71: unused class 'WebhookNotifier'
```
**Decision:** ✅ Wired in DEBT-009 via `kalshi alerts monitor --output-file ... --webhook-url ...`.

#### Exa Client Methods
```
src/kalshi_research/exa/client.py:349: unused method 'find_similar'
src/kalshi_research/exa/client.py:403: unused method 'create_research_task'
src/kalshi_research/exa/client.py:426: unused method 'wait_for_research'
```
**Decision:** ✅ Wired in DEBT-009 via `kalshi research similar ...` and `kalshi research deep ...`.

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
**Decision:** ✅ Deleted in DEBT-008 (`f4921e5`).

---

## Deep Trace: Vendor API Verification

Each item traced against official Kalshi/Exa API docs to determine TRUE dead code vs HALFWAY implementations.

### Kalshi API Methods - Verified Against `docs/_vendor-docs/kalshi-api-reference.md`

| Our Method | Kalshi Endpoint | Verdict | Action |
|------------|-----------------|---------|--------|
| `get_trades` | `GET /markets/trades` | ✅ WIRED | `kalshi data sync-trades` |
| `get_candlesticks` | `GET /markets/candlesticks` | ✅ WIRED | `kalshi market history` |
| `get_series_candlesticks` | `GET /series/{series}/markets/{ticker}/candlesticks` | ✅ WIRED | `kalshi market history --series ...` |
| `get_exchange_status` | `GET /exchange/status` | ✅ WIRED | `kalshi status` and scan halt checks |
| `create_order` | `POST /portfolio/orders` | **RESERVED** | Keep - trading feature |
| `cancel_order` | `DELETE /portfolio/orders/{id}` | **RESERVED** | Keep - trading feature |
| `amend_order` | `POST /portfolio/orders/{id}/amend` | **RESERVED** | Keep - trading feature |
| `get_orders` | `GET /portfolio/orders` | **RESERVED** | Keep - order management |
| WebSocket `subscribe_*` | All WS channels | **RESERVED** | Explicit `# RESERVED` marker (DEBT-009) |

### Exa API Methods - Verified Against `docs/_vendor-docs/exa-api-reference.md`

| Our Method | Exa Endpoint | Verdict | Action |
|------------|--------------|---------|--------|
| `find_similar` | `POST /findSimilar` | ✅ WIRED | `kalshi research similar` |
| `create_research_task` | `POST /research/v1` | ✅ WIRED | `kalshi research deep` |
| `wait_for_research` | Polling `GET /research/v1/{id}` | ✅ WIRED | `kalshi research deep --wait` |

### Analysis Module - No Vendor API (Our Logic)

| Item | Verdict | Reasoning |
|------|---------|-----------|
| `EdgeDetector` (all methods) | **TRUE SLOP** | Exported in `__init__` but never instantiated/used in app |
| `compute_spread_stats` | **TRUE SLOP** | Called in tests/docs only, never in app logic |
| `compute_volatility` | **TRUE SLOP** | Called in tests/docs only, never in app logic |
| `compute_volume_profile` | **TRUE SLOP** | Called in tests/docs only, never in app logic |
| `scan_all` | **TRUE SLOP** | Convenience method, never used |
| `verify_market_open` | ✅ WIRED | Supports exchange halt checks when provided |
| `max_safe_buy_size` | **TRUE SLOP** | Redundant wrapper: safe sizing is already exposed via `max_safe_order_size` and `kalshi market liquidity` |

### Research Module

| Item | Verdict | Reasoning |
|------|---------|-----------|
| `TemporalValidator` | **TRUE SLOP** | No clear use case, no integration path |
| `notebook_utils.py` | **FALSE POSITIVE** | Used by Jupyter notebooks in `/notebooks/` |

### Repository Methods

| Method | Verdict | Reasoning |
|--------|---------|-----------|
| `get_by_series` | **YAGNI CRUFT** | Built speculatively, never used |
| `get_by_category` | **YAGNI CRUFT** | Built speculatively, never used |
| `get_expiring_before` | **YAGNI CRUFT** | Built speculatively, never used |
| `get_latest_batch` | **YAGNI CRUFT** | Built speculatively, never used |
| `delete_older_than` | **YAGNI CRUFT** | Built speculatively, never used |
| `get_by_result` | **YAGNI CRUFT** | Built speculatively, never used |
| `count_by_result` | **YAGNI CRUFT** | Built speculatively, never used |

---

## Complexity Hotspots (Radon Analysis)

### Functions Rated D (Very High Complexity - Refactor Priority)

| Function | Complexity | Location |
|----------|------------|----------|
| `ThesisBacktester._compute_result` | **D (22)** | `research/backtest.py:202` |

### Functions Rated C (High Complexity - Monitor)

| Function | Complexity | Location |
|----------|------------|----------|
| `PnLCalculator.calculate_summary_with_trades` | C (20) | `portfolio/pnl.py:171` |
| `SentimentAggregator.get_market_summary` | C (16) | `news/sentiment.py:74` |
| `SentimentAggregator.get_event_summary` | C (16) | `news/sentiment.py:158` |
| `AlertMonitor._check_condition` | C (15) | `alerts/monitor.py:117` |
| `KalshiClient.create_order` | C (15) | `api/client.py:647` |
| `KalshiClient.amend_order` | C (15) | `api/client.py:809` |
| `PortfolioSyncer.sync_trades` | C (14) | `portfolio/syncer.py:195` |
| `KalshiWebSocket._handle_message` | C (14) | `websocket/client.py:215` |

### Maintainability Index (Lowest Scores - Still Passing)

| File | MI Score | Notes |
|------|----------|-------|
| `api/client.py` | 29.63 | Large file, many methods |
| `research/invalidation.py` | 30.98 | Complex logic |
| `exa/client.py` | 31.15 | Large file |
| `research/thesis_research.py` | 31.31 | Complex logic |
| `analysis/liquidity.py` | 35.29 | Dense calculations |

---

## Structural Bloat

### 1. Triple Data Modeling (Actually NOT Bloat)

The codebase uses THREE different patterns for data models:

| Pattern | File Count | Purpose |
|---------|------------|---------|
| `@dataclass` | 19 files | Internal DTOs, analysis results |
| Pydantic `BaseModel` | 15 files | API response models |
| SQLAlchemy `Mapped[]` | 15 files | Database ORM |

**REVISED Assessment:** This is **VALID architecture**, not bloat.

- **Pydantic**: Validates external API responses (immutable, frozen)
- **SQLAlchemy**: Persists to database (mutable, ORM-managed)
- **dataclass**: Lightweight internal DTOs for analysis (no validation overhead)

**This is proper separation of concerns.** Different layers need different models. The apparent "redundancy" is intentional - you don't want your DB model coupled to your API response format.

### 2. Repeated Boilerplate (Resolved)

**Previously:** 16 calls to `await db.create_tables()` scattered across CLI commands:
- `cli/portfolio.py`: 6 calls
- `cli/news.py`: 5 calls
- `cli/data.py`: 5 calls

**Now:** Consolidated into a single helper (`open_db()` / `open_db_session()`), leaving exactly **1**
`await db.create_tables()` call in the CLI layer (`src/kalshi_research/cli/db.py`).

```python
from kalshi_research.cli.db import open_db

async with open_db(db_path) as db, db.session_factory() as session:
    ...
```

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
| `cli/portfolio.py` | 608 | DB setup refactored (DEBT-010); LOC snapshot is pre-refactor |
| `cli/scan.py` | 564 | OK - scanner has legitimate complexity |
| `research/thesis.py` | 482 | TemporalValidator removed (DEBT-008); LOC snapshot is pre-refactor |
| `exa/client.py` | 449 | ~100 lines of unused methods |
| `analysis/liquidity.py` | 448 | Removed dead wrapper (DEBT-008); remaining dense calculations |
| `analysis/scanner.py` | 410 | Removed dead `scan_all` (DEBT-008); remaining scanner logic |
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

### Phase 1: Quick Wins (Est. 400 LOC reduction)

1. [x] Delete `EdgeDetector` class (keep `Edge` dataclass) (DEBT-008)
2. [x] Delete `TemporalValidator` class (DEBT-008)
3. [x] Delete unused analysis methods (`compute_spread_stats`, etc.) (DEBT-008)
4. [x] Delete unused repository methods (DEBT-008)
5. [x] Remove unused imports flagged by ruff (DEBT-008)

**Note:** `FileNotifier` and `WebhookNotifier` were HALFWAY implementations; ✅ wired in DEBT-009.

### Phase 2: Refactoring (Est. 300 LOC reduction)

1. [x] Consolidate repeated `create_tables()` calls into `open_db()` helpers (DEBT-010)
2. [x] Wire in Exa client methods (DEBT-009)
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
- Halfway implementations (now wired in DEBT-009)
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

## Tool Command Reference

```bash
# === DEAD CODE DETECTION ===

# Vulture (high confidence - safe to delete)
vulture src/ --min-confidence 80

# Vulture (all potential dead code)
vulture src/ --min-confidence 60

# Deadcode (alternative, better scope tracking)
deadcode src/

# Count unused methods/functions/classes
vulture src/ --min-confidence 60 2>&1 | grep -E "unused (method|function|class)" | wc -l

# === COMPLEXITY ANALYSIS ===

# Cyclomatic complexity (find complex functions)
radon cc src/ -a -s

# Only show C or worse
radon cc src/ -a -s | grep -E " - [C-F] "

# Maintainability index (lower = worse, but all A is good)
radon mi src/ -s

# === CREATE WHITELIST FOR FALSE POSITIVES ===
vulture src/ --make-whitelist > vulture_whitelist.py
```

---

## Summary: Verdict Categories

| Category | Count | Action |
|----------|-------|--------|
| **TRUE SLOP** | ~12 items | DELETE immediately (see DEBT-008) |
| **HALFWAY IMPL** | ~14 items | ✅ Wired in DEBT-009 |
| **RESERVED** | ~5 items | Keep with `# RESERVED:` comment |
| **FALSE POSITIVE** | ~30+ items | Add to whitelist |
| **YAGNI CRUFT** | ~7 items | DELETE (see DEBT-008) |

**Bottom line:** ~10-15% of code is dead. After cleanup, this codebase would be solid B+/A- engineering.

---

## Cross-References

| Debt Item | Derived From This Audit |
|-----------|------------------------|
| [DEBT-008](../_archive/debt/DEBT-008-dead-code-cleanup.md) | TRUE SLOP + YAGNI items |
| [DEBT-009](../_archive/debt/DEBT-009-finish-halfway-implementations.md) | HALFWAY items |
| [DEBT-010](../_archive/debt/DEBT-010-reduce-boilerplate.md) | Structural bloat (boilerplate) |

**Note:** DEBT-007 is a separate operational hardening document, not derived from this bloat audit.
