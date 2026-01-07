# BUG-019: Portfolio Sync Implementation Incomplete (P3)

**Priority:** P3 (Medium - Feature gap)
**Status:** ✅ Fixed
**Found:** 2026-01-07
**Fixed:** 2026-01-07
**Spec:** SPEC-013-portfolio-sync-implementation.md

---

## Summary

Portfolio sync existed only as placeholders, preventing users from syncing positions/fills and making portfolio commands misleading.

---

## Root Cause

- Authenticated API endpoints existed but portfolio sync was not wired end-to-end (API client + syncer + CLI).
- Tests assumed `PortfolioSyncer` was a stub and did not exercise real sync paths.

---

## Fix Applied

- Implemented authenticated portfolio endpoints:
  - `KalshiClient.get_positions()` and `KalshiClient.get_fills()` in `src/kalshi_research/api/client.py`
- Implemented real DB persistence + idempotency in `src/kalshi_research/portfolio/syncer.py`
- Wired the CLI commands so users can actually run the feature:
  - `kalshi portfolio sync` and `kalshi portfolio balance` in `src/kalshi_research/cli.py`
- Added support for loading private keys from env base64 (`KALSHI_PRIVATE_KEY_B64`) in `src/kalshi_research/api/auth.py`

---

## Regression Tests Added

- `tests/unit/portfolio/test_syncer.py`
- `tests/integration/cli/test_cli_commands.py`

---

## Follow-Ups

None. Cost basis + mark pricing follow-up was addressed in BUG-025.
