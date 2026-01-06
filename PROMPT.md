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
3. Update `main.py` imports to use new path: `from kalshi_research.clients import ...`
4. Create `src/kalshi_research/__init__.py` with version
5. Create `src/kalshi_research/py.typed` marker
6. Write `pyproject.toml` exactly as specified in SPEC-001
7. Create `.python-version` with `3.11`
8. Create `.env.example` template
9. Update `.gitignore` as specified
10. Create `.pre-commit-config.yaml` as specified
11. Create `.github/workflows/ci.yml` as specified
12. Run `uv sync` to install dependencies
13. Run `uv run ruff check . --fix` to fix lint errors
14. Run `uv run ruff format .` to format code
15. Add type hints to `clients.py` for mypy compliance
16. Run `uv run mypy src/` and fix all errors
17. Create `tests/conftest.py` with shared fixtures
18. Create `tests/unit/test_clients.py` with basic tests
19. Run `uv run pytest tests/unit -v` - all tests must pass

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
14. Configure `alembic.ini` (async url) and `alembic/env.py` (import `Base`, set `target_metadata`)
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
4. Use code from specs as the starting point. Minor corrections are allowed when:
   - Code has syntax errors or typos
   - mypy strict mode requires additional type annotations
   - Live API behavior differs from spec (test against real API when possible)
5. If a test fails, debug and fix before continuing
6. Commit after each phase: `git add -A && git commit -m "Phase N: description"`

## Test-Driven Development (TDD) Workflow

**For EVERY new module, follow RED-GREEN-REFACTOR:**

1. **RED:** Write failing test FIRST
   ```bash
   # Create test file before implementation
   # Example: tests/unit/test_calibration.py BEFORE src/kalshi_research/analysis/calibration.py
   uv run pytest tests/unit/test_<module>.py -v  # Should FAIL (no implementation)
   ```

2. **GREEN:** Write minimal code to pass
   ```bash
   # Create implementation
   uv run pytest tests/unit/test_<module>.py -v  # Should PASS
   ```

3. **REFACTOR:** Clean up while tests stay green
   ```bash
   uv run ruff check . --fix && uv run ruff format .
   uv run mypy src/
   uv run pytest tests/unit -v  # Still passes
   ```

## Testing Philosophy: Behavior Over Mocks

**CRITICAL: Avoid over-mocking. Tests that mock everything test nothing.**

### The Testing Pyramid

```
        /\
       /  \     Integration Tests (few) - Real DB, real API calls
      /----\
     /      \   Behavioral Tests (many) - Real objects, real logic
    /--------\
   /          \ Unit Tests (pure functions) - No mocks needed
  --------------
```

### When to Mock vs When NOT to Mock

**ONLY mock at system boundaries:**
- HTTP calls to external APIs (use `respx` ONLY for KalshiPublicClient)
- File system operations (use `tmp_path` fixture instead when possible)
- Current time (use dependency injection, not `unittest.mock.patch`)

**NEVER mock:**
- Your own domain objects (Market, Trade, Orderbook, etc.)
- Pydantic models - use REAL instances
- Pure functions (calibration math, edge detection logic)
- Repository methods when testing services - use real in-memory SQLite
- Internal class collaborations

### Test Categories

**1. Pure Function Tests (NO MOCKS):**
```python
# GOOD: Test actual behavior with real data
def test_brier_score_perfect_forecast():
    analyzer = CalibrationAnalyzer()
    forecasts = np.array([1.0, 0.0, 1.0])
    outcomes = np.array([1, 0, 1])

    score = analyzer.compute_brier_score(forecasts, outcomes)

    assert score == 0.0  # Perfect score

def test_brier_score_worst_forecast():
    analyzer = CalibrationAnalyzer()
    forecasts = np.array([0.0, 1.0, 0.0])
    outcomes = np.array([1, 0, 1])

    score = analyzer.compute_brier_score(forecasts, outcomes)

    assert score == 1.0  # Worst possible
```

**2. Domain Object Tests (REAL OBJECTS):**
```python
# GOOD: Create real Pydantic models, test real behavior
def test_orderbook_spread_calculation():
    orderbook = Orderbook(
        yes=[(45, 100), (44, 200)],
        no=[(53, 150), (54, 250)],
    )

    assert orderbook.best_yes_bid == 45
    assert orderbook.best_no_bid == 54
    assert orderbook.spread == 1  # 100 - 45 - 54

# BAD: Mocking the object you're testing
def test_orderbook_spread_BAD():
    orderbook = Mock()
    orderbook.spread = 1  # This tests NOTHING
    assert orderbook.spread == 1
```

**3. Repository Tests (REAL IN-MEMORY DATABASE):**
```python
# GOOD: Use real SQLite in-memory database
@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session

async def test_market_repository_save_and_load(db_session):
    repo = MarketRepository(db_session)
    market = Market(ticker="TEST-123", ...)  # Real object

    await repo.save(market)
    loaded = await repo.get_by_ticker("TEST-123")

    assert loaded.ticker == market.ticker
```

**4. HTTP Client Tests (MOCK ONLY THE BOUNDARY):**
```python
# GOOD: Mock only the HTTP layer, test everything else real
@respx.mock
async def test_get_market_parses_response():
    respx.get(...).mock(return_value=Response(200, json={...}))

    async with KalshiPublicClient() as client:
        market = await client.get_market("TICKER")

    # Assert on REAL parsed Market object
    assert isinstance(market, Market)
    assert market.ticker == "TICKER"
```

### Dependency Injection for Testability

**Instead of mocking time:**
```python
# BAD: Patching datetime
@patch('kalshi_research.analysis.edge.datetime')
def test_edge_detection(mock_dt):
    mock_dt.now.return_value = datetime(2024, 1, 1)
    ...

# GOOD: Inject time as dependency
class EdgeDetector:
    def __init__(self, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self._clock = clock

def test_edge_detection():
    fixed_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    detector = EdgeDetector(clock=lambda: fixed_time)
    ...
```

**Instead of mocking the client:**
```python
# BAD: Mocking the entire client
def test_data_fetcher():
    mock_client = Mock()
    mock_client.get_markets.return_value = [Mock(), Mock()]
    fetcher = DataFetcher(mock_client)
    ...

# GOOD: Use a real client with mocked HTTP (or a fake/stub)
@respx.mock
async def test_data_fetcher():
    respx.get(...).mock(return_value=Response(200, json={"markets": [...]}))

    async with KalshiPublicClient() as client:
        fetcher = DataFetcher(client)
        markets = await fetcher.fetch_all_markets()

    assert len(markets) > 0
    assert all(isinstance(m, Market) for m in markets)
```

### Test Requirements

- Every public function/method must have at least one **behavioral** test
- Use `pytest.mark.parametrize` for multiple test cases
- Use `respx` ONLY for HTTP boundary (KalshiPublicClient)
- Use real in-memory SQLite for repository tests
- Use `hypothesis` for property-based testing on pure functions
- Test edge cases with REAL objects: empty lists, None values, boundaries
- Test error paths: real exceptions, real validation errors

## Clean Code Principles (Uncle Bob / Gang of Four)

**SOLID Principles - Enforce These:**
- **S**ingle Responsibility: Each class/module does ONE thing
- **O**pen/Closed: Extend via composition, not modification
- **L**iskov Substitution: Subtypes must be substitutable
- **I**nterface Segregation: Small, focused interfaces
- **D**ependency Inversion: Depend on abstractions, not concretions

**DRY (Don't Repeat Yourself):**
- Extract common code into shared utilities
- Use base classes/mixins for shared behavior
- Constants in `src/kalshi_research/constants.py` (create if needed)

**Gang of Four Patterns to Use:**
- **Repository Pattern**: Data access (already in SPEC-003)
- **Factory Pattern**: Object creation (use `polyfactory` for tests)
- **Strategy Pattern**: Interchangeable algorithms (edge detection)
- **Observer Pattern**: Event handling (scheduler callbacks)
- **Decorator Pattern**: Cross-cutting concerns (retries via `tenacity`)

**Code Smells to AVOID:**
- God classes (>300 lines)
- Long methods (>30 lines)
- Deep nesting (>3 levels)
- Magic numbers (use constants)
- Commented-out code (delete it)
- Duplicate code (extract to function)

## Quality Gates (Must Pass Before Phase Completion)

```bash
# Run ALL checks before moving to next phase:
uv run ruff check .           # No lint errors
uv run ruff format --check .  # Properly formatted
uv run mypy src/              # No type errors
uv run pytest tests/unit -v --cov=kalshi_research --cov-fail-under=80  # >80% coverage
```

If ANY check fails, fix it before proceeding. No exceptions.

## Important API Notes

**Read these before implementing SPEC-002:**

- **Market status filter vs response:** Filter params use `unopened/open/closed/settled`, but API responses return `active/closed/determined/finalized`
- **Candlesticks:** Use batch endpoint `/markets/candlesticks` (not `/markets/{ticker}/candlesticks`)
- **Orderbook:** Returns `{"yes": [[price,qty],...], "no": [...]}` not objects with `yes_bids/yes_asks`
- **Trade fields:** Use `created_time` + `yes_price/no_price`, not `timestamp` + `price`
- **Auth signing:** Sign the FULL path including `/trade-api/v2` prefix, not just the relative endpoint

## Completion

When ALL success criteria are met, output:

<promise>KALSHI RESEARCH PLATFORM COMPLETE</promise>
