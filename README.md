# Kalshi Research Platform

Research tools for Kalshi prediction market analysis.

## Features

- **Market Scanner** - Find close races, high volume, wide spreads
- **Calibration Analysis** - Brier scores, historical accuracy
- **Edge Detection** - Flag mispriced markets vs your thesis
- **Event Correlation** - Analyze related market movements
- **Alerts** - Get notified when conditions are met
- **Backtesting** - Test trading strategies on historical data
- **Notebooks** - Jupyter templates for exploration

## Installation

```bash
# Clone the repo
git clone https://github.com/your-username/kalshi-research.git
cd kalshi-research

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e ".[dev,research]"
```

## Quick Start

```bash
# Initialize database
kalshi data init

# Sync markets from Kalshi
kalshi data sync-markets

# Scan for opportunities
kalshi scan opportunities --filter close-race

# Get market details
kalshi market get TICKER-NAME

# Start continuous data collection
kalshi data collect --interval 15
```

## CLI Reference

See `kalshi --help` for all commands.

## Documentation

- [QUICKSTART.md](docs/QUICKSTART.md) - Get started in 5 minutes
- [USAGE.md](docs/USAGE.md) - Detailed usage guide
- [docs/_specs/](docs/_specs/) - Technical specifications

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
