# DEBT-007: A+ Engineering Robustness Delta (Operational Hardening Gaps)

**Priority:** P2 (Reliability / correctness confidence)
**Status:** 🔴 Active
**Created:** 2026-01-10

---

## Summary

The codebase is in strong shape (tests, typing, structured models, safe-by-default patterns in many places).
What keeps it from an “A+ robustness” grade is not a single bug, but a set of **confidence gaps** where the
runtime pathways and quality gates do not fully enforce the same invariants the code intends:

- Database schema evolution is not wired into the default runtime path (risk of schema drift on existing DBs).
- Pre-commit validates unit tests; CI validates unit + mocked E2E CLI pipelines (pre-commit E2E is optional).
- Live API contract tests exist but are not exercised in CI by default (gated) and should be run on a schedule.
- Several “must-never-happen” invariants are enforced in code but not in the database layer (optional hardening).
- The agent/trading safety harness (TradeExecutor / guardrails) is planned but not implemented (critical for autonomy).

This doc is the **A- → A+ delta dossier**: evidence-backed gaps and the clean, SSOT-aligned upgrades required.

---

## Evidence (SSOT)

### 1) DB schema evolution is not part of the default CLI runtime

- The default “initialize DB” path uses SQLAlchemy `create_all`:
  - `src/kalshi_research/data/database.py` → `DatabaseManager.create_tables()` uses `Base.metadata.create_all`
- The CLI uses `create_tables()` on common execution paths:
  - `src/kalshi_research/cli/data.py` → `data init`, `data sync-markets`, `data snapshot`, `data collect`
- Alembic exists and is tested, but is not invoked by CLI/runtime:
  - `tests/integration/data/test_alembic_migrations.py` validates upgrade/downgrade roundtrip
  - No CLI command currently runs `alembic upgrade head`

**Why it matters:** `create_all` does **not** upgrade existing tables. Once the schema evolves, existing
`data/kalshi.db` can drift from the ORM expectations without an automatic upgrade path.

### 2) E2E CLI pipelines are gated in CI (not pre-commit)

- Pre-commit quick test runs only unit tests:
  - `.pre-commit-config.yaml` → `uv run pytest tests/unit ...`
- CI test job runs unit tests and mocked E2E CLI pipelines:
  - `.github/workflows/ci.yml`
- The repo has mocked end-to-end coverage that exercises CLI entrypoints + DB + mocked HTTP:
  - `tests/e2e/test_data_pipeline.py`
  - `tests/e2e/test_news_pipeline.py`
  - `tests/e2e/test_analysis_pipeline.py`

**Why it matters:** The project is CLI-first. The mocked E2E suite is the fastest way to catch wiring
regressions (dependency wiring, command composition, serialization, path defaults).

### 3) Live API contract tests exist but are not executed in CI by default

- Live API tests are explicitly gated behind `KALSHI_RUN_LIVE_API=1`:
  - `tests/integration/api/test_public_api_live.py`
  - `tests/integration/api/test_authenticated_api_live.py`
- The CI integration job does not set `KALSHI_RUN_LIVE_API=1`:
  - `.github/workflows/ci.yml` → integration job runs `pytest tests/integration -m integration`
- The CI integration job currently provisions demo credentials under `DEMO_KEYID` / `DEMO_KEYFILE`, but the
  live tests read `KALSHI_KEY_ID` / `KALSHI_PRIVATE_KEY_PATH` (so live authenticated tests remain skipped).
  - `.github/workflows/ci.yml`
  - `tests/integration/api/test_authenticated_api_live.py`

Exa also has a real-API integration test that is intentionally opt-in (and can cost money):

- `tests/integration/exa/test_exa_research.py` is skipped unless `EXA_API_KEY` is set and asserts
  `exa_cost_dollars > 0`.

**Why it matters:** These tests are “trust anchors” for vendor drift; if they’re skipped or stale, they
provide false confidence.

### 4) DB invariants are not fully enforced at the DB layer (optional hardening)

- Portfolio invariants are encoded as unconstrained strings:
  - `src/kalshi_research/portfolio/models.py` (`Position.side`, `Trade.side`, `Trade.action`)

**Why it matters:** The application code keeps these values correct today, but DB-level constraints help
prevent silent corruption (manual edits, future code paths, migrations, bulk loads).

### 5) Agent safety harness is not implemented (required for autonomous execution)

- No `TradeExecutor` implementation exists in `src/kalshi_research/` (search returns none).
- Future/spec work exists (system intent) but is not enforced in code:
  - `docs/_specs/SPEC-034-trade-executor-safety-harness.md`
  - `docs/_future/TODO-00B-trade-executor-phase2.md`

**Why it matters:** The low-level client supports `dry_run`, but without a higher-level harness the system
can accidentally trade in any future autonomous loop.

### 6) Docs build is green but emits warnings (polish)

- `uv run mkdocs build --strict` passes, but emits INFO warnings about links to excluded `_archive/**`
  pages (because `mkdocs.yml` excludes `_archive/**` from the built site while internal docs still link to
  those files).

**Why it matters:** It’s not a correctness bug, but it’s a signal that the docs are not “warning clean” at
A+ polish level.

---

## Impact

- **Schema drift risk:** Upgrading code can break existing DBs silently until runtime.
- **False-green CI risk:** CLI wiring regressions can ship if only unit tests run by default.
- **Vendor drift risk:** Live endpoints can change without us noticing quickly.
- **Safety risk (future autonomy):** Lack of a trade safety harness increases the chance of unintended orders.

---

## Clean Fix Specification (A+ Path)

### A) Make migrations the default upgrade path (DB safety)

Add a supported runtime upgrade command (and docs):

- New CLI command: `kalshi data migrate` (or `kalshi data upgrade`)
  - Runs Alembic `upgrade head` against the configured DB URL.
  - Prints current → target revision.
  - Is safe to run repeatedly (idempotent).
- Optional: on startup, detect schema mismatch and print a clear “run migrate” instruction.

**Acceptance criteria**
- Existing DBs are upgraded without deleting `data/kalshi.db`.
- CI validates `kalshi data migrate` on a temp DB.

### B) Gate the CLI pipelines in CI (confidence)

Run mocked E2E tests in CI by default:

- Add `pytest tests/e2e -m "not integration and not slow"` to `.github/workflows/ci.yml` test job.

**Acceptance criteria**
- [x] All mocked E2E tests pass (`uv run pytest tests/e2e -m "not integration and not slow"`).
- [x] Live demo E2E continues to skip safely without creds.

### C) Fix and quarantine live API contract tests (vendor drift)

- Update live tests to match SSOT types (e.g., `PortfolioBalance`).
- Keep them gated behind `KALSHI_RUN_LIVE_API=1` for PR reliability.
- Add a scheduled workflow (nightly/weekly) that sets `KALSHI_RUN_LIVE_API=1` and runs live tests using
  dedicated canary credentials.
- For Exa live tests, run on a schedule only with explicit budgets and max-results limits (paid API).

**Acceptance criteria**
- Live tests are correct when enabled.
- Vendor drift is detected within 24h of a breaking change (scheduled run).

**Cost/risk guidance**
- Kalshi live reads (exchange/markets/orderbook/balance/positions) generally do not cost money, but they do
  consume rate limits and require secrets management (use dedicated demo canary credentials).
- Exa live tests **can cost money**; keep them out of PR CI and run them on a budgeted schedule.

### D) Optional hardening: DB-level invariants

Introduce CHECK constraints (via Alembic) for:

- `positions.side IN ('yes', 'no')`
- `trades.side IN ('yes', 'no')`
- `trades.action IN ('buy', 'sell')`

**Acceptance criteria**
- Invalid rows cannot be inserted at DB layer.
- Migrations include any required data cleanup for pre-existing invalid rows (if any).

### E) Implement TradeExecutor safety harness before autonomy (critical)

Implement the “safe trading boundary” described in `SPEC-034`:

- Explicit environment gating (demo vs prod).
- Global kill-switch and per-run caps (max orders, max notional, max loss).
- Enforced dry-run default unless explicitly overridden.
- Audit logging of every intended order with deterministic serialization.

**Acceptance criteria**
- A future agent loop cannot place an order without passing through the harness.
- Harness is unit-tested with mocked client network calls.

---

## Related

- `docs/_debt/security-audit.md` (agent safety / prompt injection notes)
- `docs/_specs/SPEC-034-trade-executor-safety-harness.md`
- `docs/_specs/SPEC-027-settlement-timestamp.md` (schema evolution precedent)
- `docs/developer/testing.md` (test tiers, CI wiring, cost/cadence)
