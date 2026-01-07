# Kalshi Research Platform — Adversarial Audit Report

**Date:** 2026-01-07  
**Auditor:** Codex CLI (GPT-5.2)  
**Verdict:** **PASS (core research pipeline + quality gates)** — deferred items documented

---

## Executive Summary

The platform is production-ready for **local research workflows**:

- DB init/sync/snapshot/export works against SQLite
- Market scanning and analysis commands run end-to-end
- Strict quality gates are green (`ruff`, `mypy --strict`, `pytest`)

The audit also surfaced real-world API mismatches and integration gaps (documented as BUG-011..BUG-016). All discovered issues were fixed with regression tests.

**Deferred scope:** authenticated portfolio sync/balance remain stubs (SPEC-011 explicitly marks these as deferred).

---

## Verification & Methodology

- **Quality gates:** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src/`, `uv run pytest`
- **Integration tests:** SQLite + Alembic + CLI (Typer `CliRunner`) + HTTP error simulation via `respx`
- **E2E tests:** pipeline-style tests under `tests/e2e/` (no live network by default)
- **Live API sanity tests:** gated behind `KALSHI_RUN_LIVE_API=1` (skipped by default)

---

## Test Suite (Minimal Mocks)

### API integration (`tests/integration/api/`)
- Error handling: 400/401/429/500 + timeouts + retry behavior (via `respx`)
- Live public API smoke/pagination tests: `tests/integration/api/test_public_api_live.py` (skipped unless enabled)

### Database integration (`tests/integration/data/`)
- Real SQLite CRUD lifecycle for repositories
- Foreign key enforcement + concurrent writes
- Alembic upgrade/downgrade roundtrip

### CLI integration (`tests/integration/cli/`)
- Real CLI invocations (exit codes, error output, flag combinations)
- Uses real SQLite + `respx` for deterministic API responses

### End-to-end (`tests/e2e/`)
- Full data pipeline: init → sync → snapshot/export → verify
- Analysis pipeline: sync → scan → alert-style evaluation

---

## Bugs Found, Fixed, and Locked In With Tests

| Bug | Priority | Symptom | Root Cause | Fix | Regression Coverage |
|-----|----------|---------|------------|-----|--------------------|
| BUG-011 | P0 | `/events` requests fail at `limit=1000` | API max is 200 | Pagination now caps `/events` page size to 200 | `tests/unit/api/test_client.py`, `tests/integration/api/test_public_api_live.py` |
| BUG-012 | P1 | Market parsing fails on `status="initialized"` | Enum missing value | Added enum member | `tests/unit/api/test_models.py`, `tests/integration/api/test_public_api_live.py` |
| BUG-013 | P1 | Fresh DB missing portfolio tables | Models not imported into `Base.metadata` | Import portfolio models during DB init + in Alembic env | `tests/integration/data/test_database_manager_integration.py`, `tests/integration/data/test_alembic_migrations.py` |
| BUG-014 | P1 | `kalshi analysis calibration` crashed | CLI called non-existent analyzer method | CLI now builds forecasts/outcomes from DB, then calls pure calibration math | `tests/integration/cli/test_cli_commands.py`, `tests/unit/test_cli_extended.py` |
| BUG-015 | P1 | `kalshi scan movers` timezone crash | Naive/aware datetime comparisons | Normalize timestamps to UTC for comparisons | `tests/integration/cli/test_cli_commands.py` |
| BUG-016 | P1 | `kalshi data snapshot` fails on new DB | Tables not ensured before insert | Snapshot now calls `create_tables()` first | `tests/integration/cli/test_cli_commands.py`, `tests/e2e/test_data_pipeline.py` |

Additional critical correctness fix (not originally tracked as a bug): **portfolio ↔ thesis linkage** was broken due to `thesis_id` being treated as an integer while thesis IDs are UUID strings; schema + CLI behavior now use string thesis IDs and include a migration.

---

## Code Quality Audit (SOLID / DRY / Patterns)

### SOLID (key outcomes)
- **SRP improved:** calibration math stays in `CalibrationAnalyzer` (pure compute), while CLI owns orchestration and IO.
- **Dependency boundaries enforced:** HTTP behavior stays in `api/`; persistence stays in `data/`; CLI composes them.
- **Correctness over decorators:** retry behavior is now explicit and testable (no “decorator hides config” failure modes).

### DRY / duplication
- Pagination and retry logic are centralized in the API client (cursor iterators + explicit retry loop).
- CLI “single-shot” loops gained `--once` flags for testability without duplicating command logic.

### Patterns used intentionally
- **Repository pattern:** kept as the DB boundary; integration tests validate CRUD behavior against real SQLite.
- **Adapter boundary:** `KalshiPublicClient` adapts HTTP → typed models; regression tests cover real-world response variance.

---

## Risks / Deferred Items

- **Authenticated portfolio sync & live balance:** `kalshi portfolio sync` and `kalshi portfolio balance` are stubs (deferred in SPEC-011). Shipping a production trading assistant would require implementing authenticated endpoints + integration tests with credentials.
- **Alerts monitor daemon mode:** `--daemon` exists but is explicitly noted as not implemented (foreground fallback).

---

## How To Re-Run (Locally)

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest

# Enable live public API integration tests
KALSHI_RUN_LIVE_API=1 uv run pytest -m integration tests/integration/api/test_public_api_live.py
```

---

## Coverage

**Measured coverage (branch enabled): 90% overall** (`uv run pytest -p no:sugar --cov`)

```bash
uv run pytest -p no:sugar --cov
```

Notable lower-coverage areas (still within ≥90% overall target):
- `src/kalshi_research/api/client.py` (public + auth client wiring)
- `src/kalshi_research/cli.py` (breadth of commands/branches)
- `src/kalshi_research/research/notebook_utils.py` (notebook helpers)
