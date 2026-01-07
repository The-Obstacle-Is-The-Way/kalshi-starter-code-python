# SPEC-012: Developer Experience (DevX)

**Status:** Draft
**Priority:** P3
**Depends On:** All previous specs complete

---

## Overview

Add modern developer experience tooling for efficient development workflows. This includes a Makefile (or just), standardized commands, and quality-of-life improvements.

---

## Problem Statement

Currently, developers must remember multiple tool invocations:
```bash
uv run pytest tests/unit -v
uv run ruff check .
uv run ruff format .
uv run mypy src/
uv run alembic upgrade head
```

Modern projects provide unified command interfaces for common workflows.

---

## Requirements

### 1. Makefile (Primary)

Create a comprehensive Makefile with 2026 best practices:

```makefile
# Makefile - Kalshi Research Platform
# Modern Python DevX (2026)

.PHONY: help install dev test lint format check ci clean docs db

# Default target
help:
	@echo "Kalshi Research Platform - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install     Install production dependencies"
	@echo "  make dev         Install all dependencies (dev, research)"
	@echo ""
	@echo "Quality:"
	@echo "  make test        Run all tests"
	@echo "  make test-unit   Run unit tests only"
	@echo "  make test-cov    Run tests with coverage report"
	@echo "  make lint        Run linting (ruff check)"
	@echo "  make format      Format code (ruff format)"
	@echo "  make typecheck   Run type checking (mypy)"
	@echo "  make check       Run all quality checks"
	@echo "  make ci          Run full CI pipeline locally"
	@echo ""
	@echo "Database:"
	@echo "  make db-init     Initialize database"
	@echo "  make db-migrate  Run all migrations"
	@echo "  make db-revision Create new migration"
	@echo "  make db-reset    Reset database (DESTRUCTIVE)"
	@echo ""
	@echo "Development:"
	@echo "  make run         Start CLI help"
	@echo "  make shell       Start Python shell with imports"
	@echo "  make notebook    Start Jupyter notebook"
	@echo "  make clean       Clean build artifacts"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs        Build documentation"
	@echo "  make serve-docs  Serve docs locally"

# =============================================================================
# Setup
# =============================================================================

install:
	uv sync --no-dev

dev:
	uv sync --all-extras
	uv run pre-commit install

# =============================================================================
# Quality Checks
# =============================================================================

test:
	uv run pytest

test-unit:
	uv run pytest tests/unit -v

test-integration:
	uv run pytest tests/integration -v

test-cov:
	uv run pytest --cov=src/kalshi_research --cov-report=term-missing --cov-report=html

lint:
	uv run ruff check .

lint-fix:
	uv run ruff check . --fix

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy src/

# Run all quality checks
check: lint format-check typecheck
	@echo "All checks passed!"

# Full CI pipeline (what CI runs)
ci: check test-cov
	@echo "CI pipeline passed!"

# =============================================================================
# Database
# =============================================================================

db-init:
	uv run kalshi data init

db-migrate:
	uv run alembic upgrade head

db-revision:
	@read -p "Migration message: " msg; \
	uv run alembic revision --autogenerate -m "$$msg"

db-reset:
	rm -f data/kalshi.db
	uv run alembic upgrade head
	@echo "Database reset complete"

# =============================================================================
# Development
# =============================================================================

run:
	uv run kalshi --help

shell:
	uv run python -c "from kalshi_research import *; import IPython; IPython.embed()"

notebook:
	uv run jupyter notebook notebooks/

# Sync market data
sync:
	uv run kalshi data sync-markets

# Watch mode for development (requires watchdog)
watch:
	uv run watchmedo auto-restart --patterns="*.py" --recursive -- uv run pytest tests/unit -v

# =============================================================================
# Cleanup
# =============================================================================

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-all: clean
	rm -rf .venv/
	rm -rf data/kalshi.db

# =============================================================================
# Documentation
# =============================================================================

docs:
	@echo "Building documentation..."
	@echo "TODO: Add mkdocs or sphinx"

serve-docs:
	@echo "Serving documentation..."
	@echo "TODO: Add mkdocs serve or sphinx-autobuild"

# =============================================================================
# Release
# =============================================================================

build:
	uv build

publish-test:
	uv publish --repository testpypi

publish:
	uv publish
```

### 2. Justfile Alternative (Optional)

For cross-platform compatibility, provide `justfile`:

```just
# justfile - Modern command runner
# Install: brew install just (macOS) / cargo install just (any)

set shell := ["bash", "-uc"]

default:
    @just --list

# Install dev dependencies
dev:
    uv sync --all-extras
    uv run pre-commit install

# Run all tests
test:
    uv run pytest

# Run unit tests with verbose output
test-unit:
    uv run pytest tests/unit -v

# Run tests with coverage
test-cov:
    uv run pytest --cov=src/kalshi_research --cov-report=term-missing

# Run linting
lint:
    uv run ruff check .

# Format code
format:
    uv run ruff format .

# Run type checking
typecheck:
    uv run mypy src/

# Run all quality checks
check: lint typecheck
    uv run ruff format --check .

# Run full CI pipeline locally
ci: check test-cov

# Initialize database
db-init:
    uv run kalshi data init

# Run database migrations
db-migrate:
    uv run alembic upgrade head

# Create new migration
db-revision message:
    uv run alembic revision --autogenerate -m "{{message}}"

# Start Jupyter notebook
notebook:
    uv run jupyter notebook notebooks/

# Clean build artifacts
clean:
    rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ htmlcov/ .coverage
    find . -type d -name __pycache__ -exec rm -rf {} +
```

### 3. VS Code Tasks (Optional)

Create `.vscode/tasks.json` for IDE integration:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Test: All",
      "type": "shell",
      "command": "make test",
      "group": { "kind": "test", "isDefault": true }
    },
    {
      "label": "Test: Unit",
      "type": "shell",
      "command": "make test-unit"
    },
    {
      "label": "Lint: Check",
      "type": "shell",
      "command": "make lint"
    },
    {
      "label": "Lint: Fix",
      "type": "shell",
      "command": "make lint-fix"
    },
    {
      "label": "Format",
      "type": "shell",
      "command": "make format"
    },
    {
      "label": "Type Check",
      "type": "shell",
      "command": "make typecheck"
    },
    {
      "label": "CI: Full",
      "type": "shell",
      "command": "make ci",
      "group": { "kind": "build", "isDefault": true }
    }
  ]
}
```

### 4. mise Configuration (Version Management)

Create `.mise.toml` for Python version management:

```toml
[tools]
python = "3.12"
uv = "latest"

[env]
PYTHONDONTWRITEBYTECODE = "1"
PYTHONUNBUFFERED = "1"
```

### 5. Dev Container (Optional)

Create `.devcontainer/devcontainer.json` for VS Code:

```json
{
  "name": "Kalshi Research",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",
  "features": {
    "ghcr.io/devcontainers-contrib/features/uv:1": {}
  },
  "postCreateCommand": "make dev",
  "customizations": {
    "vscode": {
      "extensions": [
        "charliermarsh.ruff",
        "ms-python.python",
        "ms-python.mypy-type-checker",
        "ms-toolsai.jupyter"
      ]
    }
  }
}
```

---

## CLI Quick Reference Card

Add to `docs/CLI_REFERENCE.md`:

```markdown
# Kalshi CLI Quick Reference

## Data Management
kalshi data init              # Initialize database
kalshi data sync-markets      # Fetch all markets
kalshi data collect -i 15     # Collect prices every 15 min
kalshi data export -f parquet # Export to Parquet

## Market Analysis
kalshi market list            # List open markets
kalshi market get TICKER      # Get market details
kalshi market orderbook TICK  # View orderbook

## Scanning
kalshi scan opportunities -f close-race    # 45-55% markets
kalshi scan opportunities -f high-volume   # High volume
kalshi scan opportunities -f wide-spread   # Wide spreads

## Alerts
kalshi alerts list            # List active alerts
kalshi alerts add price TICK --above 60    # Price alert
kalshi alerts remove ID       # Remove alert

## Analysis
kalshi analysis calibration   # Brier score analysis
kalshi analysis metrics TICK  # Market metrics

## Research
kalshi research thesis create "My thesis" -m TICK1,TICK2
kalshi research thesis list
kalshi research backtest

## Portfolio
kalshi portfolio positions    # View positions
kalshi portfolio pnl          # P&L summary
kalshi portfolio history      # Trade history
```

---

## Acceptance Criteria

- [ ] `Makefile` exists with all standard targets
- [ ] `make help` shows all available commands
- [ ] `make dev` sets up complete dev environment
- [ ] `make check` runs lint + format + typecheck
- [ ] `make ci` runs full CI pipeline locally
- [ ] `make test-cov` generates coverage report
- [ ] All make targets work on macOS and Linux
- [ ] VS Code tasks.json configured (optional)
- [ ] CLI quick reference documented

---

## Testing

```bash
# Verify Makefile works
make help
make dev
make check
make test
make ci

# Verify individual targets
make lint
make format
make typecheck
make test-unit
make test-cov
```

---

## Priority Justification

**P3 (Low)** because:
- Platform is fully functional without this
- Existing commands documented in README
- Quality-of-life improvement only
- No user-facing functionality affected
