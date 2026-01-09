# Repository Guidelines

## CRITICAL: Commit Safety Protocol

**NEVER commit code without running quality gates first.** A previous incident introduced syntax corruption (`时不时` instead of `import`) that broke the entire codebase. This was caused by committing without pre-commit hooks installed.

### MANDATORY Before ANY Commit

```bash
# 1. FIRST: Ensure pre-commit hooks are installed (do this ONCE after clone)
uv run pre-commit install

# 2. ALWAYS run pre-commit before staging/committing
uv run pre-commit run --all-files

# 3. If pre-commit passes, THEN commit
git add . && git commit -m "Your message"

# 4. NEVER use --no-verify to bypass hooks
# git commit --no-verify  # <- FORBIDDEN
```

### Pre-commit Will Automatically Check

1. **Python syntax validation** (`check-ast`) - Catches encoding corruption
2. **Ruff linting** - Code quality and style
3. **Ruff formatting** - Consistent formatting
4. **Mypy type checking** - Static type safety
5. **Unit tests** - Quick smoke test

### FORBIDDEN Patterns

- **NO `# type: ignore`** - Fix the type error properly
- **NO untyped `Any`** - Use specific types (exception: JSON dicts as `dict[str, Any]`)
- **NO `--no-verify` commits** - Always run pre-commit hooks
- **NO manual git commits without pre-commit** - Always verify first

## Project Structure & Module Organization

- `src/kalshi_research/`: main package (src-layout)
  - `api/`: Kalshi HTTP clients + Pydantic models
  - `data/`: async SQLite/SQLAlchemy persistence, repositories, exports
  - `analysis/`, `research/`, `alerts/`, `portfolio/`: domain modules
  - `cli/`: Typer CLI package entrypoint (`kalshi`)
- `tests/`: `unit/` mirrors `src/`; `integration/` hits real API (needs creds)
- `docs/`: usage guides plus specs/bug tracker (`docs/_specs/`, `docs/_bugs/`)
- `alembic/`, `alembic.ini`: database migrations
- `data/`: local runtime artifacts (e.g., `data/kalshi.db`, exports)

## Build, Test, and Development Commands

Preferred dependency manager is `uv` (see `uv.lock`):

```bash
uv sync --all-extras              # install dev + research extras
uv run pre-commit install         # CRITICAL: Install commit hooks
uv run kalshi --help              # run CLI without global install
uv run ruff check .               # lint (CI)
uv run ruff format --check .      # format check (CI); drop --check to format
uv run mypy src/                  # strict type checking (CI)
uv run pytest -m "not integration and not slow"  # fast local suite (CI-like)
```

## Coding Style & Naming Conventions

- Python 3.11+, 4-space indentation; `ruff` is the formatter/linter (line length 100).
- Names: `snake_case` for functions/variables, `PascalCase` for classes, `test_*.py` for tests.
- Keep boundaries clear: HTTP logic stays in `api/`; DB access goes through `data/repositories/`.

## Testing Guidelines

- `pytest` + `pytest-asyncio` (see markers in `pyproject.toml`: `unit`, `integration`, `slow`).
- Prefer testing real domain logic; only mock at system boundaries (HTTP, filesystem).
- Put new tests under `tests/unit/<module>/...` to match the `src/` layout.

## Commit & Pull Request Guidelines

- **ALWAYS run `uv run pre-commit run --all-files` before committing**
- Use atomic commits; follow the repo's common pattern: `[BUG-###] Fix: ...`, `[SPEC-###] Implement: ...`, `[FEATURE] Add: ...`, `[QUALITY-###] Fix: ...`.
- PRs should include: what changed, how it was tested (commands run), and any user-facing doc updates (often `docs/how-to/usage.md` / `docs/tutorials/quickstart.md`).
- Before review, ensure local checks match CI: `ruff`, `mypy`, and `pytest` are green.

## Security & Configuration Tips

- Copy `.env.example` → `.env`; never commit `.env`, API keys, or private key material.
- Public endpoints work without creds; portfolio features/integration tests require `KALSHI_KEY_ID` plus a key (`KALSHI_PRIVATE_KEY_PATH` or `KALSHI_PRIVATE_KEY_B64`).

## Database Safety (Do Not Destroy State)

- **Never delete** `data/kalshi.db` to “fix” issues (e.g. `database disk image is malformed`).
- Diagnose first (`sqlite3 data/kalshi.db "PRAGMA integrity_check;"`) and recover when needed (`sqlite3 data/kalshi.db ".recover" | sqlite3 data/recovered.db`).
- `data/exa_cache/` is disposable cache; the SQLite DB is not.
