# Kalshi Research Platform

[![CI](https://github.com/The-Obstacle-Is-The-Way/kalshi-starter-code-python/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/The-Obstacle-Is-The-Way/kalshi-starter-code-python/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/The-Obstacle-Is-The-Way/kalshi-starter-code-python/branch/main/graph/badge.svg)](https://codecov.io/gh/The-Obstacle-Is-The-Way/kalshi-starter-code-python)
[![Python](https://img.shields.io/badge/python-3.11%E2%80%933.13-blue)](https://www.python.org/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-261230?logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)
[![Mypy](https://img.shields.io/badge/type%20checked-mypy-blue)](https://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)

Research tools for Kalshi prediction market analysis.

Project intent: this is a **single-user research CLI** (plus local SQLite cache) for internal workflows. It is **not**
intended as a multi-user production service.

## Features

- **Data pipeline** - Sync markets/events/settlements, take price snapshots, export to Parquet/CSV, run DB migrations
- **Scanning** - Opportunities, new markets, movers, and basic arbitrage signals
- **Analysis** - Metrics, calibration (Brier score), and correlation (DB-backed)
- **Alerts** - Local alert conditions + monitoring loop (console/file/webhook), daemon mode + log trimming
- **Portfolio (authenticated)** - Sync positions/fills/settlements, compute FIFO cost basis + P&L (realized + unrealized)
- **Thesis tracking** - Create/list/show/resolve theses (local JSON)
- **Exa (optional)** - Market context/topic research, find similar pages, deep research tasks (with crash recovery), news tracking + sentiment
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
# Show exchange status (public)
uv run kalshi status

# Initialize database
uv run kalshi data init

# Validate/apply schema migrations (safe dry-run by default)
uv run kalshi data migrate

# Sync markets from Kalshi (start small)
uv run kalshi data sync-markets --max-pages 1

# Take a price snapshot (needed for movers/correlation)
uv run kalshi data snapshot --max-pages 1

# Scan for opportunities
uv run kalshi scan opportunities --filter close-race --max-pages 1 --full

# Get market details
uv run kalshi market get <TICKER>

# Start continuous data collection (interval is in minutes)
uv run kalshi data collect --interval 15

# (Optional) Exa-powered research
# EXA_API_KEY=... uv run kalshi research context TICKER-NAME --max-news 5 --max-papers 3
# (Paid API) EXA_API_KEY=... uv run kalshi research deep "What could make this market resolve YES?" --wait
```

## CLI Reference

See `uv run kalshi --help` for all commands.

## Documentation

- Hosted docs (GitHub Pages): https://the-obstacle-is-the-way.github.io/kalshi-starter-code-python/
- [docs/index.md](docs/index.md) - Docs index (Diataxis)
- [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md) - Quickstart
- [docs/getting-started/usage.md](docs/getting-started/usage.md) - Usage workflows
- [docs/developer/cli-reference.md](docs/developer/cli-reference.md) - CLI index (SSOT map)
- [docs/_specs/](docs/_specs/) - Internal technical specs

Build the docs site locally with MkDocs Material:
- `uv run mkdocs serve`
- `uv run mkdocs build --strict`

## Agent Skills

- Codex CLI skills live in `.codex/skills/` (restart Codex after changes).
- Claude Code skills live in `.claude/skills/`.

## Development

```bash
# Run tests
uv run pytest -m "not integration and not slow"

# Run linting
uv run ruff check .

# Run type checking
uv run mypy src/

# Run the full local quality gate suite (what CI runs)
uv run pre-commit run --all-files
```

## License

Apache-2.0 (see `LICENSE`)
