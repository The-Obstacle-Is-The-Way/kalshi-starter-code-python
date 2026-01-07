# ADVERSARIAL SPEC & BUG AUDIT REPORT

**Auditor:** Senior Software Architect
**Date:** 2026-01-06
**Target:** Kalshi Research Platform Specs (001-008) & Bugs (001-007)

---

## 1. SPEC AUDIT RESULTS

### SPEC-001: Modern Python Foundation
**Verdict:** [PASS]
- **Analysis:** Solid foundation. Tooling (uv, ruff, mypy) is modern and correct.
- **Notes:** Python 3.14 in CI matrix is aggressive (alpha/beta status) and causing BUG-007.

### SPEC-002: Kalshi API Client
**Verdict:** [WARN]
- **Issue 1 (Architecture):** `KalshiClient` inherits from `KalshiPublicClient` but explicitly *skips* `super().__init__()`. While it manually sets `self._client`, this is brittle. If the parent class adds more initialization logic later, the child class breaks silently.
- **Issue 2 (Type Safety):** `Market` model uses `int` for cents. This is good for precision, but `midpoint` calculation in `Orderbook` returns `Decimal`. `PriceSnapshot` in SPEC-003 uses `REAL` for midpoint. Consistency needed on floating-point vs Decimal usage for calculated fields.
- **Recommendation:** Refactor `KalshiClient` to use composition (contain a `KalshiPublicClient`) or properly call `super().__init__`. Ensure strict Decimal usage for all currency math to avoid float artifacts.

### SPEC-003: Data Layer & Storage
**Verdict:** [WARN]
- **Issue 1 (SQLite Timezones):** Spec requires `DateTime(timezone=True)`. SQLite does not natively store timezones. SQLAlchemy + aiosqlite can be tricky here. The spec must explicitly mandate **UTC storage** (converting to UTC before save, ensuring naive-UTC on load) to avoid timezone confusion.
- **Issue 2 (Generated Columns):** Uses `GENERATED ALWAYS AS ... STORED`. Requires SQLite >= 3.31. Python 3.11+ bundles recent SQLite, but external environments (e.g., CI runners using system sqlite) might fail if old.
- **Recommendation:** Add explicit "Timezone Storage Strategy" section enforcing UTC conversion at the repository boundary.

### SPEC-004: Research Analysis Framework
**Verdict:** [PASS]
- **Analysis:** Comprehensive. Mathematical formulas for Brier score are correct. `EdgeDetector` logic is sound.

### SPEC-005: Alerts & Notifications
**Verdict:** [WARN]
- **Issue 1 (Duplication):** `AlertMonitor` running in a polling loop (`cli monitor`) operates independently of `DataFetcher`. Running both `kalshi data collect` (for storage) and `kalshi alerts monitor` (for alerts) doubles API load and rate limit usage.
- **Recommendation:** Integrate alerting *into* the data collection pipeline (`DataFetcher` should emit events that `AlertMonitor` consumes), or explicitly note the trade-off.

### SPEC-006: Event Correlation
**Verdict:** [PASS]
- **Analysis:** Good definition of correlation types. Lead-lag is a nice addition.

### SPEC-007: Probability Tracking
**Verdict:** [PASS]
- **Analysis:** Metrics are standard and useful.

### SPEC-008: Notebooks & Backtesting
**Verdict:** [PASS]
- **Analysis:** Backtesting logic is simple but sufficient for "Research" scope.

---

## 2. BUG AUDIT RESULTS

**Summary:** All bugs (001-007) are **ACCURATE** and correctly identified based on the file system state and specs.

*   **BUG-001 (Missing Scan):** Valid. Feature specified but not reachable via CLI.
*   **BUG-002 (Missing Alembic):** Valid. Critical for DB evolution.
*   **BUG-003 (Missing Notebooks):** Valid.
*   **BUG-004 (Missing Analysis Modules):** Valid. `correlation.py`, `metrics.py`, `visualization.py` are missing.
*   **BUG-005 (Missing Research Modules):** Valid. `backtest.py`, `notebook_utils.py` are missing.
*   **BUG-006 (Missing Alerts):** Valid. Entire subsystem missing.
*   **BUG-007 (CI Failures):** Valid. Python 3.14 is the likely culprit.

---

## 3. CRITICAL FINDINGS & RECOMMENDATIONS

### Critical Finding 1: API Load Duplication
Running the "Data Collector" (SPEC-003) and "Alert Monitor" (SPEC-005) as separate CLI commands will cause double the API requests, potentially hitting rate limits (P2 requirements mentions robustness against 429s, but we should avoid causing them).

**Fix:** Architecture change. The `AlertMonitor` should optimally hook into the data stream. However, for a "starter code" refactor, keeping them separate is simpler but should be documented. Ideally, `kalshi data collect` should optionally run alerts.

### Critical Finding 2: Python 3.14 in CI
Including an unreleased Python version in a "strict" CI pipeline (where failure blocks merge) is bad practice for a production-intent project.

**Fix:** Move 3.14 to `experimental: true` or remove it.

### Critical Finding 3: Database Timezone Handling
Implicit reliance on SQLAlchemy to handle SQLite timezones correctly often leads to "Naive datetime received" errors or mixed-tz data.

**Fix:** Enforce UTC-only in Repositories.

---

## 4. ACTION PLAN

1.  **Refine Specs:**
    *   Update **SPEC-002** to fix `KalshiClient` inheritance.
    *   Update **SPEC-003** to enforce explicit UTC handling strategy.
    *   Update **SPEC-005** to mention API load considerations.
2.  **Refine Bugs:**
    *   Update **BUG-007** to explicitly recommend removing/softening Python 3.14 check.
3.  **Approve:**
    *   Mark specs as `Status: Reviewed`.

**VERDICT:** [ ] NEEDS MINOR FIXES (proceeding to fix)
