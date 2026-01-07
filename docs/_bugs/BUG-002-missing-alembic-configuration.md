# BUG-002: Missing Alembic Migration Configuration

**Priority:** P2
**Status:** ✓ FIXED (2026-01-06)
**Discovered:** 2026-01-06
**Spec Reference:** PROMPT.md Phase 3, SPEC-003 Section 3.5

---

## Summary

The Alembic database migration framework is not configured. SPEC-003 Section 3.5 explicitly requires Alembic configuration for async SQLAlchemy migrations.

## Expected Behavior

Per SPEC-003 requirements:
```
alembic/
├── env.py                # Async migration runner
├── versions/             # Migration scripts
└── alembic.ini           # Configuration
```

Should support:
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

## Current Behavior

```bash
$ ls alembic/
ls: alembic/: No such file or directory
```

The `alembic` package is installed (in pyproject.toml dependencies) but not configured.

## Root Cause

Alembic initialization was never run. The migration environment needs to be created and configured for async SQLAlchemy.

## Fix

1. Initialize Alembic:
```bash
cd /path/to/project
alembic init alembic
```

2. Configure `alembic/env.py` for async (per SPEC-003 Section 3.5):
```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from kalshi_research.data.models import Base

target_metadata = Base.metadata
config = context.config

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())
```

3. Update `alembic.ini` with SQLite URL:
```ini
sqlalchemy.url = sqlite+aiosqlite:///data/kalshi.db
```

## Acceptance Criteria

- [ ] `alembic/` directory exists with proper structure
- [ ] `alembic/env.py` configured for async SQLAlchemy
- [ ] `alembic revision --autogenerate` works
- [ ] `alembic upgrade head` creates tables
- [ ] CI can run migrations
