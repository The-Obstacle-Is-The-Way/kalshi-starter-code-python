# DEBT-047: Magic Numbers — Extract Policy-Encoding Literals to Constants

## Status

- **Severity:** MEDIUM
- **Effort:** L (multi-day mechanical refactor)
- **Blocking:** No (but it prevents subtle divergence bugs)
- **Target Date:** 2026-02-23
- **Status:** Active

## Problem

Policy-encoding literals (pagination limits, depth defaults, threshold ranges, budget defaults) are scattered across the codebase.
This guarantees future inconsistency — the same concept will quietly diverge across modules.

Clean Code standard: policy decisions should be named, centralized, and easy to audit.

## Evidence

Examples (2026-01-19 audit):

- Default pagination limit appears in multiple locations:
  - `src/kalshi_research/data/fetcher.py:177` (`limit=200`)
  - `src/kalshi_research/data/fetcher.py:188` (`limit=200`)
  - `src/kalshi_research/cli/scan.py:95` (`limit=200`)
  - `src/kalshi_research/cli/market.py:404` (`limit=200`)

- Default orderbook depth is a literal:
  - `src/kalshi_research/api/client.py:373` (`depth: int = 10`)

- Scanner close-race range is a literal:
  - `src/kalshi_research/analysis/scanner.py:174` (`(0.40, 0.60)`)

- Exa default budgets are literals:
  - `src/kalshi_research/exa/policy.py:25-27` (`0.05`, `0.25`, `1.00`)

Reproduce quickly:

```bash
rg -n \"\\blimit=200\\b\" src/kalshi_research
rg -n \"depth: int = 10|depth=10\" src/kalshi_research
rg -n \"\\(0\\.40, 0\\.60\\)\" src/kalshi_research
```

## Solution (Concrete)

1. Create a policy constants module (suggested: `src/kalshi_research/policy.py` or `src/kalshi_research/constants.py`)
2. Define named constants for every policy value, for example:
   - `DEFAULT_PAGINATION_LIMIT = 200`
   - `DEFAULT_ORDERBOOK_DEPTH = 10`
   - `DEFAULT_CLOSE_RACE_RANGE = (0.40, 0.60)`
   - `DEFAULT_EXA_BUDGETS_BY_MODE = {...}`
3. Replace all call sites to reference the named constant.
4. Add unit tests for constants that encode important business policy (e.g., scanner thresholds).

## Definition of Done (Objective)

- [x] All documented policy literals removed from function bodies (grep checks below return nothing):
  - `rg -n \"\\blimit=200\\b\" src/kalshi_research` ✓
  - `rg -n \"depth: int = 10|depth=10\" src/kalshi_research` ✓
  - `rg -n \"\\(0\\.40, 0\\.60\\)\" src/kalshi_research` (only in constants.py definition) ✓
- [x] All tests pass: `uv run pytest`
- [x] All quality gates pass: `uv run pre-commit run --all-files`

**Note:** Phase A/B complete. Phase C (Exa budget defaults) remains for future iteration.

## Acceptance Criteria (Phased)

- [x] Phase A: Introduce constants module and migrate pagination/depth defaults
- [x] Phase B: Migrate scanner/liquidity threshold literals
- [ ] Phase C: Migrate Exa budget defaults and any other cost policy literals
