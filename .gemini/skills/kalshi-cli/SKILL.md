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
| `KALSHI_DEMO_KEY_ID` | Portfolio commands | Demo API key ID from Kalshi (preferred when `KALSHI_ENVIRONMENT=demo`) |
| `KALSHI_DEMO_PRIVATE_KEY_PATH` | Portfolio commands | Path to demo RSA private key file |
| `KALSHI_DEMO_PRIVATE_KEY_B64` | Portfolio commands | Alternative: Base64-encoded demo key |
| `KALSHI_ENVIRONMENT` | All | `prod` or `demo` (default: prod); when demo, prefers `KALSHI_DEMO_*` creds if set |
| `KALSHI_RATE_TIER` | API calls | `basic`/`advanced`/`premier`/`prime` |
| `KALSHI_LOG_LEVEL` | Debugging | Structured log level for CLI (default: `WARNING`; logs go to stderr) |
| `EXA_API_KEY` | Exa-powered research/news | API key for Exa (`research context/topic/similar/deep`, `research thesis create --with-research`, `research thesis check-invalidation`, `research thesis suggest`, `news collect`) |
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

### status/version - Utilities
```bash
uv run kalshi status [--json]             # Exchange status
uv run kalshi version                     # CLI version info
```

### data - Data Management
```bash
uv run kalshi data init [--db PATH]                        # Initialize database
uv run kalshi data migrate [--dry-run|--apply]             # Migrations (dry-run default)
uv run kalshi data sync-markets [--status open] [--max-pages N] [--mve-filter exclude|only] [--include-mve-events]
uv run kalshi data sync-settlements [--max-pages N]        # Sync settled outcomes
uv run kalshi data sync-trades [--ticker TICKER] [--limit N] [--min-ts TS] [--max-ts TS] [--output FILE] [--json]
uv run kalshi data snapshot [--status open] [--max-pages N]  # Take price snapshot
uv run kalshi data collect [--interval 15] [--once] [--max-pages N] [--include-mve-events]  # Continuous collection
uv run kalshi data export [--format parquet|csv] [--output DIR]      # Export data
uv run kalshi data stats                                   # Show statistics
uv run kalshi data prune [--snapshots-older-than-days N] [--news-older-than-days N] [--dry-run|--apply]
uv run kalshi data vacuum                                  # Reclaim DB space after deletes
```

### market - Market Lookup
```bash
uv run kalshi market list [--status open] [--event EVT] [--event-prefix PREFIX] [--category TEXT] [--exclude-category TEXT] [--limit N] [--full/-F]  # List markets (NO --search!)
uv run kalshi market get TICKER                                    # Fetch single market
uv run kalshi market orderbook TICKER [--depth 5]                  # Get orderbook
uv run kalshi market liquidity TICKER [--depth 25] [--max-slippage-cents 3]
uv run kalshi market history TICKER [--series SERIES] [--interval 1h] [--days 7] [--start-ts TS] [--end-ts TS] [--json]
```

### scan - Opportunity Scanning
```bash
uv run kalshi scan opportunities [--filter close-race] [--category TEXT] [--no-sports] [--event-prefix PREFIX] [--top 10] [--max-pages N] [--full/-F]
uv run kalshi scan new-markets [--hours 24] [--category econ,ai] [--include-unpriced] [--limit 20] [--max-pages N] [--json] [--full/-F]
uv run kalshi scan arbitrage [--db PATH] [--threshold 0.1] [--top 10] [--tickers-limit N] [--max-pages N] [--full/-F]
uv run kalshi scan movers [--db PATH] [--period 24h] [--top 10] [--max-pages N] [--full/-F]
```

### portfolio - Portfolio Tracking (Requires Auth)
```bash
uv run kalshi portfolio sync [--db PATH] [--env demo|prod] [--rate-tier basic|advanced|premier|prime] [--skip-mark-prices]
uv run kalshi portfolio positions [--db PATH] [--ticker TICKER] [--full/-F]
uv run kalshi portfolio pnl [--db PATH] [--ticker TICKER] [--full/-F]
uv run kalshi portfolio balance [--env demo|prod] [--rate-tier basic|advanced|premier|prime]
uv run kalshi portfolio history [-n 20] [--db PATH] [--ticker TICKER]
uv run kalshi portfolio link TICKER --thesis ID [--db PATH]  # Link position to thesis
uv run kalshi portfolio suggest-links [--db PATH]
```

### research - Research & Thesis Tracking
```bash
uv run kalshi research backtest --start YYYY-MM-DD --end YYYY-MM-DD [--db PATH]  # End date is inclusive
uv run kalshi research context TICKER [--max-news 10] [--max-papers 5] [--days 30] [--json]
uv run kalshi research topic "TOPIC" [--no-summary] [--json]
uv run kalshi research similar URL [-n 10] [--json]
uv run kalshi research deep "TOPIC" [--model exa-research-fast|exa-research|exa-research-pro] [--wait] [--schema FILE] [--json]  # Paid API
uv run kalshi research cache clear [--all] [--cache-dir DIR]
uv run kalshi research thesis create "TITLE" -m T1,T2 --your-prob 0.7 --market-prob 0.5 --confidence 0.8 [--with-research] [-y]
uv run kalshi research thesis list [--full/-F]
uv run kalshi research thesis show ID [--with-positions] [--db PATH]
uv run kalshi research thesis edit ID [--title TEXT] [--bull TEXT] [--bear TEXT]
uv run kalshi research thesis resolve ID --outcome yes|no|void
uv run kalshi research thesis check-invalidation ID [--hours 48]
uv run kalshi research thesis suggest [--category TEXT]
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
uv run kalshi alerts add price|volume|spread|sentiment TICKER (--above N | --below N)
uv run kalshi alerts remove ALERT_ID_PREFIX
uv run kalshi alerts monitor [--interval 60] [--daemon] [--once] [--max-pages N] [--output-file PATH] [--webhook-url URL]
uv run kalshi alerts trim-log [--log PATH] [--max-mb N] [--keep-mb N] [--dry-run|--apply]
```

### analysis - Market Analysis
```bash
uv run kalshi analysis calibration [--db PATH] [--days 30] [--output FILE]
uv run kalshi analysis metrics TICKER [--db PATH]
uv run kalshi analysis correlation [--db PATH] [--event EVT] [--tickers T1,T2] [--min 0.5] [--top 10]
```

---

## Critical Rules

1. **NO `--search` option exists** on any command. Query database directly instead.
2. **Use `--full/-F`** to disable CLI truncation; if you still need exact tickers, query the database.
3. **Always use `uv run kalshi`** prefix - commands require virtual environment.
4. **Check `--help`** before assuming options exist.
5. **`news track` defaults to 2 queries** (title + title + "news"), so `news collect` usually makes 2 Exa calls per tracked item.
6. **Cost warning**: `research deep` (and `research thesis create --with-research`) can incur Exa API costs.

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
