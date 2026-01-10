# DEBT-008: Dead Code Cleanup (True Slop)

**Status:** 🔴 Active
**Priority:** P2
**Owner:** TBD
**Created:** 2026-01-10
**Audit Source:** [`bloat.md`](bloat.md)

## Summary

The codebase contains approximately 400 lines of "True Slop"—code that was generated or implemented but never wired into the application logic, CLI, or API surface. This code is dead weight that confuses maintenance and agents.

## Scope (Strictly Delete)

These items have been verified as **unused** (except in their own unit tests) via deep trace analysis.

### 1. `EdgeDetector` Class
- **File:** `src/kalshi_research/analysis/edge.py`
- **Verdict:** TRUE SLOP.
- **Reason:** Exported in `__init__` but never instantiated by any app code. Speculative feature that was never integrated.
- **Action:** Delete `EdgeDetector` class. Keep `Edge` dataclass (if used by notebooks).

### 2. `TemporalValidator` Class
- **File:** `src/kalshi_research/research/thesis.py`
- **Verdict:** TRUE SLOP.
- **Reason:** Thesis validation is handled by Pydantic models. This class is redundant and unused.
- **Action:** Delete entire class.

### 3. Unused Analysis Methods
- **File:** `src/kalshi_research/analysis/metrics.py`
    - `compute_spread_stats`
    - `compute_volatility`
    - `compute_volume_profile`
- **File:** `src/kalshi_research/analysis/scanner.py`
    - `scan_all`
- **Verdict:** TRUE SLOP.
- **Reason:** Never called by the CLI or analysis pipeline.
- **Action:** Delete methods.

### 4. Unused Repository Methods (YAGNI)
- **File:** `src/kalshi_research/data/repositories/*.py`
    - `get_by_series`
    - `get_by_category`
    - `get_expiring_before`
    - `get_latest_batch`
    - `delete_older_than`
    - `get_by_result`
    - `count_by_result`
- **Verdict:** YAGNI CRUFT.
- **Reason:** Speculative queries that were never used.
- **Action:** Delete methods.

## Verification Plan

1. **Delete** the items listed above.
2. **Run Tests:** `uv run pytest`. Expect failures in unit tests specifically testing these dead items.
3. **Delete Tests:** Remove the unit tests that covered the deleted code.
4. **Verify App:** Run `uv run kalshi scan opportunities` to ensure no regression in core flows.
