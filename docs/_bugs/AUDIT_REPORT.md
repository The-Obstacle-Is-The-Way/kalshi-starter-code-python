# Adversarial Audit Report (Bug Tracker Summary)

**Date:** 2026-01-08
**Auditor:** Codex CLI (GPT-5.2)
**Verdict:** **PASS (CI-LIKE GATES GREEN) — no follow-up bugs open**

---

## Executive Summary

The platform is stable and test-gated. Linting, formatting, strict mypy, and the fast local test suite are green.

**Quality Gates (run):**
- `uv run ruff check .` ✅
- `uv run ruff format --check .` ✅
- `uv run mypy src/ --strict` ✅
- `uv run pytest -m "not integration and not slow"` ✅ → `412 passed, 34 deselected`
- `uv run pytest` ✅ → `438 passed, 8 skipped`

**Note:** Integration tests hit the live public API and may be rate-limit sensitive.

---

## Key Findings & Fixes

- **Truthiness traps (BUG-021, BUG-022):** Removed `if limit:` / `if min_ts:` style checks that mishandled `0` values; added regression tests.
- **More truthiness traps (BUG-036, BUG-037):** Fixed silent `0`/`0.0` fallbacks in CLI metrics + edge histogram; added regression tests.
- **Inverse-sum pricing safety (BUG-038):** Excluded one-sided quotes from midpoint-based inverse-sum and arbitrage pricing; added regression coverage.
- **DX fix for auth (BUG-039):** CLI now loads `.env` on invocation, matching repo guidance and pytest behavior; added unit coverage.
- **Test order flake (BUG-040):** Alembic migrations no longer disable `kalshi_research.*` loggers when run in-process; added a regression guard.
- **Silent failure removal (BUG-021):** Notebook setup now logs failures instead of swallowing exceptions.
- **Export hardening (BUG-023):** `query_parquet()` now validates paths (defense-in-depth vs SQL-injection-through-path strings).
- **Legacy HTTP reliability (BUG-024):** Added request timeouts and fixed 2xx status check in `src/kalshi_research/clients.py`.
- **Portfolio auth wiring (BUG-019):** `kalshi portfolio sync` / `kalshi portfolio balance` now work end-to-end and support `KALSHI_PRIVATE_KEY_B64`.

---

## Remaining Risks / Follow-Ups

- **Live API drift:** Even with strong unit/integration coverage, real API responses can change; keep `tests/integration/api/test_public_api_live.py` runnable in a credentials-enabled environment.

---

## References

- Bug table: `docs/_bugs/README.md`
- Spec index: `docs/_specs/README.md`
