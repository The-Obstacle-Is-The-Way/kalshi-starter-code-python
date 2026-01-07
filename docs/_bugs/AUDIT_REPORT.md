# Adversarial Audit Report (Bug Tracker Summary)

**Date:** 2026-01-07
**Auditor:** Codex CLI (GPT-5.2)
**Verdict:** **PASS (CI-LIKE GATES GREEN) — 1 follow-up bug open (P2)**

---

## Executive Summary

The platform is stable and test-gated. Linting, formatting, strict mypy, and the full test suite pass with ≥90% line coverage.

**Quality Gates (run):**
- `uv run ruff check .` ✅
- `uv run ruff format --check .` ✅
- `uv run mypy src/` ✅
- `uv run pytest --cov=src` ✅ → `401 passed, 6 skipped`, **Coverage: 90%**

**Note:** Live Kalshi API tests are skipped unless `KALSHI_RUN_LIVE_API=1`.

---

## Key Findings & Fixes

- **Truthiness traps (BUG-021, BUG-022):** Removed `if limit:` / `if min_ts:` style checks that mishandled `0` values; added regression tests.
- **Silent failure removal (BUG-021):** Notebook setup now logs failures instead of swallowing exceptions.
- **Export hardening (BUG-023):** `query_parquet()` now validates paths (defense-in-depth vs SQL-injection-through-path strings).
- **Legacy HTTP reliability (BUG-024):** Added request timeouts and fixed 2xx status check in `src/kalshi_research/clients.py`.
- **Portfolio auth wiring (BUG-019):** `kalshi portfolio sync` / `kalshi portfolio balance` now work end-to-end and support `KALSHI_PRIVATE_KEY_B64`.

---

## Remaining Risks / Follow-Ups

- **BUG-025 (P2, Open):** Portfolio positions do not compute cost basis (`avg_price_cents`) or mark price (`current_price_cents`), so unrealized P&L remains incomplete.
- **Live API drift:** Even with strong unit/integration coverage, real API responses can change; keep `tests/integration/api/test_public_api_live.py` runnable in a credentials-enabled environment.

---

## References

- Bug table: `docs/_bugs/README.md`
- Spec index: `docs/_specs/README.md`
