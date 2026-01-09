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

## data - Data Management

### data init
Initialize the database with required tables.

```bash
uv run kalshi data init [--db PATH]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |

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

### data sync-settlements
Sync settled market outcomes from Kalshi API to database.

```bash
uv run kalshi data sync-settlements [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |
| `--max-pages` | None | Pagination safety limit |

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
| `--status`, `-s` | `open` | Filter by status: open, closed, etc. |
| `--event`, `-e` | None | Filter by event ticker |
| `--limit`, `-n` | `20` | Maximum number of results |

**IMPORTANT**: There is NO `--search` or `--query` option. Use database queries instead.

### market orderbook
Fetch orderbook for a market.

```bash
uv run kalshi market orderbook TICKER [OPTIONS]
```

| Argument/Option | Default | Description |
|-----------------|---------|-------------|
| `TICKER` | Required | Market ticker |
| `--depth`, `-d` | `5` | Orderbook depth (levels) |

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
| `--top`, `-n` | `10` | Number of results |
| `--min-volume` | `0` | Minimum 24h volume (close-race only) |
| `--max-spread` | `100` | Maximum bid-ask spread in cents (close-race only) |
| `--max-pages` | None | Pagination safety limit |

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

### research thesis list
List all theses.

```bash
uv run kalshi research thesis list
```

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

### research backtest
Run backtests on resolved theses using historical settlements.

```bash
uv run kalshi research backtest --start DATE --end DATE [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--start` | Required | Start date (YYYY-MM-DD) |
| `--end` | Required | End date (YYYY-MM-DD) |
| `--thesis`, `-t` | None | Specific thesis ID (default: all resolved) |
| `--db`, `-d` | `data/kalshi.db` | Path to SQLite database file |

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
| `ALERT_TYPE` | Required | Type: `price`, `volume`, `spread` |
| `TICKER` | Required | Market ticker to monitor |
| `--above` | None | Trigger when above threshold |
| `--below` | None | Trigger when below threshold |

**Note**: `volume` and `spread` only support `--above`.

### alerts remove
Remove an alert by ID.

```bash
uv run kalshi alerts remove ALERT_ID
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
