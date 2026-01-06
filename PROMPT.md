# Kalshi Research Platform - Ralph Wiggum Implementation Prompt

You are building a Kalshi prediction market research platform. Follow the specs in `docs/_specs/` exactly.

## Project Goal

Transform the bare-bones Kalshi starter code into a production-quality research platform with:
- Modern Python tooling (uv, ruff, mypy, pytest)
- Complete API client for all Kalshi endpoints
- SQLite data storage with async support
- Research & analysis tools (calibration, edge detection)
- Full test coverage (>80%)

## Implementation Order

Complete these phases IN ORDER. Do not skip ahead.

### Phase 1: Modern Python Foundation (SPEC-001)

1. Create `src/kalshi_research/` directory structure
2. Move `clients.py` to `src/kalshi_research/clients.py`
3. Create `src/kalshi_research/__init__.py` with version
4. Create `src/kalshi_research/py.typed` marker
5. Write `pyproject.toml` exactly as specified in SPEC-001
6. Create `.python-version` with `3.11`
7. Create `.env.example` template
8. Update `.gitignore` as specified
9. Create `.pre-commit-config.yaml` as specified
10. Create `.github/workflows/ci.yml` as specified
11. Run `uv sync` to install dependencies
12. Run `uv run ruff check . --fix` to fix lint errors
13. Run `uv run ruff format .` to format code
14. Add type hints to `clients.py` for mypy compliance
15. Run `uv run mypy src/` and fix all errors
16. Create `tests/conftest.py` with shared fixtures
17. Create `tests/unit/test_clients.py` with basic tests
18. Run `uv run pytest tests/unit -v` - all tests must pass

**Phase 1 Checkpoint:** `uv run ruff check . && uv run mypy src/ && uv run pytest tests/unit` all pass

### Phase 2: API Client (SPEC-002)

1. Create `src/kalshi_research/api/` directory
2. Create `src/kalshi_research/api/__init__.py`
3. Create `src/kalshi_research/api/exceptions.py` with all exception classes
4. Create `src/kalshi_research/api/models/` directory
5. Create `src/kalshi_research/api/models/__init__.py`
6. Create `src/kalshi_research/api/models/market.py` with Market, Orderbook, Trade, Candlestick
7. Create `src/kalshi_research/api/models/event.py` with Event model
8. Create `src/kalshi_research/api/auth.py` with KalshiAuth (port from clients.py)
9. Create `src/kalshi_research/api/client.py` with KalshiPublicClient and KalshiClient
10. Update `src/kalshi_research/__init__.py` to export client classes
11. Create `tests/unit/test_api_client.py` with mocked tests using respx
12. Create `tests/unit/test_api_models.py` with model validation tests
13. Run `uv run pytest tests/unit -v` - all tests must pass
14. Run `uv run mypy src/` - no errors

**Phase 2 Checkpoint:** Can import and instantiate `KalshiPublicClient`, all tests pass

### Phase 3: Data Layer (SPEC-003)

1. Create `src/kalshi_research/data/` directory
2. Create `src/kalshi_research/data/__init__.py`
3. Create `src/kalshi_research/data/database.py` with async session management
4. Create `src/kalshi_research/data/models.py` with all SQLAlchemy ORM models
5. Create `src/kalshi_research/data/repositories/` directory
6. Create `src/kalshi_research/data/repositories/__init__.py`
7. Create `src/kalshi_research/data/repositories/markets.py`
8. Create `src/kalshi_research/data/repositories/prices.py`
9. Create `src/kalshi_research/data/fetcher.py` with DataFetcher class
10. Create `src/kalshi_research/data/scheduler.py` with drift-corrected scheduler
11. Create `src/kalshi_research/data/export.py` with Parquet export
12. Create `data/.gitkeep` to ensure directory exists
13. Set up Alembic: `uv run alembic init alembic`
14. Configure `alembic.ini` and `alembic/env.py` for async SQLAlchemy
15. Create initial migration: `uv run alembic revision --autogenerate -m "initial"`
16. Create `tests/unit/test_data_models.py` with ORM tests
17. Create `tests/unit/test_repositories.py` with repository tests
18. Run `uv run pytest tests/unit -v` - all tests pass
19. Run `uv run mypy src/` - no errors

**Phase 3 Checkpoint:** Can create database, run migrations, save/load data

### Phase 4: CLI (Required for all specs)

1. Create `src/kalshi_research/cli.py` with Typer app
2. Add `data init` command (create database)
3. Add `data sync-markets` command
4. Add `data snapshot` command
5. Add `data collect --interval` command
6. Add `data export-parquet` command
7. Add `scan` command with filters
8. Test CLI: `uv run kalshi --help`
9. Create `tests/unit/test_cli.py` with CLI tests

**Phase 4 Checkpoint:** `uv run kalshi --help` shows all commands

### Phase 5: Research & Analysis (SPEC-004)

1. Create `src/kalshi_research/analysis/` directory
2. Create `src/kalshi_research/analysis/__init__.py`
3. Create `src/kalshi_research/analysis/calibration.py` with CalibrationAnalyzer
4. Create `src/kalshi_research/analysis/edge.py` with EdgeDetector
5. Create `src/kalshi_research/analysis/scanner.py` with MarketScanner
6. Create `src/kalshi_research/analysis/metrics.py` with market metrics
7. Create `src/kalshi_research/research/` directory
8. Create `src/kalshi_research/research/__init__.py`
9. Create `src/kalshi_research/research/thesis.py` with Thesis and ThesisTracker
10. Create `tests/unit/test_calibration.py` with calibration tests
11. Create `tests/unit/test_edge.py` with edge detection tests
12. Create `notebooks/` directory
13. Create `notebooks/01_exploration.ipynb` template
14. Run `uv run pytest tests/unit -v` - all tests pass
15. Run `uv run mypy src/` - no errors

**Phase 5 Checkpoint:** Analysis tools work, all tests pass

### Phase 6: Final Verification

1. Run full test suite: `uv run pytest tests/ -v --cov=kalshi_research --cov-report=term-missing`
2. Verify coverage is >80%
3. Run `uv run ruff check .` - no errors
4. Run `uv run ruff format --check .` - no errors
5. Run `uv run mypy src/` - no errors
6. Test CLI commands work: `uv run kalshi --help`
7. Verify imports work:
   ```python
   from kalshi_research.api import KalshiPublicClient
   from kalshi_research.analysis import CalibrationAnalyzer, EdgeDetector
   from kalshi_research.data import DataFetcher
   ```

## Success Criteria

ALL of the following must be true:
- [ ] `uv sync` installs without errors
- [ ] `uv run ruff check .` passes
- [ ] `uv run ruff format --check .` passes
- [ ] `uv run mypy src/` passes with no errors
- [ ] `uv run pytest tests/unit -v` all tests pass
- [ ] Test coverage >80%
- [ ] `uv run kalshi --help` shows all commands
- [ ] No import errors when importing main modules

## Rules

1. Read the specs in `docs/_specs/` before implementing each phase
2. Run tests after EVERY file creation to catch errors early
3. Fix all ruff/mypy errors before moving to next phase
4. Use EXACT code from specs - do not improvise
5. If a test fails, debug and fix before continuing
6. Commit after each phase: `git add -A && git commit -m "Phase N: description"`

## Completion

When ALL success criteria are met, output:

<promise>KALSHI RESEARCH PLATFORM COMPLETE</promise>
