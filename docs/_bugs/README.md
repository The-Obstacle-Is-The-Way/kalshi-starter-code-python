# Bug Reports Index

This directory is the staging area for **active** bug reports. Once resolved, bugs are moved to the archive.

## Active Bugs

| ID | Title | Priority | Status | Verified |
|---|---|---|---|---|
| **[BUG-069](BUG-069-order-response-status-field-mismatch.md)** | Order response schema mismatch (`status` vs `order_status`) can orphan live orders | P0 | Open | 2026-01-12 |
| **[BUG-064](BUG-064-missing-order-safety-parameters.md)** | Missing Order Safety Parameters (`reduce_only`, etc.) | P2 | Open | 2026-01-12 |
| **[BUG-063](BUG-063-missing-dollar-fields-market-model.md)** | Missing Dollar Fields in Market Model | P3 | Open | 2026-01-12 |
| **[BUG-065](BUG-065-amend-order-missing-required-fields.md)** | `amend_order()` Missing Required Fields (BROKEN) | P2 | Open | 2026-01-12 |
| **[BUG-066](BUG-066-fill-model-missing-fields.md)** | Fill Model Missing Fields (API Completeness) | P3 | Open | 2026-01-12 |
| **[BUG-067](BUG-067-order-model-missing-fields.md)** | Order Model Missing Fields (API Completeness) | P3 | Open | 2026-01-12 |
| **[BUG-068](BUG-068-market-model-missing-structural-fields.md)** | Market Model Missing Structural Fields | P3 | Open | 2026-01-12 |
| **[BUG-070](BUG-070-cancel-order-drops-reduced-by.md)** | `cancel_order()` drops `reduced_by` from cancel response | P3 | Open | 2026-01-12 |

### Verification Note (2026-01-12)

All bugs verified against actual codebase usage. Several originally classified as P0-P2 were **downgraded** after discovering:
- Missing fields are not used in any code paths
- No CLI commands expose the affected functionality
- Core platform works without these fields (API completeness issues, not functional bugs)

### Priority Guide

- **P2**: Medium - API completeness gaps (safety params, not yet exposed via CLI)
- **P3**: Low - Nice-to-have API parity (fields exist in API but we don't use them)

### Recently Closed Dependency Chain (Resolved)

```
BUG-057 (FIFO fix)
    └── introduced BUG-058 (crash on incomplete history)
            └── root cause: BUG-059 (missing settlements)
            └── allowed by: BUG-061 (missing tests)
```

**Fix order used:** BUG-061 → BUG-059 → BUG-058

## Next ID Tracker
Use this ID for the next bug report you create:
**BUG-071**

---

## Archive (Resolved)
All resolved bug reports are stored in
[`docs/_archive/bugs/`](https://github.com/The-Obstacle-Is-The-Way/kalshi-starter-code-python/tree/main/docs/_archive/bugs/).

Note: `docs/_archive/**` is intentionally excluded from the MkDocs site build (historical provenance only).

### Recently Archived (2026-01-10)

| ID | Title | Status |
|---|---|---|
| **BUG-062** | Backtest date range end-date excludes full day | ✅ Fixed |
| **BUG-061** | Test suite missing FIFO edge case coverage | ✅ Fixed |
| **BUG-060** | Duplicate realized P&L computation (ignores Kalshi's value) | 🟡 Closed |
| **BUG-059** | Missing portfolio settlements sync | ✅ Fixed |
| **BUG-058** | FIFO P&L crashes on incomplete trade history | ✅ Fixed |
| **BUG-057** | Portfolio P&L integrity (FIFO realized P&L + unknown handling) | ✅ Fixed |
| **BUG-056** | Deep Codebase Audit: Financial & Safety Risks (P0/P1) | ✅ Fixed |
| **BUG-054** | Portfolio CLI crashes on fresh/empty DB (missing tables) | ✅ Fixed |
| **BUG-053** | Data sync is not concurrency-safe (IntegrityError on upsert) | ✅ Fixed |

### Recently Resolved (Ralph Wiggum Cleanup - 2026-01-09)

| ID | Title | Status |
|---|---|---|
| **BUG-052** | `market list --status active` traceback (invalid filter) | ✅ Fixed |
| **BUG-051** | Cancel order response schema mismatch | ✅ Fixed |
| **BUG-050** | Silent exception swallowing in alerts sentiment computation | ✅ Fixed |
| **BUG-049** | Asymmetrical rate limiting (reads unprotected) | ✅ Fixed |
| **BUG-048** | Negative liquidity validation error crashes market scan | ✅ Fixed |
| **BUG-047** | Portfolio sync shows 0 positions (response key mismatch) | ✅ Fixed |

### Previously Resolved

| ID | Title | Status |
|---|---|---|
| **BUG-046** | Datetime Serialization in News Collector | ✅ Fixed |
| **BUG-045** | Legacy Starter Code Compatibility Layer | ✅ Removed |
| **INCIDENT-001** | Chinese Character Syntax Corruption | ✅ Resolved |
| **BUG-044** | WebSocket client silent JSON errors | ✅ Fixed |
| **BUG-040** | Alembic FileConfig Disables Existing Loggers | ✅ Fixed |
| **BUG-039** | CLI Dotenv Not Loaded for Auth | ✅ Fixed |
| **BUG-038** | Scan Arbitrage Inverse One-Sided Quotes | ✅ Fixed |
| **BUG-037** | Edge Histogram Zero Estimate Truthiness | ✅ Fixed |
| **BUG-036** | Analysis Metrics Spread Truthiness | ✅ Fixed |
| **BUG-035** | Scan & Snapshot Missing Max Pages | ✅ Fixed |
| **BUG-034** | Portfolio Positions Hides Zero Price | ✅ Fixed |
| **BUG-033** | Market Model API Schema Mismatch | ✅ Fixed |
| **BUG-032** | Scan Arbitrage Tickers Limit Silent | ✅ Fixed |
| **BUG-031** | Scan Movers Percent Units Wrong | ✅ Fixed |
| **BUG-030** | Scan Arbitrage Inverse Sum False Positives | ✅ Fixed |
| **BUG-029** | Scan Close Race Returns Illiquid Junk | ✅ Fixed |
| **BUG-028** | Alerts Monitor "Once" Flag Ignored | ✅ Fixed |
| **BUG-027** | Pagination Cap Silently Truncates Data | ✅ Fixed |
| **BUG-026** | Data Snapshot Foreign Key Failure | ✅ Fixed |
| **BUG-025** | Portfolio Positions Missing Cost Basis | ✅ Fixed |
| **BUG-024** | Legacy Client Missing Timeouts | ✅ Fixed |
| **BUG-023** | Query Parquet Path Validation | ✅ Fixed |
| **BUG-022** | API Client Truthiness Filters | ✅ Fixed |
| **BUG-021** | Notebook Utils Limit & Exception Handling | ✅ Fixed |
| **BUG-020** | Visualization Type Ignores | ✅ Fixed |
| **BUG-019** | Portfolio Sync Incomplete | ✅ Fixed |
| **BUG-018** | API Client Type Safety | ✅ Fixed |
| **BUG-016** | Data Snapshot Missing Init | ✅ Fixed |
| **BUG-015** | Scan Movers Timezone Crash | ✅ Fixed |
| **BUG-014** | CLI Analysis Calibration Broken | ✅ Fixed |
| **BUG-013** | Database Init Missing Portfolio Tables | ✅ Fixed |
| **BUG-012** | Missing Market Status Enum | ✅ Fixed |
| **BUG-011** | API Limit Exceeds Max | ✅ Fixed |
| **BUG-010** | Missing Portfolio Link | ✅ Fixed |
| **BUG-009** | Incomplete CLI Commands | ✅ Fixed |
| **BUG-008** | Inconsistent Test Structure | ✅ Fixed |
| **BUG-007** | CI/CD Test Failures | ✅ Fixed |
| **BUG-006** | Missing Alerts System | ✅ Fixed |
| **BUG-005** | Missing Research Modules | ✅ Fixed |
| **BUG-004** | Missing Analysis Modules | ✅ Fixed |
| **BUG-003** | Missing Notebooks Directory | ✅ Fixed |
| **BUG-002** | Missing Alembic Configuration | ✅ Fixed |
| **BUG-001** | Missing Scan CLI Command | ✅ Fixed |
