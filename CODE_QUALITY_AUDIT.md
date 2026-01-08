# Code Quality Audit: Configuration & Magic Number Analysis

**Date:** 2026-01-08
**Scope:** API Client → Data Fetcher → Repository → CLI vertical slice
**Status:** Findings documented, prioritized for future cleanup

---

## Executive Summary

This audit analyzed the core data flow path through the codebase. While the code is functional and well-tested, there are opportunities to improve maintainability through centralized configuration.

**Key Finding:** Magic numbers and hard-coded paths are scattered across ~15 files. Centralizing these into a config module would reduce duplication and improve maintainability.

---

## Priority 1: Hard-Coded Paths (Duplicated 57+ times)

### Database Path Sprawl
The path `data/kalshi.db` appears as a default in 12+ CLI commands:

| File | Line | Context |
|------|------|---------|
| `cli.py` | 148, 169, 211, 251, 289, 369, 409, 721, 873, 1291, 1385, 1427, 1629, 1827, 1938, 2023, 2100, 2234, 2305, 2345 | `--db` option default |
| `database.py` | 28 | Constructor default |

**Recommendation:** Create `DEFAULT_DB_PATH` constant in a central config module.

### Other Hard-Coded Paths

| Path | File | Line | Usage |
|------|------|------|-------|
| `data/alerts.json` | `cli.py` | 1015 | `_get_alerts_file()` |
| `data/theses.json` | `cli.py` | 1534 | `_get_thesis_file()` |
| `data/exports` | `cli.py` | 376 | Export output default |
| `data/alert_monitor.log` | `cli.py` | 48 | Daemon log path |

---

## Priority 2: API Client Magic Numbers

### Retry & Timeout Configuration

| File | Line | Value | Purpose |
|------|------|-------|---------|
| `client.py` | 42 | `30.0` | HTTP timeout (seconds) |
| `client.py` | 43 | `5` | Max retries |
| `client.py` | 83, 473, 604, 638, 692 | `multiplier=1, min=1, max=60` | Exponential backoff params |
| `client.py` | 410 | `"/trade-api/v2"` | API path prefix |

**Recommendation:** Move to `APIConfig` class:
```python
@dataclass
class APIConfig:
    timeout_seconds: float = 30.0
    max_retries: int = 5
    backoff_multiplier: float = 1.0
    backoff_min_seconds: float = 1.0
    backoff_max_seconds: float = 60.0
```

### Pagination Limits

| File | Line | Value | API Endpoint |
|------|------|-------|--------------|
| `client.py` | 109, 141 | `100` | Markets default limit |
| `client.py` | 120, 233 | `1000` | Markets max limit |
| `client.py` | 163, 344 | `1000` | Markets page size |
| `client.py` | 314 | `200` | Events max limit (API constraint) |
| `client.py` | 263 | `100` | Candlesticks max tickers |
| `client.py` | 533 | `200` | Fills max limit |

**Recommendation:** Document API constraints in constants:
```python
class APILimits:
    MARKETS_MAX_PER_PAGE = 1000
    EVENTS_MAX_PER_PAGE = 200
    CANDLESTICKS_MAX_TICKERS = 100
    FILLS_MAX_PER_PAGE = 200
```

---

## Priority 3: Rate Limiter Magic Numbers

| File | Line | Value | Purpose |
|------|------|-------|---------|
| `rate_limiter.py` | 65 | `0.1` | Log threshold (only log waits > 100ms) |
| `rate_limiter.py` | 89 | `0.9` | Safety margin (use 90% of limit) |
| `rate_limiter.py` | 139 | `0.2` | Cancel operation cost factor |

---

## Priority 4: Scanner & Analysis Magic Numbers

### MarketScanner Thresholds

| File | Line | Value | Purpose |
|------|------|-------|---------|
| `scanner.py` | 61 | `(0.40, 0.60)` | Close race probability range |
| `scanner.py` | 62 | `10000` | High volume threshold |
| `scanner.py` | 63 | `5` | Wide spread threshold (cents) |
| `scanner.py` | 169 | `6` | Volume log10 scale factor |
| `scanner.py` | 216 | `20` | Spread cap for scoring |

### CorrelationAnalyzer Thresholds

| File | Line | Value | Purpose |
|------|------|-------|---------|
| `correlation.py` | 82-87 | `0.3`, `0.7` | Strength classification thresholds |
| `correlation.py` | 113-117 | `30`, `0.5`, `0.05` | min_samples, min_correlation, significance |
| `correlation.py` | 173 | `0.3` | Correlation type threshold |

---

## Priority 5: CLI Default Values

### Intervals & Timeouts

| File | Line | Value | Purpose |
|------|------|-------|---------|
| `cli.py` | 294 | `15` | Snapshot interval (minutes) |
| `cli.py` | 337 | `3600` | Market sync interval (hourly) |
| `cli.py` | 510 | `5` | Orderbook depth default |
| `cli.py` | 564 | `20` | Market list limit |
| `cli.py` | 619 | `10` | Scan top_n default |
| `cli.py` | 1175 | `60` | Alert monitor interval (seconds) |

### Analysis Thresholds

| File | Line | Value | Purpose |
|------|------|-------|---------|
| `cli.py` | 787 | `0.5` | Min correlation for arbitrage |
| `cli.py` | 963 | `0.01` | Price move threshold (1%) |
| `cli.py` | 898 | `{"1h": 1, "6h": 6, "24h": 24, "7d": 168}` | Period hours mapping |

---

## Priority 6: Data Layer Magic Numbers

### Batch Commit Sizes

| File | Line | Value | Purpose |
|------|------|-------|---------|
| `fetcher.py` | 201, 257, 314 | `100` | Commit batch size |

---

## Non-Issues (Intentional Design)

These are **not** problems - they're documented API constraints or intentional defaults:

1. **Price validation (1-99)** in `client.py:572-573` - Kalshi API constraint
2. **API path prefix** in `client.py:410` - Matches Kalshi API versioning
3. **Rate tier limits** in `rate_limiter.py:25-30` - Matches Kalshi documentation

---

## Inconsistent Logging

The codebase uses two logging systems:

| Pattern | Files Using |
|---------|-------------|
| `logging.getLogger(__name__)` | `client.py`, `fetcher.py`, `scheduler.py`, `export.py` |
| `structlog.get_logger()` | `rate_limiter.py`, `websocket/client.py`, `notifiers.py`, `notebook_utils.py`, `syncer.py`, `thesis.py` |

**Recommendation:** Standardize on `structlog` for consistency with modern async patterns.

---

## Proposed Solution: Centralized Config Module

Create `src/kalshi_research/config.py`:

```python
"""Centralized configuration for Kalshi Research Platform."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

@dataclass(frozen=True)
class Paths:
    """Default paths for data storage."""
    DATA_DIR: Path = Path("data")
    DATABASE: Path = Path("data/kalshi.db")
    ALERTS_FILE: Path = Path("data/alerts.json")
    THESES_FILE: Path = Path("data/theses.json")
    EXPORTS_DIR: Path = Path("data/exports")
    ALERT_LOG: Path = Path("data/alert_monitor.log")


@dataclass(frozen=True)
class APILimits:
    """Kalshi API pagination limits (documented constraints)."""
    MARKETS_MAX_PER_PAGE: int = 1000
    EVENTS_MAX_PER_PAGE: int = 200
    CANDLESTICKS_MAX_TICKERS: int = 100
    FILLS_MAX_PER_PAGE: int = 200


@dataclass(frozen=True)
class RetryConfig:
    """HTTP retry configuration."""
    timeout_seconds: float = 30.0
    max_retries: int = 5
    backoff_multiplier: float = 1.0
    backoff_min_seconds: float = 1.0
    backoff_max_seconds: float = 60.0


@dataclass(frozen=True)
class ScannerConfig:
    """Market scanner thresholds."""
    close_race_range: tuple[float, float] = (0.40, 0.60)
    high_volume_threshold: int = 10000
    wide_spread_threshold: int = 5


@dataclass(frozen=True)
class CorrelationConfig:
    """Correlation analysis thresholds."""
    min_samples: int = 30
    min_correlation: float = 0.5
    significance_level: float = 0.05


# Default instances
PATHS = Paths()
API_LIMITS = APILimits()
RETRY_CONFIG = RetryConfig()
SCANNER_CONFIG = ScannerConfig()
CORRELATION_CONFIG = CorrelationConfig()
```

---

## Action Items (Prioritized)

### Immediate (Low Risk)
- [ ] Create `src/kalshi_research/config.py` with centralized constants
- [ ] Update `database.py` to use `PATHS.DATABASE`
- [ ] Update CLI storage functions to use `PATHS.*`

### Short-term (Medium Risk)
- [ ] Refactor `client.py` to use `RetryConfig` and `APILimits`
- [ ] Standardize on `structlog` for all logging
- [ ] Update scanner/correlation to use config dataclasses

### Long-term (Higher Risk)
- [ ] Add environment variable overrides for config values
- [ ] Add `--config` CLI option for custom config file
- [ ] Consider YAML/TOML config file for power users

---

## Conclusion

The codebase is functional and well-tested. The magic numbers identified are defaults, not bugs. However, centralizing configuration would:

1. **Reduce duplication** - Single source of truth for paths/limits
2. **Improve discoverability** - All tunables in one place
3. **Enable customization** - Easy to add env var overrides
4. **Aid documentation** - Config module serves as reference

This audit recommends a phased approach, starting with path centralization (lowest risk) and progressing to full config refactoring.
