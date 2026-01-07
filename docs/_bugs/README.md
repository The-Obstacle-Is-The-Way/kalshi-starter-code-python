# Kalshi Research Platform - Bug Tracker

**Audit Date:** 2026-01-07
**Auditor:** Codex CLI (GPT-5.2)

---

## Quality Gates (CI-like)

| Check | Status |
|-------|--------|
| `uv run ruff check .` | ✅ PASS |
| `uv run ruff format --check .` | ✅ PASS |
| `uv run mypy src/ --strict` | ✅ PASS |
| `uv run pytest -m "not integration and not slow"` | ✅ PASS |

**Test Results:** `398 passed, 34 deselected` (integration + slow excluded).

---

## Bug Status Overview

| ID | Priority | Status | Summary |
|----|----------|--------|---------|
| BUG-001 | P1 | ✅ Fixed | Missing `scan` CLI command |
| BUG-002 | P2 | ✅ Fixed | Missing Alembic configuration |
| BUG-003 | P3 | ✅ Fixed | Missing notebooks directory |
| BUG-004 | P3 | ✅ Fixed | Missing analysis modules |
| BUG-005 | P3 | ✅ Fixed | Missing research/backtest modules |
| BUG-006 | P1 | ✅ Fixed | Missing alerts system |
| BUG-007 | P1 | ✅ Fixed | CI/CD test failures |
| BUG-008 | P4 | ✅ Fixed | Inconsistent test structure |
| BUG-009 | P3 | ✅ Fixed | Incomplete CLI commands |
| BUG-010 | P4 | ✅ Fixed | Portfolio ↔ thesis linking commands |
| BUG-011 | P0 | ✅ Fixed | `/events` `limit` capped to 200 |
| BUG-012 | P1 | ✅ Fixed | `MarketStatus` missing `"initialized"` |
| BUG-013 | P1 | ✅ Fixed | DB init omitted portfolio tables |
| BUG-014 | P1 | ✅ Fixed | `kalshi analysis calibration` crash |
| BUG-015 | P1 | ✅ Fixed | `kalshi scan movers` timezone crash |
| BUG-016 | P1 | ✅ Fixed | `kalshi data snapshot` missing init |
| BUG-018 | P4 | ✅ Fixed | API Client internal typing (Tech Debt) |
| BUG-019 | P3 | ✅ Fixed | Portfolio sync + CLI wiring |
| BUG-020 | P4 | ✅ Fixed | Visualization strict typing friction |
| BUG-021 | P3 | ✅ Fixed | Notebook utils limit + exception handling |
| BUG-022 | P2 | ✅ Fixed | API client 0-valued params + fills limit cap |
| BUG-023 | P2 | ✅ Fixed | `query_parquet()` path validation |
| BUG-024 | P2 | ✅ Fixed | Legacy `requests` client timeouts |
| BUG-025 | P2 | ✅ Fixed | Positions missing cost basis + mark price |
| BUG-026 | P0 | ✅ Fixed | `kalshi data snapshot` FOREIGN KEY constraint failure |
| BUG-027 | P1 | ✅ Fixed | Pagination cap silently truncates markets/events |
| BUG-028 | P2 | ✅ Fixed | `kalshi alerts monitor --once` UX + progress |
| BUG-029 | P2 | ✅ Fixed | Close-race scanner returns illiquid/unpriced markets |
| BUG-030 | P3 | ✅ Fixed | Arbitrage scan false positives from 0/0 markets |
| BUG-031 | P2 | ✅ Fixed | `kalshi scan movers` percent units wrong |
| BUG-032 | P3 | ✅ Fixed | `kalshi scan arbitrage` silently truncates tickers |
| BUG-033 | P0 | ✅ Fixed | Market model API schema mismatch (negative liquidity, missing status) |

---

## Open Bugs

None. All bugs have been fixed. 🎉

---

## References

- Spec index: `docs/_specs/README.md`
- Full audit report: `AUDIT_REPORT.md`
