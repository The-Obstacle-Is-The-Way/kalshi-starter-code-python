# Code Quality Audit: Configuration Analysis

**Date:** 2026-01-08 (Revised)
**Scope:** Full codebase vertical slice + test suite
**Methodology:** First-principles validation against 12-factor app best practices

---

## Executive Summary

After critical review and validation against [Python 2025-2026 best practices](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) and [12-factor app methodology](https://medium.com/datamindedbe/twelve-factor-python-applications-using-pydantic-settings-f74a69906f2f), this audit identifies **true issues** while correcting **false positives** from the initial analysis.

**Key Finding:** The codebase follows correct patterns for CLI defaults with overrides. The primary legitimate issues are:
1. Path constants could be centralized (DRY)
2. Logging uses mixed systems (logging vs structlog)

Most items flagged as "magic numbers" are actually **correct by design**.

---

## False Positives (Corrected)

These were initially flagged but are **NOT issues**:

### 1. API Limits (1000, 200, 100)

| Value | Purpose | Why NOT a Magic Number |
|-------|---------|------------------------|
| `1000` | Markets max per page | **Kalshi API constraint** - cannot be changed |
| `200` | Events max per page | **Kalshi API constraint** - documented in API |
| `100` | Candlesticks max tickers | **Kalshi API constraint** - external limit |

These are **immutable external constraints**, not tunables. Putting them in config would mislead users into thinking they're configurable.

### 2. Price Validation (1-99)

```python
if price < 1 or price > 99:
    raise ValueError("Price must be between 1 and 99 cents")
```

This is a **Kalshi business rule** - prediction market prices are in cents, 1-99. This is an invariant, not a magic number.

### 3. API Path Prefix

```python
API_PATH = "/trade-api/v2"
```

This is **API versioning** - correctly defined as a class constant. Changing it would break the API integration.

### 4. CLI Default Values with `--override`

The pattern:
```python
db_path: Path = Path("data/kalshi.db"),  # Default
typer.Option("--db", "-d", help="...")   # Override available
```

This is the **correct pattern** per 12-factor app: sensible defaults with CLI overrides. NOT a problem.

### 5. Retry Parameters

```python
timeout: float = 30.0
max_retries: int = 5
wait_exponential(multiplier=1, min=1, max=60)
```

These are **industry-standard sensible defaults**. Users who need customization can subclass or pass parameters.

---

## True Issues

### Issue 1: Path Constants Could Be Centralized (DRY)

**Severity:** Low (Code Smell, not Bug)

The path `data/kalshi.db` appears 20+ times as a CLI default. While each instance correctly allows override via `--db`, there's no single source of truth.

**Current State:**
```python
# cli.py (repeated 20+ times)
db_path: Path = Path("data/kalshi.db")
```

**Recommendation:** Define once, import everywhere:
```python
# src/kalshi_research/paths.py
from pathlib import Path

DEFAULT_DATA_DIR = Path("data")
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "kalshi.db"
DEFAULT_ALERTS_PATH = DEFAULT_DATA_DIR / "alerts.json"
DEFAULT_THESES_PATH = DEFAULT_DATA_DIR / "theses.json"
DEFAULT_EXPORTS_DIR = DEFAULT_DATA_DIR / "exports"
```

**Risk:** Very low - pure refactoring, no behavior change.

---

### Issue 2: Inconsistent Logging Systems

**Severity:** Low (Technical Debt)

| System | Files Using |
|--------|-------------|
| `logging.getLogger(__name__)` | `client.py`, `fetcher.py`, `scheduler.py`, `export.py`, `syncer.py`, `notifiers.py`, `thesis.py`, `notebook_utils.py` (8 files) |
| `structlog.get_logger()` | `rate_limiter.py`, `websocket/client.py` (2 files) |

**Recommendation:** Standardize on `structlog` - it's already a dependency and provides better structured logging for async code.

---

## What Belongs Where: `.env` vs Code Constants

Based on [12-factor app principles](https://geekcoding101.com/tech/system-design/12-factor-crash-course/):

### `.env` File (Already Correct)

The `.env.example` is **properly wired**. All env vars are used:

| Variable | Used In | Purpose |
|----------|---------|---------|
| `KALSHI_ENVIRONMENT` | `cli.py:116` | Switch prod/demo |
| `KALSHI_KEY_ID` | `cli.py:1962, 2192` | Auth |
| `KALSHI_PRIVATE_KEY_PATH` | `cli.py:1963, 2193` | Auth |
| `KALSHI_PRIVATE_KEY_B64` | `cli.py:1964, 2194` | Auth (CI) |
| `KALSHI_RUN_LIVE_API` | `tests/` | Enable live tests |

**Verdict:** `.env.example` is complete and accurate.

### Code Constants (Paths Module)

Non-secret, non-environment-specific defaults belong in code:
- File paths with CLI overrides
- API limits (external constraints)
- Reasonable defaults for timeouts/retries

---

## Test Suite Analysis

The test suite does **NOT** have parallel debt problems:

1. **E2E tests use `runner.isolated_filesystem()`** - Creates temp directories, so `data/kalshi.db` is relative to temp, not hardcoded to a real path.

2. **Unit tests use in-memory SQLite** - `sqlite+aiosqlite:///:memory:` in `conftest.py`

3. **Test fixtures are well-designed** - `make_market`, `make_orderbook`, `make_trade` factories return dicts matching API structure.

4. **No magic numbers in assertions** - Test values are explicit and documented.

**Verdict:** Test suite is clean.

---

## Scanner/Analysis Thresholds

These ARE legitimate tunables that users might want to adjust:

| Setting | Default | Purpose |
|---------|---------|---------|
| Close race range | `(0.40, 0.60)` | What's "close to 50%" |
| High volume threshold | `10000` | What's "high volume" |
| Wide spread threshold | `5` | What's "wide" |
| Min correlation | `0.5` | Statistical significance |

**Current design:** These are constructor parameters, allowing customization:
```python
scanner = MarketScanner(close_race_range=(0.45, 0.55))
```

This is the **correct pattern** - defaults with optional override. Not a bug.

---

## Proposed Changes (Minimal, High-Value)

### Change 1: Centralize Paths

Create `src/kalshi_research/paths.py`:

```python
"""Centralized path defaults for Kalshi Research Platform."""

from pathlib import Path

# All paths are relative to CWD, overridable via CLI
DEFAULT_DATA_DIR = Path("data")
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "kalshi.db"
DEFAULT_ALERTS_PATH = DEFAULT_DATA_DIR / "alerts.json"
DEFAULT_THESES_PATH = DEFAULT_DATA_DIR / "theses.json"
DEFAULT_EXPORTS_DIR = DEFAULT_DATA_DIR / "exports"
DEFAULT_ALERT_LOG = DEFAULT_DATA_DIR / "alert_monitor.log"
```

Then update `cli.py` imports:
```python
from kalshi_research.paths import DEFAULT_DB_PATH
# ...
db_path: Path = DEFAULT_DB_PATH,
```

### Change 2: Standardize Logging (Optional)

Replace `logging.getLogger(__name__)` with `structlog.get_logger()` in:
- `client.py`
- `fetcher.py`
- `scheduler.py`
- `export.py`

---

## NOT Recommended

These changes would be **over-engineering**:

1. **`pydantic-settings` for config** - Overkill for this project. The current approach (defaults + CLI overrides) is correct.

2. **YAML/TOML config files** - Adds complexity without benefit. CLI args are sufficient.

3. **Environment variable overrides for everything** - Would couple code to env vars unnecessarily. CLI overrides are more explicit.

4. **Moving API limits to config** - They're external constraints, not tunables. Misleading to put in config.

---

## Summary

| Category | Status |
|----------|--------|
| `.env.example` wiring | Complete and correct |
| Test suite | Clean, no parallel debt |
| API limits | Correctly hardcoded (external constraints) |
| CLI defaults | Correct pattern (defaults + override) |
| Path constants | Could centralize (DRY improvement) |
| Logging | Could standardize (minor tech debt) |

**Overall Assessment:** The codebase is well-designed. The initial audit over-flagged by treating external constraints and sensible defaults as "magic numbers." The only true issues are:

1. **Path centralization** - Easy DRY improvement
2. **Logging consistency** - Minor standardization

Both are optional improvements, not bugs.

---

## Sources

- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Twelve-Factor Python Applications](https://medium.com/datamindedbe/twelve-factor-python-applications-using-pydantic-settings-f74a69906f2f)
- [12 Factor Crash Course (2025)](https://geekcoding101.com/tech/system-design/12-factor-crash-course/)
- [FastAPI Settings Best Practices](https://fastapi.tiangolo.com/advanced/settings/)
