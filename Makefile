# Makefile - Kalshi Research Platform
# Modern Python DevX (2026)

.PHONY: help install dev test lint format check ci clean docs docs-serve docs-build db

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
	@echo "  make lint-fix    Run linting with auto-fix"
	@echo "  make format      Format code (ruff format)"
	@echo "  make format-check Check code formatting"
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
	@echo "  make sync        Sync market data"
	@echo "  make clean       Clean build artifacts"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs        View documentation"
	@echo "  make docs-serve  Serve docs site (MkDocs)"
	@echo "  make docs-build  Build docs site (strict)"

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
	uv run pytest --cov=kalshi_research --cov-report=term-missing --cov-report=html

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
	@echo "Starting Python shell with kalshi_research imports..."
	@uv run python -c "from kalshi_research.api.client import KalshiPublicClient, KalshiClient; from kalshi_research.data.database import DatabaseManager; from kalshi_research.analysis.scanner import MarketScanner; print('Available: KalshiPublicClient, KalshiClient, DatabaseManager, MarketScanner'); import code; code.interact(local=locals())"

notebook:
	uv run jupyter notebook notebooks/

# Sync market data
sync:
	uv run kalshi data sync-markets

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
	@echo "Documentation available:"
	@echo "  README.md          - Project overview"
	@echo "  docs/index.md                - Docs index"
	@echo "  docs/tutorials/quickstart.md - Quick start guide"
	@echo "  docs/how-to/usage.md         - Usage examples"
	@echo "  docs/reference/cli-reference.md - CLI command reference"

docs-serve:
	uv run mkdocs serve

docs-build:
	uv run mkdocs build --strict

# =============================================================================
# Release
# =============================================================================

build:
	uv build

publish-test:
	uv publish --repository testpypi

publish:
	uv publish
