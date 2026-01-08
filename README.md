# Kalshi Research Platform

Research tools for Kalshi prediction market analysis.

## Features

- **Data pipeline** - Sync markets/events, take price snapshots, export to Parquet/CSV
- **Scanning** - Opportunities, movers, and basic arbitrage signals
- **Analysis** - Metrics, calibration (Brier score), and correlation (DB-backed)
- **Alerts** - Local alert conditions + monitoring loop
- **Portfolio (authenticated)** - Sync trades/positions and compute FIFO cost basis + P&L
- **Thesis tracking** - Create/list/show/resolve theses (local JSON)
- **Notebooks** - Jupyter templates for exploration

Notes:
- `kalshi research backtest` exists but is currently a placeholder.

## Installation

```bash
# Clone the repo
git clone https://github.com/your-username/kalshi-research.git
cd kalshi-research

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
```

## CLI Reference

See `kalshi --help` for all commands.

## Documentation

- [docs/README.md](docs/README.md) - Diataxis docs index
- [docs/QUICKSTART.md](docs/QUICKSTART.md) - Tutorial quickstart
- [docs/USAGE.md](docs/USAGE.md) - How-to workflows
- [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) - CLI index
- [docs/_specs/](docs/_specs/) - Internal technical specs

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

MIT
