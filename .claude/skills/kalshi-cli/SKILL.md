---
name: kalshi-cli
description: Navigate Kalshi Research Platform CLI and database. Use when running CLI commands, querying the database, syncing portfolio, creating theses, or analyzing markets.
allowed-tools: Bash, Read, Grep, Glob
---

# Kalshi Research Platform CLI Navigation

This skill provides complete reference for the Kalshi Research Platform CLI commands and database. Use this to avoid common pitfalls like assuming CLI options exist when they don't.

## CRITICAL: Always Run from Repository Root

```bash
cd /Users/ray/Desktop/CLARITY-DIGITAL-TWIN/kalshi-starter-code-python
```

All commands use `uv run kalshi` prefix.

## Environment Variables (Required for Authenticated Commands)

Portfolio commands require authentication:
- `KALSHI_KEY_ID` - API key ID from Kalshi
- `KALSHI_PRIVATE_KEY_PATH` - Path to RSA private key file
- `KALSHI_PRIVATE_KEY_B64` - Alternative: Base64-encoded private key
- `KALSHI_ENVIRONMENT` - `prod` or `demo` (default: prod)
- `KALSHI_RATE_TIER` - `basic`, `advanced`, `premier`, or `prime` (default: basic)

## Database Location

- Default: `data/kalshi.db` (SQLite)
- Theses: `data/theses.json` (JSON file, not in database)
- Alerts: `data/alerts.json`
- Exports: `data/exports/`

---

## Complete CLI Reference

### Main Command

```bash
uv run kalshi [--env prod|demo] COMMAND
```

### data - Data Management

```bash
# Initialize database (run once)
uv run kalshi data init

# Sync markets from API to database
uv run kalshi data sync-markets

# Sync settlements (resolved market outcomes)
uv run kalshi data sync-settlements

# Take price snapshot of all markets
uv run kalshi data snapshot

# Continuous data collection
uv run kalshi data collect

# Export to Parquet or CSV
uv run kalshi data export [-d DB_PATH] [-o OUTPUT_DIR] [-f parquet|csv]

# Show database statistics
uv run kalshi data stats
```

### market - Market Lookup

```bash
# Get single market by EXACT ticker
uv run kalshi market get TICKER

# List markets (NO --search option exists!)
uv run kalshi market list [-s STATUS] [-e EVENT_TICKER] [-n LIMIT]
#   -s/--status: open, closed, settled (default: open)
#   -e/--event: Filter by event ticker
#   -n/--limit: Max results (default: 20)

# Get orderbook
uv run kalshi market orderbook TICKER
```

**IMPORTANT**: There is NO `--search` or `--query` option on `market list`. To find markets:
1. Query database directly: `sqlite3 data/kalshi.db "SELECT ticker, title FROM markets WHERE title LIKE '%keyword%'"`
2. Use `kalshi data sync-markets` first to populate the database
3. Use exact tickers from database queries

### scan - Market Scanning

```bash
# Scan for opportunities
uv run kalshi scan opportunities [-f FILTER] [-n TOP] [--min-volume N] [--max-spread N]
#   -f/--filter: close-race, high-volume, wide-spread, expiring-soon
#   -n/--top: Number of results (default: 10)

# Find arbitrage opportunities
uv run kalshi scan arbitrage

# Show biggest price movers
uv run kalshi scan movers
```

### portfolio - Portfolio Tracking (Requires Auth)

```bash
# Sync positions and trades from Kalshi API
uv run kalshi portfolio sync [-d DB_PATH] [--skip-mark-prices] [--rate-tier TIER]

# View current positions
uv run kalshi portfolio positions [-d DB_PATH]

# View P&L summary
uv run kalshi portfolio pnl [-d DB_PATH]

# View account balance
uv run kalshi portfolio balance [--rate-tier TIER]

# View trade history
uv run kalshi portfolio history [-d DB_PATH] [-n LIMIT] [-t TICKER]

# Link position to thesis
uv run kalshi portfolio link POSITION_ID THESIS_ID

# Suggest thesis-position links
uv run kalshi portfolio suggest-links [-d DB_PATH]
```

### research - Research & Thesis Tracking

```bash
# Create new thesis (ALL flags required)
uv run kalshi research thesis create "TITLE" \
  -m TICKER1,TICKER2 \
  --your-prob 0.65 \
  --market-prob 0.50 \
  --confidence 0.8 \
  --bull "Why YES case" \
  --bear "Why NO case"

# List all theses
uv run kalshi research thesis list

# Show thesis details
uv run kalshi research thesis show THESIS_ID

# Resolve thesis with outcome
uv run kalshi research thesis resolve THESIS_ID --outcome yes|no|void

# Run backtest on resolved theses
uv run kalshi research backtest --start YYYY-MM-DD --end YYYY-MM-DD [-t THESIS_ID]
```

### alerts - Alert Management

```bash
# List active alerts
uv run kalshi alerts list

# Add alert (price, volume, or spread)
uv run kalshi alerts add ALERT_TYPE TICKER [--above N] [--below N]
#   ALERT_TYPE: price, volume, spread

# Remove alert
uv run kalshi alerts remove ALERT_ID

# Start monitoring (foreground)
uv run kalshi alerts monitor
```

### analysis - Market Analysis

```bash
# Analyze market calibration and Brier scores
uv run kalshi analysis calibration

# Calculate market metrics for a ticker
uv run kalshi analysis metrics TICKER

# Analyze correlations between markets
uv run kalshi analysis correlation
```

---

## Database Schema

Query the database directly when CLI options are insufficient:

```bash
sqlite3 data/kalshi.db "YOUR QUERY"
```

### Tables

**events** - Market events/categories
- ticker (PK), series_ticker, title, status, category, mutually_exclusive, created_at, updated_at

**markets** - Individual prediction markets
- ticker (PK), event_ticker (FK), series_ticker, title, subtitle, status, result
- open_time, close_time, expiration_time, category, subcategory, created_at, updated_at

**price_snapshots** - Historical price data
- id (PK), ticker (FK), snapshot_time, yes_bid, yes_ask, no_bid, no_ask
- last_price, volume, volume_24h, open_interest, liquidity

**settlements** - Resolved market outcomes
- ticker (PK/FK), event_ticker, settled_at, result, final_yes_price, final_no_price
- yes_payout, no_payout

**positions** - Synced portfolio positions
- id (PK), ticker, side (yes/no), quantity, avg_price_cents, current_price_cents
- unrealized_pnl_cents, realized_pnl_cents, thesis_id, opened_at, closed_at, last_synced

**trades** - Synced trade history
- id (PK), kalshi_trade_id (unique), ticker, side (yes/no), action (buy/sell)
- quantity, price_cents, total_cost_cents, fee_cents, position_id, executed_at, synced_at

### Common Queries

```sql
-- Find markets by keyword
SELECT ticker, title FROM markets WHERE title LIKE '%keyword%' AND status = 'open';

-- Get all trades for a ticker
SELECT * FROM trades WHERE ticker = 'TICKER' ORDER BY executed_at;

-- Get open positions from trades (if positions table is empty)
SELECT ticker, side, SUM(CASE WHEN action='buy' THEN quantity ELSE -quantity END) as net_qty
FROM trades GROUP BY ticker, side HAVING net_qty > 0;

-- Get full ticker from partial match
SELECT ticker, title FROM markets WHERE ticker LIKE 'KXFED%';

-- Get trade history with prices
SELECT ticker, side, action, quantity, price_cents, executed_at
FROM trades ORDER BY executed_at DESC LIMIT 20;
```

---

## Common Workflows

### Sync Portfolio and Create Theses

```bash
# 1. Sync trades from Kalshi API
uv run kalshi portfolio sync

# 2. Check trade history
uv run kalshi portfolio history -n 50

# 3. If positions table empty but trades exist, query trades directly
sqlite3 data/kalshi.db "SELECT DISTINCT ticker FROM trades"

# 4. Get market price for a ticker
uv run kalshi market get EXACT_TICKER

# 5. Create thesis for a position
uv run kalshi research thesis create "My thesis title" \
  -m EXACT_TICKER \
  --your-prob 0.70 \
  --market-prob 0.55 \
  --confidence 0.75 \
  --bull "Reasons for YES" \
  --bear "Reasons for NO"
```

### Track and Resolve Theses

```bash
# List theses
uv run kalshi research thesis list

# When market resolves, update thesis
uv run kalshi research thesis resolve THESIS_ID --outcome yes

# Run backtest to see calibration
uv run kalshi research backtest --start 2024-01-01 --end 2025-12-31
```

### Find Markets Without --search

Since `kalshi market list` has NO search option:

```bash
# 1. Sync markets first
uv run kalshi data sync-markets

# 2. Query database directly
sqlite3 data/kalshi.db "SELECT ticker, title FROM markets WHERE title LIKE '%Super Bowl%' AND status = 'open'"

# 3. Use exact ticker from results
uv run kalshi market get KXSB-26-DEN
```

---

## Common Mistakes to Avoid

1. **DO NOT assume CLI options exist** - Check `--help` for each command
2. **DO NOT use truncated tickers** - CLI display truncates with `...`; get full tickers from database
3. **DO NOT try inline Python for API calls** - Use CLI commands which handle auth properly
4. **DO NOT assume `--search` exists** on any command - it doesn't; query database instead
5. **DO NOT skip `uv run` prefix** - Commands require the virtual environment

---

## File Locations

- CLI source: `src/kalshi_research/cli/`
- API clients: `src/kalshi_research/api/client.py`
- Portfolio syncer: `src/kalshi_research/portfolio/syncer.py`
- Thesis logic: `src/kalshi_research/research/thesis.py`
- Database manager: `src/kalshi_research/data/database.py`
- Path defaults: `src/kalshi_research/paths.py`
