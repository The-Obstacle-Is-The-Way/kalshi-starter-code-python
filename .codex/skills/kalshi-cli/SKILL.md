---
name: kalshi-cli
description: Provides complete CLI and database navigation for the Kalshi Research Platform. Covers portfolio syncing, thesis tracking, market scanning, alerts, and analysis. Essential for running CLI commands correctly without assuming non-existent options.
---

# Kalshi Research Platform Navigation

This skill provides authoritative reference for CLI commands, database queries, and workflows. It prevents common mistakes like assuming CLI options exist when they don't.

## Quick Start

```bash
# Always run from repository root
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
| `EXA_API_KEY` | Exa-powered research/news | API key for Exa (`research context/topic`, `news collect`) |
| `EXA_BASE_URL` | Exa-powered research/news | Override Exa base URL (default: https://api.exa.ai) |
| `EXA_TIMEOUT` | Exa-powered research/news | Exa request timeout seconds (default: 30) |
| `EXA_MAX_RETRIES` | Exa-powered research/news | Exa max retries (default: 3) |
| `EXA_RETRY_DELAY` | Exa-powered research/news | Exa base retry delay seconds (default: 1) |

## File Locations

| Type | Path |
|------|------|
| Database | `data/kalshi.db` (SQLite) |
| Theses | `data/theses.json` |
| Alerts | `data/alerts.json` |
| Exa cache | `data/exa_cache/` |
| Exports | `data/exports/` |
| Alert log | `data/alert_monitor.log` |

---

## CLI Command Groups

### data - Data Management
```bash
uv run kalshi data init                    # Initialize database
uv run kalshi data migrate                 # Preview migrations (dry-run default)
uv run kalshi data migrate --apply         # Apply migrations
uv run kalshi data sync-markets            # Sync markets from API
uv run kalshi data sync-settlements        # Sync resolved outcomes
uv run kalshi data sync-trades             # Fetch public trade history (CSV/JSON output)
uv run kalshi data snapshot                # Take price snapshot
uv run kalshi data collect [--interval 15] [--once] [--max-pages N]  # Continuous collection
uv run kalshi data prune                   # Preview pruning (dry-run default)
uv run kalshi data prune --apply           # Apply pruning
uv run kalshi data vacuum                  # Reclaim DB space after deletes
uv run kalshi data export [-f csv|parquet] # Export data
uv run kalshi data stats                   # Show statistics
```

### market - Market Lookup
```bash
uv run kalshi market get TICKER            # Fetch single market
uv run kalshi market list [--status open] [--event EVT] [--event-prefix PREFIX] [--category TEXT] [--exclude-category TEXT] [--limit N] [--full]  # List markets (NO --search!)
uv run kalshi market orderbook TICKER      # Get orderbook
```

### scan - Opportunity Scanning
```bash
uv run kalshi scan opportunities [--filter close-race] [--category TEXT] [--no-sports] [--event-prefix PREFIX] [--top 10] [--max-pages N] [--full]
uv run kalshi scan arbitrage [--threshold 0.1] [--top 10] [--max-pages N] [--full]
uv run kalshi scan movers [--period 24h] [--top 10] [--max-pages N] [--full]
```

### portfolio - Portfolio Tracking (Requires Auth)
```bash
uv run kalshi portfolio sync               # Sync positions, fills, settlements
uv run kalshi portfolio positions          # View positions
uv run kalshi portfolio pnl                # View P&L
uv run kalshi portfolio balance            # View balance
uv run kalshi portfolio history [-n 20]    # Trade history
uv run kalshi portfolio link TICKER --thesis ID  # Link to thesis
uv run kalshi portfolio suggest-links      # Suggest thesis links for positions
```

### research - Thesis Management
```bash
uv run kalshi research context TICKER          # Exa: market context research
uv run kalshi research topic "TOPIC"           # Exa: topic research / ideation
uv run kalshi research cache clear [--all]     # Exa cache maintenance (expired-only default)
uv run kalshi research thesis create "TITLE" -m TICKER --your-prob 0.7 --market-prob 0.5 --confidence 0.8
uv run kalshi research thesis list [--full]
uv run kalshi research thesis show ID [--with-positions]
uv run kalshi research thesis resolve ID --outcome yes|no|void
uv run kalshi research backtest --start YYYY-MM-DD --end YYYY-MM-DD  # End date is inclusive
```

### news - News Monitoring & Sentiment (Exa-Powered)
```bash
uv run kalshi news track TICKER [--event] [--queries "a, b"]   # Start tracking
uv run kalshi news list-tracked [--all]                        # Show tracked items
uv run kalshi news collect [--ticker TICKER]                   # Collect news + sentiment
uv run kalshi news sentiment TICKER [--event] [--days 7]       # Sentiment summary
uv run kalshi news untrack TICKER                              # Stop tracking
```

### alerts - Alert System
```bash
uv run kalshi alerts list
uv run kalshi alerts add price|volume|spread TICKER [--above N] [--below N]
uv run kalshi alerts remove ALERT_ID
uv run kalshi alerts monitor [--interval 60] [--daemon] [--once] [--max-pages N]
uv run kalshi alerts trim-log               # Preview log trim (dry-run default)
uv run kalshi alerts trim-log --apply       # Apply trimming
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
2. **Use `--full/-F`** to disable CLI truncation; if you still need exact tickers, query the database.
3. **Always use `uv run kalshi`** prefix - commands require virtual environment.
4. **Check `--help`** before assuming options exist.
5. **`news track` defaults to 2 queries** (title + title + "news"), so `news collect` usually makes 2 Exa calls per tracked item.

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
sqlite3 data/kalshi.db "SELECT ticker, title FROM markets WHERE title LIKE '%keyword%' AND status = 'active'"

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
