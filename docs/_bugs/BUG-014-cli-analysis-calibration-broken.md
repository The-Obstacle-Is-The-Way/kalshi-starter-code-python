# BUG-014: `kalshi analysis calibration` Crashes (P1)

**Priority:** P1 (High - CLI command unusable)
**Status:** ✅ Fixed
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Spec:** SPEC-004-research-analysis-framework.md, SPEC-010-cli-completeness.md

---

## Summary

`kalshi analysis calibration` instantiated `CalibrationAnalyzer` with a `PriceRepository` and called a non-existent `analyze()` method, causing a runtime failure.

---

## Root Cause

`src/kalshi_research/analysis/calibration.py` implements pure calibration math (`compute_calibration`) and does not accept repositories or provide an async DB-backed `analyze()` method. The CLI wiring was incorrect and masked with `type: ignore`.

---

## Fix Applied

- Reworked the CLI command to build forecasts/outcomes from DB data:
  - Load settlements over the requested time window
  - For each settled market, use the latest snapshot before settlement as the forecast
  - Compute calibration via `CalibrationAnalyzer.compute_calibration()`
- If no settled markets with price history exist, print a friendly message and exit cleanly.

---

## Regression Tests Added

- `tests/integration/cli/test_cli_commands.py`
