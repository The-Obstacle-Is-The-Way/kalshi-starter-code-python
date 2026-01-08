# BUG-039: CLI does not load `.env` for authenticated commands (P1)

**Priority:** P1 (Breaks portfolio/auth flows in default local setup)
**Status:** ✅ Fixed (2026-01-07)
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Spec:** SPEC-012-developer-experience.md, SPEC-013-portfolio-sync-implementation.md
**Checklist Ref:** CODE_AUDIT_CHECKLIST.md Section 11 (Incomplete Implementations)

---

## Summary

The repository instructs users to configure credentials via `.env`, and tests load `.env`, but the `kalshi` CLI did not.

Result: authenticated CLI commands (e.g. `portfolio balance`, `portfolio sync`) failed with “requires authentication”
even when a valid `.env` file existed.

---

## Reproduction

1. Ensure `.env` exists with valid credentials:
   - `KALSHI_KEY_ID=...`
   - `KALSHI_PRIVATE_KEY_PATH=...` (or `KALSHI_PRIVATE_KEY_B64=...`)
2. Run:

```bash
uv run kalshi portfolio balance
```

**Before fix:** exits with error “Balance requires authentication”.

---

## Root Cause

`tests/conftest.py` calls `dotenv.load_dotenv()` but `src/kalshi_research/cli.py` did not.

So running the CLI outside pytest ignored `.env` unless the user manually exported environment variables.

---

## Fix Applied

**File:** `src/kalshi_research/cli.py`

- Load `.env` on CLI invocation via the Typer callback:
  - `load_dotenv(find_dotenv(usecwd=True))`

This keeps behavior explicit to the CLI and supports running from subdirectories (parent search).

---

## Acceptance Criteria

- [x] With a valid `.env`, `uv run kalshi portfolio balance` works without manual `export ...`
- [x] Unit test ensures `.env` is read during CLI invocation

---

## Regression Test Added

- `tests/unit/test_cli_extended.py::test_portfolio_balance_loads_dotenv`

