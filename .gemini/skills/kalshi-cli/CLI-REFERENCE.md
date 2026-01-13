# Complete CLI Reference

Every command with ALL available options. Verified directly from `--help` output.

---

## Main Command

```bash
uv run kalshi [OPTIONS] COMMAND
```

| Option | Description |
|--------|-------------|
| `--env`, `-e` | API environment: `prod` or `demo` (default: from `KALSHI_ENVIRONMENT` or `prod`) |

---

## Utility Commands

### version
Show version information.

```bash
uv run kalshi version [OPTIONS]
```

### status
Show Kalshi exchange operational status.

```bash
uv run kalshi status [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--json` | False | Output as JSON |

---

## data - Data Management

### data init
Initialize the database with required tables.

```bash
uv run kalshi data init [--db PATH]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |

### data migrate
Run Alembic schema migrations (upgrade to head).

```bash
uv run kalshi data migrate [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |
| `--dry-run` / `--apply` | `--dry-run` | Validate migrations on a temporary DB copy (dry-run) or apply to the DB |

### data sync-markets
Sync markets from Kalshi API to database.

```bash
uv run kalshi data sync-markets [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |
| `--status`, `-s` | None | Filter by status (open, closed, etc.) |
| `--max-pages` | None | Pagination safety limit (None = all) |
| `--mve-filter` | None | Filter multivariate events: `exclude` (skip sports parlays) or `only` |

### data sync-settlements
Sync settled market outcomes from Kalshi API to database.

```bash
uv run kalshi data sync-settlements [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |
| `--max-pages` | None | Pagination safety limit |

### data sync-trades
Fetch public trade history from Kalshi (GET /markets/trades).

```bash
uv run kalshi data sync-trades [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--ticker` | None | Optional market ticker filter |
| `--limit` | `100` | Max trades to fetch (Kalshi caps at 1000) |
| `--min-ts` | None | Filter: min Unix timestamp (seconds) |
| `--max-ts` | None | Filter: max Unix timestamp (seconds) |
| `--output`, `-o` | None | Write results to a CSV file |
| `--json` | False | Output results as JSON to stdout |

### data snapshot
Take a price snapshot of all markets.

```bash
uv run kalshi data snapshot [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |
| `--status` | `open` | Filter by market status |
| `--max-pages` | None | Pagination safety limit |

### data collect
Run continuous data collection.

```bash
uv run kalshi data collect [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |
| `--interval`, `-i` | `15` | Interval in minutes between snapshots |
| `--once` | False | Run single sync and exit |
| `--max-pages` | None | Pagination safety limit |

### data export
Export data to Parquet or CSV for analysis.

```bash
uv run kalshi data export [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |
| `--output`, `-o` | `data/exports` | Output directory |
| `--format`, `-f` | `parquet` | Export format: `parquet` or `csv` |

### data stats
Show database statistics.

```bash
uv run kalshi data stats [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |

### data prune
Prune old rows to keep the database manageable.

```bash
uv run kalshi data prune [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |
| `--snapshots-older-than-days` | None | Delete price snapshots older than N days |
| `--news-older-than-days` | None | Delete collected news articles older than N days (by collected_at) |
| `--dry-run` / `--apply` | `--dry-run` | Preview deletions or apply changes |

### data vacuum
Run SQLite VACUUM to reclaim disk space after large deletes.

```bash
uv run kalshi data vacuum [--db PATH]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |

---

## market - Market Lookup

### market get
Fetch a single market by ticker.

```bash
uv run kalshi market get TICKER
```

| Argument | Required | Description |
|----------|----------|-------------|
| `TICKER` | Yes | Exact market ticker |

### market list
List markets with optional filters.

```bash
uv run kalshi market list [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--status`, `-s` | `open` | Filter by status: `unopened`, `open`, `paused`, `closed`, `settled` |
| `--event`, `-e` | None | Filter by event ticker |
| `--category`, `-c` | None | Filter by category (e.g. Politics, Economics, 'Science and Technology'); aliases: `pol`, `econ`, `tech`, `ai`, `crypto`, `climate` |
| `--exclude-category`, `-X` | None | Exclude a category (e.g. `--exclude-category Sports`) |
| `--event-prefix` | None | Filter by event ticker prefix (e.g. `KXFED`) |
| `--limit`, `-n` | `20` | Maximum number of results |
| `--full`, `-F` | False | Show full tickers/titles without truncation |

**IMPORTANT**: There is NO `--search` or `--query` option. Use database queries instead.

Note: `active` is a **response** status (not a filter). The CLI treats `--status active` as `open` with a warning.

### market orderbook
Fetch orderbook for a market.

```bash
uv run kalshi market orderbook TICKER [OPTIONS]
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `TICKER` | Required | Market ticker |
| `--depth`, `-d` | `5` | Orderbook depth (levels) |

### market liquidity
Analyze liquidity using orderbook depth + slippage estimates.

```bash
uv run kalshi market liquidity TICKER [OPTIONS]
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `TICKER` | Required | Market ticker |
| `--depth`, `-d` | `25` | Orderbook depth levels to fetch for analysis |
| `--max-slippage-cents` | `3` | Max slippage (cents) for the "max safe size" calculation |

### market history
Fetch candlestick history for a market.

```bash
uv run kalshi market history TICKER [OPTIONS]
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `TICKER` | Required | Market ticker to fetch candlesticks for |
| `--series` | None | Optional series ticker (uses series candlesticks endpoint) |
| `--interval`, `-i` | `1h` | Candle interval: `1m`, `1h`, `1d` |
| `--days` | `7` | Lookback window in days (used when `--start-ts` is not set) |
| `--start-ts` | None | Start timestamp (Unix seconds) |
| `--end-ts` | None | End timestamp (Unix seconds; defaults to now) |
| `--json` | False | Output as JSON |

---

## scan - Market Scanning

### scan opportunities
Scan markets for opportunities.

```bash
uv run kalshi scan opportunities [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--filter`, `-f` | None | Filter type: `close-race`, `high-volume`, `wide-spread`, `expiring-soon` |
| `--category`, `-c` | None | Filter by category |
| `--no-sports` | False | Exclude Sports category markets |
| `--event-prefix` | None | Filter by event ticker prefix (e.g. `KXFED`) |
| `--top`, `-n` | `10` | Number of results |
| `--min-volume` | `0` | Minimum 24h volume (close-race only) |
| `--max-spread` | `100` | Maximum bid-ask spread in cents (close-race only) |
| `--max-pages` | None | Optional pagination safety limit (None = full) |
| `--min-liquidity` | None | Minimum liquidity score (0-100); fetches orderbooks for candidates |
| `--show-liquidity` | False | Show liquidity score column; fetches orderbooks for displayed markets |
| `--liquidity-depth` | `25` | Orderbook depth levels for liquidity scoring |
| `--full`, `-F` | False | Show full tickers/titles without truncation |

### scan arbitrage
Find arbitrage opportunities from correlated markets.

```bash
uv run kalshi scan arbitrage [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |
| `--threshold` | `0.1` | Min divergence to flag (0-1) |
| `--top`, `-n` | `10` | Number of results |
| `--tickers-limit` | `50` | Limit correlation analysis to N tickers (0 = all) |
| `--max-pages` | None | Pagination safety limit |
| `--full`, `-F` | False | Show full tickers/relationships without truncation |

### scan movers
Show biggest price movers over a time period.

```bash
uv run kalshi scan movers [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |
| `--period`, `-p` | `24h` | Time period: `1h`, `6h`, `24h` |
| `--top`, `-n` | `10` | Number of results |
| `--max-pages` | None | Pagination safety limit |
| `--full`, `-F` | False | Show full titles without truncation |

---

## portfolio - Portfolio Tracking

**Requires authentication**: Set `KALSHI_KEY_ID` and either `KALSHI_PRIVATE_KEY_PATH` or `KALSHI_PRIVATE_KEY_B64`.

### portfolio sync
Sync positions and trades from Kalshi API.

```bash
uv run kalshi portfolio sync [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |
| `--env` | From global | Override environment (demo/prod) |
| `--rate-tier` | `basic` | API rate limit tier |
| `--skip-mark-prices` | False | Skip fetching current prices (faster) |

### portfolio positions
View current positions.

```bash
uv run kalshi portfolio positions [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |
| `--ticker`, `-t` | None | Filter by specific ticker |

### portfolio pnl
View profit & loss summary.

```bash
uv run kalshi portfolio pnl [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |
| `--ticker`, `-t` | None | Filter by specific ticker |

### portfolio balance
View account balance.

```bash
uv run kalshi portfolio balance [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--env` | From global | Override environment |
| `--rate-tier` | `basic` | API rate limit tier |

### portfolio history
View trade history.

```bash
uv run kalshi portfolio history [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |
| `--limit`, `-n` | `20` | Number of trades to show |
| `--ticker`, `-t` | None | Filter by specific ticker |

### portfolio link
Link a position to a thesis.

```bash
uv run kalshi portfolio link TICKER --thesis THESIS_ID [OPTIONS]
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `TICKER` | Required | Market ticker to link |
| `--thesis` | Required | Thesis ID to link to |
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |

### portfolio suggest-links
Suggest thesis-position links based on matching tickers.

```bash
uv run kalshi portfolio suggest-links [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |

---

## research - Research & Thesis Tracking

### research thesis create
Create a new research thesis.

```bash
uv run kalshi research thesis create "TITLE" [OPTIONS]
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `TITLE` | Required | Thesis title |
| `--markets`, `-m` | Required | Comma-separated market tickers |
| `--your-prob` | Required | Your probability (0-1) |
| `--market-prob` | Required | Market probability (0-1) |
| `--confidence` | Required | Your confidence (0-1) |
| `--bull` | "Why YES" | Bull case reasoning |
| `--bear` | "Why NO" | Bear case reasoning |
| `--with-research` | False | Attach Exa research evidence to this thesis (requires `EXA_API_KEY`) |
| `--yes`, `-y` | False | Accept research suggestions without prompting (only relevant with `--with-research`) |

### research thesis list
List all theses.

```bash
uv run kalshi research thesis list [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--full`, `-F` | False | Show full thesis IDs/titles without truncation |

### research thesis show
Show details of a thesis.

```bash
uv run kalshi research thesis show THESIS_ID [OPTIONS]
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `THESIS_ID` | Required | Thesis ID to show |
| `--with-positions` | False | Show linked positions |
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |

### research thesis resolve
Resolve a thesis with an outcome.

```bash
uv run kalshi research thesis resolve THESIS_ID --outcome OUTCOME
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `THESIS_ID` | Required | Thesis ID to resolve |
| `--outcome` | Required | Outcome: `yes`, `no`, or `void` |

### research thesis check-invalidation
Check for signals that might invalidate your thesis.

```bash
uv run kalshi research thesis check-invalidation THESIS_ID [OPTIONS]
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `THESIS_ID` | Required | Thesis ID to check |
| `--hours`, `-h` | `48` | Lookback hours |

### research thesis suggest
Generate thesis ideas from Exa research.

```bash
uv run kalshi research thesis suggest [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--category`, `-c` | None | Optional category filter (crypto, politics, etc.) |

### research backtest
Run backtests on resolved theses using historical settlements.

```bash
uv run kalshi research backtest --start DATE --end DATE [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--start` | Required | Start date (YYYY-MM-DD) |
| `--end` | Required | End date (YYYY-MM-DD, inclusive) |
| `--thesis`, `-t` | None | Specific thesis ID (default: all resolved) |
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |

---

### research context
Research context for a specific market using Exa.

```bash
uv run kalshi research context TICKER [OPTIONS]
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `TICKER` | Required | Market ticker to research |
| `--max-news` | `10` | Max news articles |
| `--max-papers` | `5` | Max research papers |
| `--days` | `30` | News recency in days |
| `--json` | False | Output as JSON |

Requires `EXA_API_KEY`.

### research topic
Research a topic for thesis ideation using Exa.

```bash
uv run kalshi research topic TOPIC [OPTIONS]
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `TOPIC` | Required | Topic or question to research |
| `--no-summary` | False | Skip summary generation |
| `--json` | False | Output as JSON |

Requires `EXA_API_KEY`.

### research similar
Find pages similar to a URL using Exa's /findSimilar endpoint.

```bash
uv run kalshi research similar [OPTIONS] URL
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `URL` | Required | Seed URL to find similar pages for |
| `--num-results`, `-n` | `10` | Number of results |
| `--json` | False | Output as JSON |

Requires `EXA_API_KEY`.

### research deep
Run Exa async deep research via /research/v1 (paid API).

```bash
uv run kalshi research deep [OPTIONS] TOPIC
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `TOPIC` | Required | Topic or question for deep research |
| `--model` | `exa-research` | Exa research model tier: `exa-research-fast`, `exa-research`, `exa-research-pro` |
| `--wait` | False | Wait for completion and print results (incurs additional Exa cost) |
| `--poll-interval` | `5.0` | Polling interval in seconds (when `--wait`) |
| `--timeout` | `300.0` | Timeout in seconds (when `--wait`) |
| `--schema` | None | Optional JSON schema file for structured output |
| `--json` | False | Output as JSON |

Requires `EXA_API_KEY`.

### research cache clear
Clear Exa response cache entries on disk.

```bash
uv run kalshi research cache clear [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--all` | False | Clear all cache entries (default: clear expired only) |
| `--cache-dir` | None | Override cache directory (default: data/exa_cache/) |

---

## news - News Monitoring & Sentiment

### news track
Start tracking news for a market or event.

```bash
uv run kalshi news track TICKER [OPTIONS]
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `TICKER` | Required | Market or event ticker |
| `--event`, `-e` | False | Treat ticker as an event ticker |
| `--queries`, `-q` | None | Comma-separated custom search queries |
| `--db`, `-d` | `data/kalshi.db` | Path to database |

### news untrack
Stop tracking a market/event.

```bash
uv run kalshi news untrack TICKER [OPTIONS]
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `TICKER` | Required | Market or event ticker |
| `--db`, `-d` | `data/kalshi.db` | Path to database |

### news list-tracked
List tracked markets/events.

```bash
uv run kalshi news list-tracked [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--all` | False | Include inactive tracked items |
| `--db`, `-d` | `data/kalshi.db` | Path to database |

### news collect
Collect news for tracked items and run sentiment analysis.

```bash
uv run kalshi news collect [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--ticker` | None | Collect only for this tracked ticker |
| `--lookback-days` | `7` | Days to look back |
| `--max-per-query` | `25` | Max articles per query |
| `--db`, `-d` | `data/kalshi.db` | Path to database |

Requires `EXA_API_KEY`.

### news sentiment
Show a sentiment summary for a market/event.

```bash
uv run kalshi news sentiment TICKER [OPTIONS]
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `TICKER` | Required | Market (or event) ticker |
| `--event`, `-e` | False | Treat as event ticker |
| `--days` | `7` | Days to analyze |
| `--db`, `-d` | `data/kalshi.db` | Path to database |

---

## alerts - Alert Management

### alerts list
List all active alerts.

```bash
uv run kalshi alerts list
```

### alerts add
Add a new alert condition.

```bash
uv run kalshi alerts add ALERT_TYPE TICKER [OPTIONS]
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `ALERT_TYPE` | Required | Type: `price`, `volume`, `spread`, `sentiment` |
| `TICKER` | Required | Market ticker to monitor |
| `--above` | None | Trigger when above threshold |
| `--below` | None | Trigger when below threshold |

**Note**: `volume`, `spread`, and `sentiment` only support `--above`.

### alerts remove
Remove an alert by ID prefix.

```bash
uv run kalshi alerts remove ALERT_ID_PREFIX
```

### alerts monitor
Start monitoring alerts.

```bash
uv run kalshi alerts monitor [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--interval`, `-i` | `60` | Check interval in seconds |
| `--daemon` | False | Run in background |
| `--once` | False | Single check cycle and exit |
| `--max-pages` | None | Pagination safety limit |
| `--output-file` | None | Write triggered alerts to a JSONL file (one alert per line) |
| `--webhook-url` | None | POST triggered alerts to a webhook URL (Slack/Discord style payload) |

### alerts trim-log
Trim the alerts monitor log to keep disk usage bounded.

```bash
uv run kalshi alerts trim-log [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--log` | `data/alert_monitor.log` | Path to the alerts monitor log file |
| `--max-mb` | `50` | Trim the log when it exceeds this many MB |
| `--keep-mb` | `5` | When trimming, keep the last N MB |
| `--dry-run` / `--apply` | `--dry-run` | Preview changes or apply trimming |

---

## analysis - Market Analysis

### analysis calibration
Analyze market calibration and Brier scores.

```bash
uv run kalshi analysis calibration [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |
| `--days` | `30` | Number of days to analyze |
| `--output`, `-o` | None | Output JSON file |

### analysis metrics
Calculate market metrics for a ticker.

```bash
uv run kalshi analysis metrics TICKER [OPTIONS]
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `TICKER` | Required | Market ticker |
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |

### analysis correlation
Analyze correlations between markets.

```bash
uv run kalshi analysis correlation [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |
| `--event`, `-e` | None | Filter by event ticker |
| `--tickers`, `-t` | None | Comma-separated tickers to analyze |
| `--min` | `0.5` | Minimum correlation threshold |
| `--top`, `-n` | `10` | Number of results |
