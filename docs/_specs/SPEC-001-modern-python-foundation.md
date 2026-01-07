# SPEC-001: Modern Python Project Foundation

**Status:** ✅ Implemented
**Priority:** P0 (Blocker for all other specs)
**Estimated Complexity:** Medium
**Dependencies:** None

---

## 1. Overview

Transform the bare-bones Kalshi starter code into a modern, production-quality Python project with proper tooling, testing infrastructure, and CI/CD pipeline.

### 1.1 Goals
- Modern Python packaging with `pyproject.toml` and `uv`
- Comprehensive testing framework (pytest + plugins)
- Code quality tooling (ruff, mypy)
- GitHub Actions CI/CD pipeline
- Pre-commit hooks for developer experience

### 1.2 Non-Goals
- Changing any existing functionality in `clients.py`
- Adding new Kalshi API endpoints (that's SPEC-002)
- Setting up deployment infrastructure

---

## Implementation References

- `pyproject.toml` (ruff/mypy/pytest config, markers, coverage)
- `uv.lock` (dependency lockfile)
- `tests/` (unit/integration/e2e suites)

---

## 2. Technical Specification

### 2.1 Project Structure

```
kalshi-research/
├── pyproject.toml           # Single source of truth for project config
├── uv.lock                   # Lockfile for reproducible builds
├── .python-version           # Pin Python version (3.11+)
├── .env.example              # Template for environment variables
├── .gitignore                # Updated for Python/uv
├── .pre-commit-config.yaml   # Pre-commit hooks
├── .github/
│   └── workflows/
│       ├── ci.yml            # Main CI pipeline
│       └── release.yml       # Release automation (future)
├── src/
│   └── kalshi_research/      # Main package (src layout)
│       ├── __init__.py
│       ├── clients.py        # Existing client code (moved)
│       └── py.typed          # PEP 561 marker
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Shared fixtures (load .env here)
│   ├── unit/
│   │   ├── __init__.py
│   │   └── test_clients.py
│   └── integration/
│       ├── __init__.py
│       └── test_api_live.py  # Requires API keys, skipped in CI
├── docs/
│   └── _specs/               # This directory
└── README.md                 # Updated documentation
```

### 2.2 pyproject.toml Configuration

```toml
[project]
name = "kalshi-research"
version = "0.1.0"
description = "Research platform for Kalshi prediction market analysis"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
authors = [{ name = "Your Name", email = "you@example.com" }]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
]
dependencies = [
    "requests>=2.32.0",
    "cryptography>=46.0.0",
    "websockets>=15.0.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.12.0",
    "httpx>=0.28.0",               # Modern async HTTP client
    "tenacity>=9.1.0",             # Retry logic with backoff
    "structlog>=25.0.0",           # Structured logging
    "sqlalchemy[asyncio]>=2.0.40", # Database ORM with async support
    "aiosqlite>=0.20.0",           # Async SQLite driver (required for SQLAlchemy async)
    "alembic>=1.14.0",             # Database migrations
    "duckdb>=1.4.0",               # Analytical OLAP database (updated)
    "typer>=0.15.0",               # CLI framework
    "rich>=13.9.0",                # Beautiful terminal output
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-cov>=6.0.0",
    "pytest-sugar>=1.0.0",
    "pytest-xdist>=3.6.0",     # Parallel test execution
    "pytest-asyncio>=0.25.0",  # Async test support
    "pytest-mock>=3.14.0",
    "pytest-timeout>=2.3.0",   # Test timeout (used in CI)
    "ruff>=0.9.0",
    "mypy>=1.14.0",
    "pre-commit>=4.0.0",
    "respx>=0.22.0",           # Mock httpx requests
    "polyfactory>=3.0.0",      # Test data factories
    "hypothesis>=6.122.0",     # Property-based testing
    "types-requests>=2.32.0",  # Type stubs for requests (required for mypy strict)
]
research = [
    "pandas>=2.2.0",
    "numpy>=2.2.0",
    "scipy>=1.15.0",
    "matplotlib>=3.10.0",
    "seaborn>=0.13.0",
    "jupyter>=1.1.0",
    "ipykernel>=6.29.0",
]
all = ["kalshi-research[dev,research]"]

[project.scripts]
kalshi = "kalshi_research.cli:app"  # Typer CLI entry point

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/kalshi_research"]

[tool.ruff]
target-version = "py311"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
    "TCH",    # flake8-type-checking
    "PTH",    # flake8-use-pathlib
    "ERA",    # eradicate (commented code)
    "PL",     # pylint
    "RUF",    # ruff-specific
]
ignore = [
    "PLR0913",  # Too many arguments (APIs need them)
    "PLR2004",  # Magic values (acceptable in tests)
]

[tool.ruff.lint.isort]
known-first-party = ["kalshi_research"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["websockets.*", "respx.*", "scipy.*", "matplotlib.*", "pandas.*", "duckdb.*", "aiosqlite.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
    "-ra",
]
markers = [
    "unit: Unit tests (no external dependencies)",
    "integration: Integration tests (requires API keys)",
    "slow: Slow tests (>5s)",
]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"

[tool.coverage.run]
source = ["src/kalshi_research"]
branch = true
omit = ["*/tests/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

### 2.3 GitHub Actions CI Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    name: Lint & Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - name: Set up Python
        run: uv python install 3.11
      - name: Install dependencies
        # Include research extra for numpy type checking in analysis modules
        run: uv sync --all-extras
      - name: Run ruff check
        run: uv run ruff check .
      - name: Run ruff format check
        run: uv run ruff format --check .
      - name: Run mypy
        run: uv run mypy src/

  test:
    name: Test (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11", "3.12", "3.13", "3.14"]
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}
      - name: Install dependencies
        run: uv sync --dev
      - name: Run tests
        run: |
          uv run pytest tests/unit \
            --cov=kalshi_research \
            --cov-report=xml \
            --cov-report=term-missing \
            -m "not integration and not slow"
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: false

  integration:
    name: Integration Tests
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
      - name: Set up Python
        run: uv python install 3.11
      - name: Install dependencies
        run: uv sync --dev
      - name: Run integration tests
        env:
          DEMO_KEYID: ${{ secrets.DEMO_KEYID }}
          # Base64 encoded private key to avoid newline issues
          DEMO_KEYFILE_CONTENT_B64: ${{ secrets.DEMO_KEYFILE_CONTENT_B64 }}
        run: |
          echo "$DEMO_KEYFILE_CONTENT_B64" | base64 -d > /tmp/demo_key.pem
          export DEMO_KEYFILE=/tmp/demo_key.pem
          uv run pytest tests/integration -m integration --timeout=60
```

### 2.4 Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.2
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.1
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.12.0
          - types-requests
        args: [--config-file=pyproject.toml]
        pass_filenames: false
        entry: mypy src/

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
        args: [--maxkb=1000]
      - id: detect-private-key
      - id: check-merge-conflict
```

### 2.5 Updated .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/

# uv
.uv/

# Testing
.coverage
.pytest_cache/
htmlcov/
.tox/
.nox/
coverage.xml
*.cover

# Type checking
.mypy_cache/
.dmypy.json
dmpy.json

# IDEs
.idea/
.vscode/
*.swp
*.swo

# Jupyter
.ipynb_checkpoints/

# Environment
.env
.env.local
*.pem

# Data (will be tracked selectively)
data/*.db
data/*.json
data/exports/
!data/.gitkeep

# OS
.DS_Store
Thumbs.db
```

---

## 3. Implementation Tasks

### 3.1 Phase 1: Project Structure
- [ ] Create `src/kalshi_research/` directory structure
- [ ] Move `clients.py` to `src/kalshi_research/clients.py`
- [ ] Create `__init__.py` with version and exports
- [ ] Create `py.typed` marker file
- [ ] Write `pyproject.toml` with all configurations
- [ ] Update `.gitignore`
- [ ] Update `main.py` imports to use new package path:
  ```python
  # main.py - updated imports
  from kalshi_research.clients import KalshiHttpClient, KalshiWebSocketClient, Environment
  ```
  Alternatively, keep a root `clients.py` shim that re-exports:
  ```python
  # clients.py (root shim for backwards compatibility)
  from kalshi_research.clients import *  # noqa: F401, F403
  ```

### 3.2 Phase 2: Tooling Setup
- [ ] Initialize uv and generate lockfile
- [ ] Configure ruff and fix any existing lint errors
- [ ] Add type hints to existing code for mypy compliance
- [ ] Set up pre-commit hooks
- [ ] Verify all tools work locally

### 3.3 Phase 3: Testing Infrastructure
- [ ] Create `tests/` directory structure
- [ ] Write `conftest.py` with shared fixtures (auto-load dotenv)
- [ ] Write initial unit tests for `clients.py`
- [ ] Set up pytest markers (unit, integration, slow)
- [ ] Configure coverage reporting

**Required conftest.py fixtures (REAL OBJECTS, minimal mocking):**

```python
# tests/conftest.py
"""
Shared test fixtures.

PHILOSOPHY: Use REAL objects wherever possible. Only mock at system boundaries.
- Real Pydantic models (not dicts pretending to be models)
- Real SQLite in-memory for repository tests
- respx ONLY for HTTP boundary
"""
import os
from datetime import datetime, timezone

import pytest
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Load environment variables from .env for integration tests
load_dotenv()


# ============================================================================
# Database Fixtures (REAL in-memory SQLite, not mocks)
# ============================================================================
@pytest.fixture
async def db_engine():
    """Create real async SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create real database session with schema."""
    from kalshi_research.data.models import Base

    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        yield session


# ============================================================================
# API Credentials (for integration tests only)
# ============================================================================
@pytest.fixture(scope="session")
def api_credentials() -> dict[str, str | None]:
    """API credentials from environment (may be None for public-only tests)."""
    return {
        "key_id": os.getenv("KALSHI_KEY_ID"),
        "private_key_path": os.getenv("KALSHI_PRIVATE_KEY_PATH"),
        "environment": os.getenv("KALSHI_ENVIRONMENT", "demo"),
    }


# ============================================================================
# Domain Object Builders (create REAL objects, not dicts)
# ============================================================================
# NOTE: These will be replaced with actual model imports in Phase 2.
# For now, they return dicts that match API response structure.
# After Phase 2, update to return REAL Pydantic models.

@pytest.fixture
def make_market():
    """Factory to create REAL Market objects with sensible defaults."""
    def _make(
        ticker: str = "TEST-MARKET",
        status: str = "active",
        yes_bid: int = 45,
        yes_ask: int = 47,
        **overrides,
    ):
        # After Phase 2, this becomes:
        # from kalshi_research.api.models.market import Market
        # return Market(ticker=ticker, status=status, ...)
        base = {
            "ticker": ticker,
            "event_ticker": "TEST-EVENT",
            "series_ticker": "TEST",
            "title": f"Test Market {ticker}",
            "subtitle": "",
            "status": status,
            "result": "",
            "yes_bid": yes_bid,
            "yes_ask": yes_ask,
            "no_bid": 100 - yes_ask,
            "no_ask": 100 - yes_bid,
            "last_price": (yes_bid + yes_ask) // 2,
            "volume": 10000,
            "volume_24h": 1000,
            "open_interest": 5000,
            "liquidity": 10000,
            "open_time": "2024-01-01T00:00:00Z",
            "close_time": "2025-12-31T00:00:00Z",
            "expiration_time": "2026-01-01T00:00:00Z",
        }
        base.update(overrides)
        return base
    return _make


@pytest.fixture
def make_orderbook():
    """Factory to create REAL Orderbook objects."""
    def _make(
        yes_bids: list[tuple[int, int]] | None = None,
        no_bids: list[tuple[int, int]] | None = None,
    ):
        # After Phase 2: return Orderbook(yes=yes_bids, no=no_bids)
        return {
            "yes": yes_bids or [(45, 100), (44, 200), (43, 500)],
            "no": no_bids or [(53, 150), (54, 250), (55, 400)],
        }
    return _make


@pytest.fixture
def make_trade():
    """Factory to create REAL Trade objects."""
    def _make(
        ticker: str = "TEST-MARKET",
        yes_price: int = 46,
        count: int = 10,
        taker_side: str = "yes",
        **overrides,
    ):
        base = {
            "trade_id": f"trade-{ticker}-{yes_price}",
            "ticker": ticker,
            "created_time": datetime.now(timezone.utc).isoformat(),
            "yes_price": yes_price,
            "no_price": 100 - yes_price,
            "count": count,
            "taker_side": taker_side,
        }
        base.update(overrides)
        return base
    return _make


# ============================================================================
# Time Injection (for testability without mocking)
# ============================================================================
@pytest.fixture
def fixed_clock():
    """Returns a clock function that always returns the same time."""
    fixed_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    def clock() -> datetime:
        return fixed_time

    clock.time = fixed_time  # Access the fixed time directly
    return clock
```

**Test file template (behavior-focused, minimal mocks):**

```python
# tests/unit/test_example.py
"""
Example test module demonstrating BEHAVIOR-FOCUSED testing.

Key principles:
1. Test BEHAVIOR, not implementation details
2. Use REAL objects (Pydantic models, domain objects)
3. Mock ONLY at system boundaries (HTTP, filesystem)
4. Use factories to create test data, not raw dicts
"""
import pytest
from hypothesis import given, strategies as st


class TestDomainBehavior:
    """Tests that verify actual business logic with REAL objects."""

    def test_orderbook_spread_with_real_object(self, make_orderbook) -> None:
        """
        GOOD: Test real computed property behavior.
        After Phase 2, this uses a real Orderbook model.
        """
        orderbook_data = make_orderbook(
            yes_bids=[(45, 100), (44, 200)],
            no_bids=[(53, 150), (54, 250)],
        )

        # After Phase 2:
        # orderbook = Orderbook(**orderbook_data)
        # assert orderbook.best_yes_bid == 45
        # assert orderbook.spread == 1  # 100 - 45 - 54

        # For now, verify data structure
        assert orderbook_data["yes"][0][0] == 45

    def test_market_factory_creates_consistent_data(self, make_market) -> None:
        """Test that factory creates valid, internally consistent data."""
        market = make_market(yes_bid=40, yes_ask=45)

        # Verify internal consistency
        assert market["no_bid"] == 55  # 100 - yes_ask
        assert market["no_ask"] == 60  # 100 - yes_bid
        assert market["last_price"] == 42  # midpoint

    @pytest.mark.parametrize(
        "yes_bid,yes_ask,expected_spread",
        [
            (45, 47, 2),
            (50, 50, 0),
            (10, 90, 80),
        ],
    )
    def test_spread_calculation(
        self, yes_bid: int, yes_ask: int, expected_spread: int
    ) -> None:
        """Test spread calculation with various inputs."""
        spread = yes_ask - yes_bid
        assert spread == expected_spread


class TestPureFunctions:
    """Tests for pure functions - NO MOCKS NEEDED."""

    @given(st.integers(min_value=1, max_value=99))
    def test_price_to_probability_always_in_range(self, price: int) -> None:
        """Property: any valid price converts to probability in [0, 1]."""
        probability = price / 100
        assert 0 < probability < 1

    @given(
        st.lists(st.floats(min_value=0, max_value=1), min_size=1, max_size=100),
        st.lists(st.integers(min_value=0, max_value=1), min_size=1, max_size=100),
    )
    def test_brier_score_properties(
        self, forecasts: list[float], outcomes: list[int]
    ) -> None:
        """Property: Brier score is always between 0 and 1."""
        if len(forecasts) != len(outcomes):
            return  # Skip mismatched lengths

        # Brier score formula: mean((forecast - outcome)^2)
        brier = sum((f - o) ** 2 for f, o in zip(forecasts, outcomes)) / len(forecasts)
        assert 0 <= brier <= 1


class TestTimeInjection:
    """Demonstrate testability via dependency injection, not mocking."""

    def test_with_fixed_time(self, fixed_clock) -> None:
        """Use injected clock instead of mocking datetime."""
        # GOOD: Pass clock as dependency
        current_time = fixed_clock()

        assert current_time.year == 2024
        assert current_time.month == 6

        # Can also access fixed time directly
        assert fixed_clock.time.day == 15
```

### 3.4 Phase 4: CI/CD
- [ ] Create `.github/workflows/ci.yml`
- [ ] Test CI pipeline on a branch
- [ ] Document required GitHub secrets (base64 encoded key)
- [ ] Add status badges to README

---

## 4. Acceptance Criteria

1. **Build**: `uv sync` installs all dependencies successfully (including Python 3.14 if available)
2. **Lint**: `uv run ruff check .` passes with no errors
3. **Format**: `uv run ruff format --check .` passes
4. **Types**: `uv run mypy src/` passes with no errors
5. **Tests**: `uv run pytest tests/unit` passes with >80% coverage
6. **CI**: GitHub Actions pipeline passes on all Python versions (3.11-3.14)
7. **Pre-commit**: All hooks pass on clean checkout

---

## 5. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing code during migration | Medium | High | Comprehensive tests before moving files |
| Type hint complexity in crypto code | Medium | Low | Use `# type: ignore` sparingly where needed |
| CI secrets management | Low | Medium | Use Base64 encoding for keys in GitHub Secrets |

---

## 6. Future Considerations

- Add dependabot for dependency updates
- Consider adding semantic-release for versioning
- Explore Codecov for coverage visualization
- Add documentation generation (mkdocs or sphinx)
