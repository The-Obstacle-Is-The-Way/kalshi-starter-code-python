# Kalshi CLI Quick Reference

Quick reference for all `kalshi` commands. For detailed usage, run `kalshi --help` or `kalshi <command> --help`.

---

## Data Management

```bash
# Initialize database (creates schema, runs migrations)
kalshi data init

# Sync all markets from Kalshi API
kalshi data sync-markets

# Collect price snapshots every N minutes (run continuously)
kalshi data collect --interval 15

# Export data to Parquet/DuckDB
kalshi data export --format parquet --output data/export/

# Show database statistics
kalshi data stats
```

---

## Market Analysis

```bash
# List all open markets
kalshi market list

# Get detailed market information
kalshi market get TICKER

# View orderbook for a market
kalshi market orderbook TICKER
```

---

## Scanning

```bash
# Find close-race markets (45-55% probability)
kalshi scan opportunities --filter close-race

# Find high-volume markets
kalshi scan opportunities --filter high-volume

# Find wide-spread markets (potential inefficiency)
kalshi scan opportunities --filter wide-spread

# Find markets with volume edge
kalshi scan opportunities --filter volume-edge

# Find markets with thesis edge
kalshi scan opportunities --filter thesis-edge

# Find arbitrage opportunities (not yet implemented)
kalshi scan arbitrage

# Show biggest price movers (not yet implemented)
kalshi scan movers
```

---

## Alerts

```bash
# List all active alerts
kalshi alerts list

# Add price threshold alert
kalshi alerts add price TICKER --above 60
kalshi alerts add price TICKER --below 40

# Add volume alert
kalshi alerts add volume TICKER --threshold 10000

# Add spread alert
kalshi alerts add spread TICKER --threshold 5

# Remove alert by ID
kalshi alerts remove ALERT_ID

# Run continuous monitoring (not yet implemented)
kalshi alerts monitor
```

---

## Analysis

```bash
# Run calibration analysis (Brier scores)
kalshi analysis calibration

# Calculate probability metrics for a market
kalshi analysis metrics TICKER

# Analyze market correlations (not yet implemented)
kalshi analysis correlation TICKER1 TICKER2
```

---

## Research

```bash
# Create new thesis
kalshi research thesis create "My thesis about X" --markets TICK1,TICK2

# List all theses
kalshi research thesis list

# Show thesis details
kalshi research thesis show THESIS_ID

# Resolve thesis (mark outcome)
kalshi research thesis resolve THESIS_ID --outcome correct

# Run backtest
kalshi research backtest --start 2024-01-01 --end 2024-12-31
```

---

## Portfolio (Read-Only Tracking)

**Note:** Requires `KALSHI_API_KEY` and `KALSHI_PRIVATE_KEY` environment variables.

```bash
# Sync portfolio from Kalshi API
kalshi portfolio sync

# View current positions
kalshi portfolio positions

# View P&L summary
kalshi portfolio pnl

# View account balance
kalshi portfolio balance

# View trade history
kalshi portfolio history

# Link position to thesis (not yet implemented)
kalshi portfolio link TICKER --thesis THESIS_ID

# Auto-suggest thesis-position links (not yet implemented)
kalshi portfolio suggest-links
```

---

## Database Operations

```bash
# Run migrations (upgrade to latest schema)
kalshi data init  # or use: alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Reset database (DESTRUCTIVE)
rm data/kalshi.db && alembic upgrade head
```

---

## Global Options

All commands support:

```bash
--help     Show help for command
--version  Show version
```

---

## Environment Variables

```bash
# Required for authenticated endpoints (portfolio sync)
export KALSHI_API_KEY="your-key-id"
export KALSHI_PRIVATE_KEY="your-private-key"

# Optional configuration
export KALSHI_BASE_URL="https://api.elections.kalshi.com"
export KALSHI_DB_PATH="data/kalshi.db"
```

---

## Typical Workflows

### Initial Setup

```bash
# 1. Install dependencies
make dev  # or: uv sync --all-extras

# 2. Initialize database
kalshi data init

# 3. Sync markets
kalshi data sync-markets
```

### Research Workflow

```bash
# 1. Find opportunities
kalshi scan opportunities --filter close-race

# 2. Analyze specific market
kalshi market get KXBTC-24DEC31-B50K

# 3. Create thesis
kalshi research thesis create "Bitcoin will hit 50K" --markets KXBTC-24DEC31-B50K

# 4. Set up alerts
kalshi alerts add price KXBTC-24DEC31-B50K --above 60

# 5. Monitor continuously
kalshi data collect --interval 15
```

### Analysis Workflow

```bash
# 1. Sync latest data
kalshi data sync-markets

# 2. Run calibration analysis
kalshi analysis calibration

# 3. Export for deeper analysis
kalshi data export --format parquet --output data/export/

# 4. Open Jupyter notebook
make notebook  # or: jupyter notebook notebooks/
```

### Portfolio Tracking Workflow

```bash
# 1. Set environment variables
export KALSHI_API_KEY="..."
export KALSHI_PRIVATE_KEY="..."

# 2. Sync portfolio
kalshi portfolio sync

# 3. View positions
kalshi portfolio positions

# 4. Check P&L
kalshi portfolio pnl

# 5. Link to thesis
kalshi research thesis show THESIS_ID --with-positions
```

---

## Tips

- Use `--help` on any command for detailed options
- Most commands accept `--format json` for machine-readable output
- Use `make test` to verify installation
- Use `make check` to run all quality checks
- Set up alerts before starting data collection for real-time notifications

---

## See Also

- [README.md](../README.md) - Project overview
- [QUICKSTART.md](QUICKSTART.md) - Getting started guide
- [USAGE.md](USAGE.md) - Detailed usage examples
