---
name: kalshi-cli
description: Provides complete CLI and database navigation for the Kalshi Research Platform. Covers portfolio syncing, thesis tracking, market scanning, alerts, and analysis. Essential for running CLI commands correctly without assuming non-existent options.
allowed-tools: Bash, Read, Grep, Glob
---

# Kalshi Research Platform Navigation

This skill provides authoritative reference for CLI commands, database queries, and workflows. It prevents common mistakes like assuming CLI options exist when they don't.

## Quick Start

```bash
# Always run from repository root
cd /Users/ray/Desktop/CLARITY-DIGITAL-TWIN/kalshi-starter-code-python

# All commands use uv run prefix
uv run kalshi --help
```

## Environment Variables

| Variable | Required For | Description |
|----------|-------------|-------------|
| `KALSHI_KEY_ID` | Portfolio commands | API key ID from Kalshi |
| `KALSHI_PRIVATE_KEY_PATH` | Portfolio commands | Path to RSA private key file |
| `KALSHI_PRIVATE_KEY_B64` | Portfolio commands | Alternative: Base64-encoded key |
| `KALSHI_ENVIRONMENT` | All | `prod` or `demo` (default: prod) |
| `KALSHI_RATE_TIER` | API calls | `basic`/`advanced`/`premier`/`prime` |

## File Locations

| Type | Path |
|------|------|
| Database | `data/kalshi.db` (SQLite) |
| Theses | `data/theses.json` |
| Alerts | `data/alerts.json` |
| Exports | `data/exports/` |
| Alert log | `data/alert_monitor.log` |

---

## CLI Command Groups

### data - Data Management
```bash
uv run kalshi data init                    # Initialize database
uv run kalshi data sync-markets            # Sync markets from API
uv run kalshi data sync-settlements        # Sync resolved outcomes
uv run kalshi data snapshot                # Take price snapshot
uv run kalshi data collect [--once]        # Continuous collection
uv run kalshi data export [-f csv|parquet] # Export data
uv run kalshi data stats                   # Show statistics
```

### market - Market Lookup
```bash
uv run kalshi market get TICKER            # Fetch single market
uv run kalshi market list [-n 20]          # List markets (NO --search!)
uv run kalshi market orderbook TICKER      # Get orderbook
```

### scan - Opportunity Scanning
```bash
uv run kalshi scan opportunities [-f close-race|high-volume|wide-spread|expiring-soon]
uv run kalshi scan arbitrage [--threshold 0.1]
uv run kalshi scan movers [-p 1h|6h|24h]
```

### portfolio - Portfolio Tracking (Requires Auth)
```bash
uv run kalshi portfolio sync               # Sync from Kalshi API
uv run kalshi portfolio positions          # View positions
uv run kalshi portfolio pnl                # View P&L
uv run kalshi portfolio balance            # View balance
uv run kalshi portfolio history [-n 20]    # Trade history
uv run kalshi portfolio link TICKER --thesis ID  # Link to thesis
```

### research - Thesis Management
```bash
uv run kalshi research thesis create "TITLE" -m TICKER --your-prob 0.7 --market-prob 0.5 --confidence 0.8
uv run kalshi research thesis list
uv run kalshi research thesis show ID [--with-positions]
uv run kalshi research thesis resolve ID --outcome yes|no|void
uv run kalshi research backtest --start YYYY-MM-DD --end YYYY-MM-DD
```

### alerts - Alert System
```bash
uv run kalshi alerts list
uv run kalshi alerts add price|volume|spread TICKER [--above N] [--below N]
uv run kalshi alerts remove ALERT_ID
uv run kalshi alerts monitor [--daemon] [--once]
```

### analysis - Market Analysis
```bash
uv run kalshi analysis calibration [--days 30]
uv run kalshi analysis metrics TICKER
uv run kalshi analysis correlation [--min 0.5]
```

---

## Critical Rules

1. **NO `--search` option exists** on any command. Query database directly instead.
2. **Use exact tickers** - CLI display truncates with `...`; get full tickers from database.
3. **Always use `uv run kalshi`** prefix - commands require virtual environment.
4. **Check `--help`** before assuming options exist.

---

## Detailed References

For complete documentation, see:
- **[CLI-REFERENCE.md](CLI-REFERENCE.md)** - Every command with ALL options
- **[DATABASE.md](DATABASE.md)** - Schema and SQL queries
- **[WORKFLOWS.md](WORKFLOWS.md)** - Step-by-step guides
- **[GOTCHAS.md](GOTCHAS.md)** - Edge cases and pitfalls

---

## Quick Database Queries

When CLI options are insufficient, query SQLite directly:

```bash
# Find markets by keyword (since no --search exists)
sqlite3 data/kalshi.db "SELECT ticker, title FROM markets WHERE title LIKE '%keyword%' AND status = 'open'"

# Get full ticker from partial match
sqlite3 data/kalshi.db "SELECT ticker FROM markets WHERE ticker LIKE 'KXFED%'"

# Get all trades for analysis
sqlite3 data/kalshi.db "SELECT * FROM trades ORDER BY executed_at DESC LIMIT 20"

# Calculate net position from trades
sqlite3 data/kalshi.db "SELECT ticker, side, SUM(CASE WHEN action='buy' THEN quantity ELSE -quantity END) as net FROM trades GROUP BY ticker, side HAVING net > 0"
```

---

## Source Code Locations

| Module | Path |
|--------|------|
| CLI commands | `src/kalshi_research/cli/` |
| API clients | `src/kalshi_research/api/client.py` |
| Portfolio syncer | `src/kalshi_research/portfolio/syncer.py` |
| Thesis logic | `src/kalshi_research/research/thesis.py` |
| Database | `src/kalshi_research/data/database.py` |
| Paths | `src/kalshi_research/paths.py` |
| Analysis | `src/kalshi_research/analysis/` |
| Alerts | `src/kalshi_research/alerts/` |
