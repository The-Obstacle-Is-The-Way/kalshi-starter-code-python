# SPEC-001: Modern Python Project Foundation

**Status:** Draft
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
    "cryptography>=46.0.0",        # Updated for 2026
    "websockets>=15.0.0",          # Updated
    "python-dotenv>=1.0.0",
    "pydantic>=2.12.0",            # Updated
    "httpx>=0.28.0",               # Modern HTTP client (async support)
    "tenacity>=9.1.0",             # Retry logic
    "structlog>=25.0.0",           # Structured logging
    "sqlalchemy>=2.0.40",          # Database ORM
    "alembic>=1.14.0",             # Database migrations
    "duckdb>=1.1.0",               # Analytical OLAP database
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-cov>=6.0.0",
    "pytest-sugar>=1.0.0",
    "pytest-xdist>=3.6.0",     # Parallel test execution
    "pytest-asyncio>=0.25.0",  # Async test support
    "pytest-mock>=3.14.0",
    "ruff>=0.9.0",
    "mypy>=1.14.0",
    "pre-commit>=4.0.0",
    "respx>=0.22.0",           # Mock httpx requests
    "polyfactory>=3.0.0",      # Test data factories
    "hypothesis>=6.122.0",     # Property-based testing
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
kalshi = "kalshi_research.cli:main"

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
module = ["websockets.*", "respx.*", "scipy.*", "matplotlib.*", "pandas.*"]
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
        run: uv sync --dev
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