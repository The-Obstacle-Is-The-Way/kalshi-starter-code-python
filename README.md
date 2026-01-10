# Kalshi Research Platform

[![CI](https://github.com/The-Obstacle-Is-The-Way/kalshi-starter-code-python/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/The-Obstacle-Is-The-Way/kalshi-starter-code-python/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/The-Obstacle-Is-The-Way/kalshi-starter-code-python/branch/main/graph/badge.svg)](https://codecov.io/gh/The-Obstacle-Is-The-Way/kalshi-starter-code-python)
[![Python](https://img.shields.io/badge/python-3.11%E2%80%933.13-blue)](https://www.python.org/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-261230?logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)
[![Mypy](https://img.shields.io/badge/type%20checked-mypy-blue)](https://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)

Research tools for Kalshi prediction market analysis.

## Features

- **Data pipeline** - Sync markets/events, take price snapshots, export to Parquet/CSV
- **Scanning** - Opportunities, movers, and basic arbitrage signals
- **Analysis** - Metrics, calibration (Brier score), and correlation (DB-backed)
- **Alerts** - Local alert conditions + monitoring loop
- **Portfolio (authenticated)** - Sync trades/positions and compute FIFO cost basis + P&L
- **Thesis tracking** - Create/list/show/resolve theses (local JSON)
- **Exa (optional)** - Market context research, thesis evidence/invalidation, news tracking + sentiment
- **Notebooks** - Jupyter templates for exploration

Notes:
- `kalshi research backtest` runs real backtests on resolved theses (requires settlements in your DB).

## Installation

```bash
# Clone the repo
git clone https://github.com/The-Obstacle-Is-The-Way/kalshi-starter-code-python.git
cd kalshi-starter-code-python

# Install with uv (recommended)
uv sync --all-extras

# Or with pip
pip install -e ".[dev,research]"
```

## Quick Start

```bash
# Initialize database
uv run kalshi data init

# Sync markets from Kalshi (start small)
uv run kalshi data sync-markets --max-pages 1

# Scan for opportunities
uv run kalshi scan opportunities --filter close-race --max-pages 1

# Get market details
uv run kalshi market get TICKER-NAME

# Start continuous data collection
uv run kalshi data collect --interval 15

# (Optional) Exa-powered research
# EXA_API_KEY=... uv run kalshi research context TICKER-NAME --max-news 5 --max-papers 3
```

## CLI Reference

See `kalshi --help` for all commands.

## Documentation

- Hosted docs (GitHub Pages): https://the-obstacle-is-the-way.github.io/kalshi-starter-code-python/
- [docs/index.md](docs/index.md) - Docs index (Diataxis)
- [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md) - Quickstart
- [docs/getting-started/usage.md](docs/getting-started/usage.md) - Usage workflows
- [docs/developer/cli-reference.md](docs/developer/cli-reference.md) - CLI index (SSOT map)
- [docs/_specs/](docs/_specs/) - Internal technical specs

Build the docs site locally with MkDocs Material:
- `uv run mkdocs serve`

## Agent Skills

- Codex CLI skills live in `.codex/skills/` (restart Codex after changes).
- Claude Code skills live in `.claude/skills/`.

## Development

```bash
# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run type checking
uv run mypy src/
```

## License

Apache-2.0 (see `LICENSE`)
