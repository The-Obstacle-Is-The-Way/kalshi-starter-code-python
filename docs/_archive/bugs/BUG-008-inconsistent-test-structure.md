# BUG-008: Inconsistent Test Directory Structure

**Status:** ✅ Fixed (2026-01-07)
**Priority:** P4 (Cleanup)
**Created:** 2026-01-06
**Fixed:** 2026-01-07
**Category:** Code Organization

---

## Problem

The test directory structure is inconsistent. Newer modules (created by Ralph loop) have properly nested test directories that mirror `src/`, while older modules have flat test files.

### Current State (Inconsistent)

```tree
tests/unit/
├── alerts/
├── analysis/
├── api/
├── data/
├── portfolio/
├── research/
├── test_cli.py
├── test_cli_extended.py
└── test_clients.py
```

### Desired State (Consistent)

```tree
tests/unit/
├── api/
│   ├── __init__.py
│   ├── test_client.py
│   ├── test_client_extended.py
│   ├── test_models.py
│   └── test_auth.py
├── data/
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_models.py
│   ├── test_repositories.py
│   ├── test_fetcher.py
│   ├── test_scheduler.py
│   └── test_export.py
├── analysis/
│   ├── __init__.py
│   ├── test_calibration.py
│   ├── test_correlation.py
│   ├── test_edge.py
│   ├── test_metrics.py
│   ├── test_scanner.py
│   └── test_visualization.py
├── alerts/                    # Already correct
│   └── ...
├── research/                  # Already correct
│   └── ...
├── test_cli.py               # Keep at root (tests root-level cli.py)
└── __init__.py
```

---

## Fix Applied

Reorganized unit tests to mirror the `src/` layout:

- `tests/unit/api/`
- `tests/unit/data/`
- `tests/unit/analysis/`
- `tests/unit/portfolio/`
- `tests/unit/research/`

Root-level unit tests remain only for truly root-level concerns (`cli.py` and legacy client glue).

---

## Implementation Steps

1. Create directories: `tests/unit/api/`, `tests/unit/data/`, `tests/unit/analysis/`
2. Add `__init__.py` to each new directory
3. Move files using `git mv` to preserve history
4. Update any import paths if needed
5. Run `pytest` to verify all tests still pass
6. Run `ruff check` to verify no import issues

---

## Verification

```bash
# All tests should still pass after restructure
uv run pytest tests/unit -v

# CI-like suite (excluding integration/slow)
uv run pytest -m "not integration and not slow"

# Structure should mirror src/
diff <(find src/kalshi_research -type d | sed 's|src/kalshi_research|tests/unit|' | sort) \
     <(find tests/unit -type d -not -name __pycache__ | sort)
```

---

## Notes

- This is a non-functional change (cleanup only)
- Improves codebase navigability
- Makes it easier to find tests for specific modules
- Priority P4 - can be done after all functional work is complete
