# BUG-008: Inconsistent Test Directory Structure

**Status:** Open
**Priority:** P4 (Cleanup)
**Created:** 2026-01-06
**Category:** Code Organization

---

## Problem

The test directory structure is inconsistent. Newer modules (created by Ralph loop) have properly nested test directories that mirror `src/`, while older modules have flat test files.

### Current State (Inconsistent)

```
tests/unit/
├── alerts/                    # ✅ NESTED (mirrors src/kalshi_research/alerts/)
│   ├── __init__.py
│   ├── test_conditions.py
│   ├── test_monitor.py
│   └── test_notifiers.py
├── research/                  # ✅ NESTED (mirrors src/kalshi_research/research/)
│   ├── __init__.py
│   ├── test_backtest.py
│   └── test_notebook_utils.py
├── test_api_client.py         # ❌ FLAT (should be api/test_client.py)
├── test_api_models.py         # ❌ FLAT (should be api/test_models.py)
├── test_api_auth.py           # ❌ FLAT (should be api/test_auth.py)
├── test_data_database.py      # ❌ FLAT (should be data/test_database.py)
├── test_data_models.py        # ❌ FLAT (should be data/test_models.py)
├── test_data_repositories.py  # ❌ FLAT (should be data/test_repositories.py)
├── test_data_fetcher.py       # ❌ FLAT (should be data/test_fetcher.py)
├── test_data_scheduler.py     # ❌ FLAT (should be data/test_scheduler.py)
├── test_data_export.py        # ❌ FLAT (should be data/test_export.py)
├── test_analysis_*.py         # ❌ FLAT (should be analysis/*.py)
├── test_cli.py                # ✅ OK (cli.py is at root level)
└── test_clients.py            # ❌ FLAT (unclear what this tests)
```

### Desired State (Consistent)

```
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

## Files to Move

| Current Location | New Location |
|-----------------|--------------|
| `test_api_client.py` | `api/test_client.py` |
| `test_api_client_extended.py` | `api/test_client_extended.py` |
| `test_api_models.py` | `api/test_models.py` |
| `test_api_auth.py` | `api/test_auth.py` |
| `test_data_database.py` | `data/test_database.py` |
| `test_data_models.py` | `data/test_models.py` |
| `test_data_repositories.py` | `data/test_repositories.py` |
| `test_data_fetcher.py` | `data/test_fetcher.py` |
| `test_data_scheduler.py` | `data/test_scheduler.py` |
| `test_data_export.py` | `data/test_export.py` |
| `test_analysis_calibration.py` | `analysis/test_calibration.py` |
| `test_analysis_correlation.py` | `analysis/test_correlation.py` |
| `test_analysis_edge.py` | `analysis/test_edge.py` |
| `test_analysis_metrics.py` | `analysis/test_metrics.py` |
| `test_analysis_scanner.py` | `analysis/test_scanner.py` |
| `test_analysis_visualization.py` | `analysis/test_visualization.py` |
| `test_clients.py` | Investigate & move appropriately |
| `test_research_thesis.py` | `research/test_thesis.py` |

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
