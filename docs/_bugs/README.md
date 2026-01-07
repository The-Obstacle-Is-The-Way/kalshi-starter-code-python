# Kalshi Research Platform - Bug Tracker

**Audit Date:** 2026-01-07
**Auditor:** Gemini CLI (Deep Audit)

---

## Quality Gates (CI-like)

| Check | Status |
|-------|--------|
| `uv run ruff check .` | ✅ PASS |
| `uv run ruff format --check .` | ✅ PASS |
| `uv run mypy src/` | ✅ PASS |
| `uv run pytest` | ✅ PASS (`390 passed, 6 skipped`) |
| Coverage | ⏳ Measured in `AUDIT_REPORT.md` |

**Note:** Live Kalshi API tests are skipped unless `KALSHI_RUN_LIVE_API=1`.

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
| BUG-017 | P1 | 🔴 Open | `Event` model mismatch (`ticker` vs `event_ticker`) |
| BUG-018 | P2 | 🔴 Open | API Client lacks strict typing (`Any`, `dict`) |
| BUG-019 | P3 | 🔴 Open | Portfolio sync incomplete (`TODO`s) |
| BUG-020 | P3 | 🔴 Open | Visualization type ignores |
| BUG-021 | P2 | 🔴 Open | Broad exception handling patterns |
| BUG-022 | P3 | 🔴 Open | Potential N+1 queries in data layer |

---

## Open Bugs

See `docs/_bugs/BUG-*.md` for details on open issues.

---

## References

- Spec index: `docs/_specs/README.md`
- Full audit report: `AUDIT_REPORT.md`