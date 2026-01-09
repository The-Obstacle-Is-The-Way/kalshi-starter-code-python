# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

### If Pre-commit Fails

1. Review the error output
2. Fix the issues (many auto-fix with `--fix`)
3. Re-run `uv run pre-commit run --all-files`
4. Only commit after ALL checks pass

## Build & Development Commands

```bash
# Install dependencies (use uv, not pip)
uv sync                      # Production deps only
uv sync --all-extras         # All deps including dev and research
uv run pre-commit install    # CRITICAL: Install commit hooks

# Quality gates (all must pass before commits)
uv run ruff check .          # Lint
uv run ruff format .         # Format (or --check to verify)
uv run mypy src/             # Type checking (strict mode)
uv run pytest                # All tests

# Run single test file or specific test
uv run pytest tests/unit/api/test_client.py -v
uv run pytest tests/unit/api/test_client.py::test_name -v

# Test with coverage
uv run pytest --cov=kalshi_research --cov-report=term-missing

# Database migrations
uv run alembic upgrade head              # Run migrations
uv run alembic revision --autogenerate -m "message"  # Create migration

# CLI usage
uv run kalshi --help
uv run kalshi data init
uv run kalshi data sync-markets
uv run kalshi scan opportunities --filter close-race
```

## Code Quality Standards

### FORBIDDEN Patterns

- **NO `# type: ignore`** - Fix the type error properly
- **NO untyped `Any`** - Use specific types (exception: JSON dicts as `dict[str, Any]`)
- **NO `--no-verify` commits** - Always run pre-commit hooks
- **NO manual git commits** - Use `uv run pre-commit run` first

## Architecture

### Layer Structure

```
src/kalshi_research/
├── api/           # Kalshi API clients (HTTP boundary)
│   ├── client.py  # KalshiPublicClient (no auth), KalshiClient (auth)
│   ├── models/    # Pydantic v2 models (frozen, immutable)
│   └── auth.py    # RSA signing for authenticated endpoints
├── data/          # Persistence layer
│   ├── database.py    # DatabaseManager (async SQLite via aiosqlite)
│   ├── models.py      # SQLAlchemy ORM models
│   ├── repositories/  # Repository pattern (markets, events, prices)
│   ├── fetcher.py     # DataFetcher (coordinates API → DB)
│   └── export.py      # DuckDB/Parquet export
├── analysis/      # Research analytics
│   ├── calibration.py   # Brier scores, calibration curves
│   ├── edge.py          # Edge detection (thesis, spread, volume)
│   ├── scanner.py       # Market scanner (close races, movers)
│   ├── correlation.py   # Event correlation, arbitrage detection
│   └── metrics.py       # Probability tracking
├── alerts/        # Alert system
│   ├── conditions.py    # Alert conditions (price, volume, spread)
│   ├── monitor.py       # AlertMonitor (async polling)
│   └── notifiers.py     # Console, file, webhook notifiers
├── research/      # Research tools
│   ├── thesis.py        # Thesis tracking
│   ├── backtest.py      # ThesisBacktester
│   └── notebook_utils.py # Jupyter helpers
├── portfolio/     # Portfolio tracking (no order placement)
│   ├── models.py        # Position, Trade models
│   ├── pnl.py           # P&L calculator
│   └── syncer.py        # Sync from Kalshi API
└── cli/           # Typer CLI package (kalshi command)
```

### Key Patterns

**API Clients**: Use async context managers. `KalshiPublicClient` for research (no auth), `KalshiClient` for portfolio sync (requires API key).

**Repository Pattern**: Prefer repositories in `data/repositories/` for shared persistence logic. For
small, one-off queries in CLI commands, direct `select()` usage is acceptable when it avoids unnecessary abstraction,
but don’t duplicate repository behavior in multiple places.

**Pydantic Models**: API models in `api/models/` are frozen (`model_config = ConfigDict(frozen=True)`). Don't mutate them.

**SQLAlchemy Models**: ORM models in `data/models.py` use SQLAlchemy 2.0 declarative style with `Mapped[]` type hints.

**Testing Philosophy**: Only mock at system boundaries (HTTP via `respx`, filesystem via `tmp_path`). Use real Pydantic models, real in-memory SQLite for repositories.

## CLI Structure

```
kalshi
├── data        # init, sync-markets, sync-settlements, snapshot, collect, export, stats
├── market      # get, list, orderbook
├── scan        # opportunities, arbitrage, movers
├── alerts      # list, add, remove, monitor
├── analysis    # calibration, correlation, metrics
├── research    # thesis (create/list/show/resolve), backtest
└── portfolio   # sync, positions, pnl, balance, history, link, suggest-links
```

## Test Organization

Tests mirror source structure: `tests/unit/api/`, `tests/unit/data/`, etc. Integration tests requiring API keys go in `tests/integration/`.

Fixtures in `conftest.py` provide `make_market`, `make_orderbook`, `make_trade` factories that return dicts matching API response structure.
