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
