# Repository Guidelines

## Project Structure & Module Organization

- `src/kalshi_research/`: main package (src-layout)
  - `api/`: Kalshi HTTP clients + Pydantic models
  - `data/`: async SQLite/SQLAlchemy persistence, repositories, exports
  - `analysis/`, `research/`, `alerts/`, `portfolio/`: domain modules
  - `cli.py`: Typer CLI entrypoint (`kalshi`)
- `tests/`: `unit/` mirrors `src/`; `integration/` hits real API (needs creds)
- `docs/`: usage guides plus specs/bug tracker (`docs/_specs/`, `docs/_bugs/`)
- `alembic/`, `alembic.ini`: database migrations
- `data/`: local runtime artifacts (e.g., `data/kalshi.db`, exports)

## Build, Test, and Development Commands

Preferred dependency manager is `uv` (see `uv.lock`):

```bash
uv sync --all-extras              # install dev + research extras
uv run kalshi --help              # run CLI without global install
uv run ruff check .               # lint (CI)
uv run ruff format --check .      # format check (CI); drop --check to format
uv run mypy src/                  # strict type checking (CI)
uv run pytest -m "not integration and not slow"  # fast local suite (CI-like)
uv run pre-commit install         # enable hooks (ruff/format/mypy, etc.)
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

- Use atomic commits; follow the repo’s common pattern: `[BUG-###] Fix: ...`, `[SPEC-###] Implement: ...`, `[FEATURE] Add: ...`, `[QUALITY-###] Fix: ...`.
- PRs should include: what changed, how it was tested (commands run), and any user-facing doc updates (often `docs/USAGE.md` / `docs/QUICKSTART.md`).
- Before review, ensure local checks match CI: `ruff`, `mypy`, and `pytest` are green.

## Security & Configuration Tips

- Copy `.env.example` → `.env`; never commit `.env`, API keys, or private key material.
- Public endpoints work without creds; portfolio features/integration tests require `KALSHI_KEY_ID` plus a key (`KALSHI_PRIVATE_KEY_PATH` or `KALSHI_PRIVATE_KEY_B64`).
