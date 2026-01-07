# SPEC-009: Legacy Cleanup & Documentation

**Status:** Draft
**Priority:** P2
**Depends On:** SPEC-001 through SPEC-008 (all complete)

---

## Overview

Clean up legacy files from the original Kalshi starter code and create comprehensive documentation for actually using the research platform.

---

## Problem Statement

The project still contains legacy files from the original `kalshi-starter-code-python` repo:
- `clients.py` (root) - Superseded by `src/kalshi_research/api/client.py`
- `main.py` (root) - Basic example, now obsolete
- `requirements.txt` - Superseded by `pyproject.toml`

The README.md still references the old installation method and doesn't document the new platform.

New users have no guidance on how to actually USE the research platform.

---

## Requirements

### 1. Remove Legacy Files

```bash
# Files to remove
rm clients.py      # Superseded by src/kalshi_research/api/
rm main.py         # Obsolete example
rm requirements.txt # Superseded by pyproject.toml
```

**Verification:** These files are NOT imported anywhere in `src/` or `tests/`.

### 2. Update README.md

Complete rewrite to reflect the new platform:

```markdown
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
```

### 3. Create QUICKSTART.md

New file: `docs/QUICKSTART.md`

```markdown
# Quick Start Guide

Get started with Kalshi Research in 5 minutes.

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Installation

```bash
git clone <repo>
cd kalshi-research
uv sync
```

## First Steps

### 1. Initialize Database

```bash
kalshi data init
```

Creates SQLite database at `data/kalshi.db`.

### 2. Sync Market Data

```bash
kalshi data sync-markets
```

Fetches all markets and events from Kalshi API.

### 3. Explore Markets

```bash
# List open markets
kalshi market list

# Get specific market
kalshi market get KXBTC-25JAN01-60000

# View orderbook
kalshi market orderbook KXBTC-25JAN01-60000
```

### 4. Scan for Opportunities

```bash
# Close races (50/50 markets)
kalshi scan opportunities --filter close-race

# High volume markets
kalshi scan opportunities --filter high-volume

# Wide spread (arbitrage potential)
kalshi scan opportunities --filter wide-spread
```

### 5. Start Continuous Collection

```bash
# Collect price snapshots every 15 minutes
kalshi data collect --interval 15
```

### 6. Export for Analysis

```bash
# Export to Parquet (for pandas/DuckDB)
kalshi data export --format parquet

# Export to CSV
kalshi data export --format csv
```

## Next Steps

- Open `notebooks/exploration.ipynb` for interactive analysis
- Read [USAGE.md](USAGE.md) for advanced features
- Set up alerts for price movements
```

### 4. Create USAGE.md

New file: `docs/USAGE.md`

Comprehensive guide covering:
- All CLI commands with examples
- Python API usage
- Setting up alerts
- Creating and tracking theses
- Running backtests
- Using Jupyter notebooks
- Authentication setup (for trading features)
- Data export workflows
- Troubleshooting

---

## Acceptance Criteria

- [ ] `clients.py`, `main.py`, `requirements.txt` removed from root
- [ ] README.md completely rewritten
- [ ] `docs/QUICKSTART.md` exists with working examples
- [ ] `docs/USAGE.md` exists with comprehensive guide
- [ ] All CLI commands documented
- [ ] No broken links or references to deleted files
- [ ] `uv sync && kalshi --help` works for new clone

---

## Testing

```bash
# Verify no imports of legacy files
grep -r "from clients import" src/ tests/
grep -r "import clients" src/ tests/
grep -r "from main import" src/ tests/

# Verify README examples work
kalshi data init
kalshi market list --limit 5
kalshi scan opportunities --top 5
```

---

## Notes

- Keep original Kalshi license/attribution if required
- Archive legacy files in `docs/_archive/` if needed for reference
