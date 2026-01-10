# BUG-052: `market list --status active` crashes with traceback

**Priority**: Low
**Status**: Fixed
**Created**: 2026-01-10
**Resolved**: 2026-01-10

## Symptom

Running:

```bash
uv run kalshi market list --status active
```

Crashes with a full traceback ending in:

```
KalshiAPIError: API Error 400: ... "invalid status filter"
```

## Root Cause

- Kalshi uses **different status enums** for:
  - response payloads (e.g., `active`, `determined`, `finalized`)
  - `/markets` **filter params** (e.g., `open`, `closed`, `settled`, etc.)
- The CLI accepted any string for `--status` and did not catch `KalshiAPIError`, so a user typo became a traceback.

## Resolution

- Validate `market list --status` against the allowed filter values.
- Treat the common user mistake `active` as an alias for `open` (with a warning).
- Catch `KalshiAPIError` in the CLI and exit cleanly.

## Changes Made

- `src/kalshi_research/cli/market.py`: validate/normalize status filter and handle API errors.
- `tests/unit/cli/test_market.py`: regression tests for `active → open` and invalid status rejection.

## Acceptance Criteria

- [x] `uv run kalshi market list --status active` prints a warning and succeeds (uses `open`)
- [x] Invalid status values return exit code 2 and show valid options (no traceback)
