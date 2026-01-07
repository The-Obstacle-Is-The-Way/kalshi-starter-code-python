# Kalshi Research Platform - Bug Tracker

**Audit Date:** 2026-01-06
**Auditor:** Claude (adversarial review)
**Re-audited:** 2026-01-06 (against original user intent)

---

## Summary

Adversarial audit of the "KALSHI RESEARCH PLATFORM COMPLETE" claim against:
1. PROMPT.md success criteria
2. Original user context ("CONTEXT FOR CLAUDE")
3. SPEC-001 through SPEC-004 requirements

### Quality Check Results

| Check | Status |
|-------|--------|
| ruff check | ✓ PASS |
| ruff format | ✓ PASS |
| mypy --strict | ✓ PASS |
| pytest (185 tests) | ✓ PASS |
| Coverage (81%) | ✓ PASS (>80% required) |

### Bugs Found (Re-categorized)

**TRUE BUGS** (blocking completion per PROMPT.md or original context):

| ID | Priority | Status | Summary |
|----|----------|--------|---------|
| BUG-001 | **P1** | Open | Missing `scan` CLI command (PROMPT.md Phase 4) |
| BUG-002 | **P2** | Open | Missing Alembic migrations (PROMPT.md Phase 3) |
| BUG-006 | **P1** | Open | Missing alerts system (original context: "notify me when conditions met") |
| BUG-007 | **P1** | Open | CI/CD test failures on all Python versions (tests pass locally) |

**SPEC CREEP** (mentioned in SPEC-004 but NOT in PROMPT.md success criteria):

| ID | Priority | Status | Summary |
|----|----------|--------|---------|
| BUG-003 | P3 | Deferred | Missing `notebooks/` directory → SPEC-008 |
| BUG-004 | P3 | Deferred | Missing correlation.py, metrics.py, visualization.py → SPEC-006, SPEC-007 |
| BUG-005 | P3 | Deferred | Missing backtest.py, notebook_utils.py → SPEC-008 |

---

## Implementation Status by Spec

### SPEC-001: Modern Python Foundation ✓ COMPLETE
- [x] pyproject.toml with uv
- [x] ruff configuration
- [x] mypy --strict
- [x] pytest with markers
- [x] pre-commit hooks
- [x] CI/CD workflow

### SPEC-002: Kalshi API Client ✓ COMPLETE
- [x] Pydantic v2 models (frozen)
- [x] KalshiPublicClient (unauthenticated)
- [x] KalshiClient (authenticated)
- [x] Rate limiting & retries (tenacity)
- [x] Async context managers
- [x] All public endpoints implemented

### SPEC-003: Data Layer & Storage ⚠️ PARTIAL
- [x] SQLAlchemy 2.0 async models
- [x] Repository pattern
- [x] DatabaseManager
- [x] DataFetcher
- [x] DataScheduler (drift-corrected)
- [x] DuckDB/Parquet export
- [ ] **BUG-002**: Alembic migrations not configured

### SPEC-004: Research & Analysis ⚠️ PARTIAL
- [x] CalibrationAnalyzer (Brier score, decomposition)
- [x] EdgeDetector (thesis, spread, volume)
- [x] MarketScanner (all filters)
- [x] Thesis & ThesisTracker
- [ ] **BUG-001**: scan CLI command missing

### SPEC-005: Alerts & Notifications ❌ NOT STARTED
- [ ] **BUG-006**: Entire module missing

### SPEC-006: Event Correlation Analysis ❌ NOT STARTED
- [ ] correlation.py not implemented

### SPEC-007: Probability Tracking & Visualization ❌ NOT STARTED
- [ ] metrics.py not implemented
- [ ] visualization.py not implemented

### SPEC-008: Research Notebooks & Backtesting ❌ NOT STARTED
- [ ] notebooks/ directory missing
- [ ] backtest.py not implemented
- [ ] notebook_utils.py not implemented

---

## Priority Definitions

- **P0**: Critical - Blocks deployment/usage
- **P1**: High - Major feature missing, should fix before release
- **P2**: Medium - Feature gap, can work around
- **P3**: Low - Nice-to-have, not blocking
- **P4**: Trivial - Polish/cleanup

---

## What Blocks "COMPLETE"?

To legitimately claim "KALSHI RESEARCH PLATFORM COMPLETE" for SPEC-001 through SPEC-004:

1. **BUG-001**: Add `scan` CLI command (easy - scanner exists)
2. **BUG-002**: Set up Alembic migrations (medium)
3. **BUG-007**: Fix CI/CD test failures (investigation needed)

To satisfy original user context ("CONTEXT FOR CLAUDE"):

4. **BUG-006**: Implement alerts system ("notify me when conditions met")

After fixing BUG-001, BUG-002, BUG-006, and BUG-007, the platform meets:
- All PROMPT.md success criteria
- All original user requirements
- CI/CD green across all supported Python versions

---

## Future Specs (Not Blocking)

The following are enhancements beyond the original scope:

- SPEC-005: Alerts & Notifications (partially overlaps BUG-006)
- SPEC-006: Event Correlation Analysis
- SPEC-007: Probability Tracking & Visualization
- SPEC-008: Research Notebooks & Backtesting

These implement features mentioned in SPEC-004 "Future Considerations" section.
