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

Examples (2026-01-21 audit):

- **Already migrated to named constants** (Phase A/B complete):
  - Pagination limit: `DEFAULT_PAGINATION_LIMIT = 200` in `src/kalshi_research/constants.py`
  - Orderbook depth: `DEFAULT_ORDERBOOK_DEPTH = 10` in `src/kalshi_research/constants.py`
  - Scanner thresholds: `DEFAULT_CLOSE_RACE_RANGE = (0.40, 0.60)` and related constants

Remaining policy literals worth consolidating (Phase C):
  - Agent per-run defaults:
    - `src/kalshi_research/agent/orchestrator.py` (`max_exa_usd=0.25`, `max_llm_usd=0.25`)
    - `src/kalshi_research/cli/agent.py` (`--max-exa-usd=0.25`, `--max-llm-usd=0.25`)
  - Exa pricing estimates (vendor-pricing-sensitive, should be centralized/documented as such):
    - `src/kalshi_research/exa/policy.py` (search tier costs, answer costs, safety_factor)

Reproduce quickly:

```bash
rg -n \"\\blimit=200\\b\" src/kalshi_research
rg -n \"depth: int = 10|depth=10\" src/kalshi_research
rg -n \"\\(0\\.40, 0\\.60\\)\" src/kalshi_research
rg -n \"max_exa_usd: float = 0\\.25|max_llm_usd: float = 0\\.25\" src/kalshi_research
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

- [x] Phase A/B policy literals removed from function bodies (grep checks below return nothing):
  - `rg -n \"\\blimit=200\\b\" src/kalshi_research` ✓
  - `rg -n \"depth: int = 10|depth=10\" src/kalshi_research` ✓
  - `rg -n \"\\(0\\.40, 0\\.60\\)\" src/kalshi_research` (only in constants.py definition) ✓
- [ ] Phase C policy literals reduced: agent default budgets + Exa pricing estimate constants are named/centralized
- [x] All tests pass: `uv run pytest`
- [x] All quality gates pass: `uv run pre-commit run --all-files`

**Note:** Phase A/B complete. Phase C (cost/budget policy literals) remains for future iteration.

## Acceptance Criteria (Phased)

- [x] Phase A: Introduce constants module and migrate pagination/depth defaults
- [x] Phase B: Migrate scanner/liquidity threshold literals
- [ ] Phase C: Migrate remaining cost/budget policy literals (agent defaults + Exa pricing estimates)
