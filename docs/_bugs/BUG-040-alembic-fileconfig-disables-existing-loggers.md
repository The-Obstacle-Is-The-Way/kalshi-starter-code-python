# BUG-040: Alembic `fileConfig()` disables application loggers (P1)

**Priority:** P1 (Order-dependent test failures / CI flake)
**Status:** 🟢 Fixed (2026-01-08)
**Found:** 2026-01-08
**Spec:** SPEC-012-developer-experience.md
**Checklist Ref:** CODE_AUDIT_CHECKLIST.md Section 9 (AI-Generated Tests: Reliability)

---

## Summary

Running Alembic migrations in-process (via `alembic.command.*`) was mutating the global Python logging system in a way
that disabled `kalshi_research.*` loggers. This made tests that assert warnings via `caplog` order-dependent: if the
Alembic migration test ran first, later tests expecting log output could see **no logs at all**.

---

## Evidence / Reproduction

`logging.config.fileConfig()` defaults `disable_existing_loggers=True`, which disables any pre-existing loggers that
aren't explicitly named in the logging config file.

In this repo, `alembic/env.py` calls:

```python
fileConfig(config.config_file_name)
```

This disables existing `kalshi_research.*` loggers after migrations run:

```bash
uv run python - <<'PY'
import logging
import logging.config

logger_name = "kalshi_research.api.client"
logger = logging.getLogger(logger_name)
print("before disabled:", logger.disabled)

logging.config.fileConfig("alembic.ini")
print("after disabled:", logging.getLogger(logger_name).disabled)
PY
```

---

## Root Cause

- `alembic/env.py` calls `fileConfig(config.config_file_name)` without overriding `disable_existing_loggers`.
- The default behavior (`disable_existing_loggers=True`) disables any already-instantiated loggers not listed in
  `alembic.ini` (which only configures `root`, `sqlalchemy.engine`, and `alembic`).
- Disabled loggers drop records before handlers/pytest capture ever see them, so `caplog.text` can become empty even
  when code correctly calls `logger.warning(...)`.

---

## Ironclad Fix

**File:** `alembic/env.py`

Change Alembic logging setup to preserve existing application loggers:

```python
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)
```

**Regression Guard:**

`tests/integration/data/test_alembic_migrations.py` now creates an application logger before running migrations and
asserts it is never disabled across upgrade/downgrade.

---

## Acceptance Criteria

- [x] Running Alembic migrations in-process does not disable `kalshi_research.*` loggers.
- [x] Full `pytest` suite is order-independent; `caplog` warnings assertions remain stable.
- [x] `uv run pytest` passes.

