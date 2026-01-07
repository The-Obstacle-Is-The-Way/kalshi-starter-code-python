# BUG-020: Visualization Strict Typing Friction (P4)

**Priority:** P4 (Low - Tooling / Developer Experience)
**Status:** ✅ Fixed
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Spec:** SPEC-007-probability-tracking-visualization.md

---

## Summary

Strict mypy + incomplete third-party stubs caused typing failures in visualization utilities.

---

## Root Cause

`matplotlib` typing stubs are incomplete in places (notably around datetime inputs and formatter/locator constructors), which triggered `mypy --strict` failures.

---

## Fix Applied

- Removed the need for `# type: ignore` in `src/kalshi_research/analysis/visualization.py` by:
  - Using `Any`-typed adapters only at the library boundary
  - Keeping business logic strictly typed

---

## Regression Tests

- `uv run mypy src/` is green in CI-like gates.
