# Edge Cases & Gotchas

Things that can trip you up when using the Kalshi Research Platform.

---

## CRITICAL: Research Workflow Gotchas

### Market Open Time Matters (CATASTROPHIC if ignored)

**ALWAYS check `open_time` before researching time-sensitive markets.**

A market asking "Will X happen before Y?" only counts events AFTER the market opened. If you research an event that happened BEFORE the market opened, your recommendation will be WRONG.

**Example of catastrophic failure**:
- Market: "Will a new Stranger Things episode release before Jan 1, 2027?"
- Research found: S5 released Nov-Dec 2025
- AI concluded: "Easy YES, it already released"
- **MISSED**: Market opened Jan 5, 2026 - AFTER S5 finished
- The market asks about NEW content, not S5
- User lost money on flawed recommendation

**How to avoid**:
```bash
# ALWAYS check open_time FIRST
# NOTE: `market get` does not currently display open_time (SPEC-025 is planned).

# Ensure market metadata is current
uv run kalshi data sync-markets

# Fetch current prices/volume
uv run kalshi market get TICKER

# Get timing fields from SQLite
sqlite3 data/kalshi.db "SELECT open_time, created_at, close_time FROM markets WHERE ticker = 'TICKER'"

# If open_time is recent (e.g., last few weeks), ask:
# "Did the researched event happen AFTER this date?"
```

### Price Is Information (Don't Ignore It)

If market price suggests 10-15% probability but your research says "obvious YES", **STOP AND INVESTIGATE**.

Market participants are usually not dumb. If the price seems too easy:
1. You're missing something (like market timing)
2. There's ambiguity in the resolution criteria
3. The market knows something your research doesn't

**Rule**: If research says "easy money" but price says "unlikely", dig deeper.

### Check Portfolio Before Recommending

**ALWAYS check what user already owns before recommending new plays.**

```bash
# Before recommending, exclude owned positions
uv run kalshi portfolio history -n 50
# or
sqlite3 data/kalshi.db "SELECT DISTINCT ticker FROM trades"
```

When user asks for "new opportunities", they mean positions they DON'T already own.

---

## CLI Pitfalls

### NO Search Option Exists

The most common mistake. There is **no** `--search` or `--query` option on any command.

```bash
# WRONG - will fail
uv run kalshi market list --search "Super Bowl"

# RIGHT - query database
sqlite3 data/kalshi.db "SELECT ticker, title FROM markets WHERE title LIKE '%Super Bowl%'"
```

### Truncated Tickers in CLI Output

CLI display truncates long tickers with `...`:

```
KXFEDCHAIRNOM-29-...  # Displayed
KXFEDCHAIRNOM-29-KW   # Actual
```

Always get full tickers from database before using them.

### Ticker Discovery Is Hard

Kalshi tickers follow **no consistent naming pattern**. Don't guess tickers - you'll get 404s.

```bash
# WRONG - guessing tickers
uv run kalshi market get CONTROLS-2026      # 404
uv run kalshi market get KXCONTROLS-2026    # 404
uv run kalshi market get KXCONTROLS-26      # 404

# RIGHT - find actual ticker
# Option 1: Check database (if synced)
sqlite3 data/kalshi.db "SELECT ticker FROM markets WHERE title LIKE '%Senate%control%'"

# Option 2: Use Kalshi website to find exact ticker
# Option 3: Sync markets first, then search database
uv run kalshi data sync-markets
```

If `market get` 404s for something you found on kalshi.com, it may be an **event** slug, not a single market ticker. Use `market list --event EVENT_TICKER` to find real market tickers.

Avoid relying on “ticker patterns” — they are not stable.

### market list Status Filter Confusion (open vs active)

- `kalshi market list --status` expects filter values like `open` (see `kalshi market list --help`).
- The API/DB `Market.status` uses lifecycle values like `active`.
- `uv run kalshi market list --status active` returns a 400 (`invalid status filter`) and currently prints a full traceback.

**Workaround**:
```bash
uv run kalshi market list --status open --limit 20
# For local search, use DB status values:
sqlite3 data/kalshi.db "SELECT ticker, title FROM markets WHERE status = 'active' LIMIT 20"
```

### uv run Prefix Required

Commands must use `uv run kalshi` prefix - the virtual environment is required.

```bash
# WRONG
kalshi data stats

# RIGHT
uv run kalshi data stats
```

### Portfolio Link Uses TICKER, Not POSITION_ID

```bash
# WRONG
uv run kalshi portfolio link 123 abc-thesis-id

# RIGHT
uv run kalshi portfolio link KXSB-26-DEN --thesis abc-thesis-id
```

---

## API & Data Gotchas

### Prices Are in Cents (1-100 Scale)

All prices are stored as integers 1-100, not decimals 0.01-1.00:

```sql
-- This means 65 cents, NOT 65%
yes_bid: 65

-- Convert to probability
SELECT yes_bid / 100.0 as probability FROM price_snapshots;
```

### Unpriced Markets (Bid=0 or Ask=100)

Markets with `yes_bid=0` and `yes_ask=100` are effectively unpriced placeholders. Skip them in analysis:

```sql
SELECT * FROM price_snapshots
WHERE NOT (yes_bid = 0 AND yes_ask = 100)
  AND NOT (yes_bid = 0 AND yes_ask = 0);
```

### Negative Liquidity from API (BUG-048)

Kalshi API sometimes returns negative liquidity values (e.g., `-170750`). Our Pydantic model validates `liquidity >= 0` and will crash.

**Workaround**: Use `--max-pages` to limit pagination when scanning:
```bash
# This may crash without --max-pages
uv run kalshi scan opportunities --filter close-race

# This is safer
uv run kalshi scan opportunities --filter close-race --max-pages 5
```

### FIFO Cost Basis Calculation

Position cost basis uses strict FIFO (First-In-First-Out):
- Buy orders add lots to a queue
- Sell orders consume from front of queue
- Average is computed from remaining lots

This is the IRS-standard method but may differ from your intuition.

### Positions Table May Be Empty

The API sometimes returns empty positions even when trades exist. Workaround:

```sql
-- Calculate positions from trades
SELECT
  ticker,
  side,
  SUM(CASE WHEN action='buy' THEN quantity ELSE -quantity END) as net_qty
FROM trades
GROUP BY ticker, side
HAVING net_qty > 0;
```

---

## Rate Limiting

### Token Bucket Algorithm

The client uses token bucket rate limiting with configurable tiers:

| Tier | Read/min | Write/min |
|------|----------|-----------|
| BASIC | 20 | 10 |
| ADVANCED | 30 | 30 |
| PREMIER | 100 | 100 |
| PRIME | 400 | 400 |

Set via `KALSHI_RATE_TIER` environment variable or `--rate-tier` option.

### Safety Margin

The rate limiter uses 90% of limits by default to avoid hitting hard limits.

### Retry-After Headers

When rate limited, the client respects `Retry-After` headers from the API.

---

## Database Gotchas

### SQLite WAL Mode

Database uses WAL (Write-Ahead Logging) for concurrent access. May leave `.db-wal` and `.db-shm` files:

```
data/kalshi.db
data/kalshi.db-wal
data/kalshi.db-shm
```

Don't delete these while the database is open.

### DISTINCT ON Not Supported

SQLite doesn't support `DISTINCT ON`. Use subqueries instead:

```sql
-- WRONG (PostgreSQL syntax)
SELECT DISTINCT ON (ticker) * FROM price_snapshots ORDER BY snapshot_time DESC;

-- RIGHT (SQLite)
SELECT * FROM price_snapshots p1
WHERE snapshot_time = (
  SELECT MAX(snapshot_time) FROM price_snapshots p2 WHERE p2.ticker = p1.ticker
);
```

### Timestamps Are ISO 8601 Strings

Use SQLite datetime functions:

```sql
WHERE snapshot_time > datetime('now', '-24 hours')
WHERE executed_at > date('now', '-7 days')
```

---

## Thesis & Backtest Gotchas

### Theses Stored in JSON, Not Database

Theses are in `data/theses.json`, not the SQLite database:

```bash
# View theses directly
cat data/theses.json | python -m json.tool

# CLI commands
uv run kalshi research thesis list
```

### Backtest Requires Settlements

Backtesting only works on resolved theses with matching settlements:

```bash
# Sync settlements first
uv run kalshi data sync-settlements

# Then backtest
uv run kalshi research backtest --start 2024-01-01 --end 2025-12-31
```

### Thesis Statuses

- `DRAFT` - Not yet active
- `ACTIVE` - Currently tracking
- `RESOLVED` - Outcome recorded
- `ABANDONED` - Closed without resolution

### Edge Calculation

Edge = `your_probability - market_probability`

Positive edge means you think event is more likely than market.

---

## Alert Gotchas

### One-Shot Alerts Auto-Delete

Some alert conditions are removed after triggering once.

### Volume/Spread Only Support --above

```bash
# WRONG
uv run kalshi alerts add volume TICKER --below 100

# RIGHT
uv run kalshi alerts add volume TICKER --above 5000
```

### Daemon Mode Needs Manual Stop

```bash
# Start daemon
uv run kalshi alerts monitor --daemon

# Check if running
ps aux | grep "kalshi.*monitor"

# Stop manually
kill <PID>
```

---

## Environment Gotchas

### Demo vs Production

Demo and production use different:
- API endpoints
- Authentication
- Data (demo has test markets)

```bash
# Set globally
export KALSHI_ENVIRONMENT="demo"

# Or per-command
uv run kalshi --env demo portfolio balance
```

### Environment Variables Not in Inline Python

When running inline Python, environment variables may not be accessible. Use CLI commands instead.

---

## Exa & News Gotchas

### Missing `EXA_API_KEY`

These commands require `EXA_API_KEY` (set in your environment or `.env`):

- `kalshi research context ...`
- `kalshi research topic ...`
- `kalshi news collect ...`

If it’s missing, the CLI exits with an error explaining how to set it.

### `news track` Defaults to Two Queries

If you don’t pass `--queries`, `news track` creates two queries:

1. The item title (cleaned)
2. The title + `" news"`

That means `news collect` usually makes **two Exa /search calls per tracked item**.

### Exa Cache Is Safe to Delete (DB Is Not)

`data/exa_cache/` is only a cache for Exa topic research. Deleting it is safe (you’ll just lose cached results).

Do **not** delete `data/kalshi.db` to “fix” issues; see **Critical Anti-Patterns** below.

### Exa Calls Cost Money

Exa responses include `costDollars` on some endpoints. Prefer:

- smaller `--max-news`/`--max-papers` for `research context`
- caching (topic research uses `data/exa_cache/`)
- `--no-summary` for `research topic` when you only need sources

---

## Correlation Analysis Gotchas

### Minimum Sample Size

Correlation analysis requires at least 30 price snapshots per ticker for reliable results.

### Spurious Correlations

Markets with few trades or placeholder prices can show false correlations. Filter by volume:

```bash
uv run kalshi scan arbitrage --threshold 0.1 --tickers-limit 50
```

---

## Critical Anti-Patterns

### NEVER Delete the Database to "Fix" Issues

If the database appears corrupted or you encounter errors like `database disk image is malformed`:

**WRONG:**
```bash
rm data/kalshi.db  # DANGEROUS - destroys all data
uv run kalshi data init
```

**RIGHT:**
1. Diagnose the actual issue first
2. Check for WAL file issues: `ls data/kalshi.db*`
3. Try `sqlite3 data/kalshi.db "PRAGMA integrity_check;"`
4. If corrupted, attempt recovery: `sqlite3 data/kalshi.db ".recover" | sqlite3 data/recovered.db`
5. Back up before any destructive action

Deleting the database destroys:
- All synced markets/events
- All price snapshots (historical data)
- All tracked news items
- All sentiment analysis
- All portfolio positions and trades

This data may take hours to rebuild and some historical data is unrecoverable.

---



### "not found" (404)

Market doesn't exist or ticker is wrong. Get exact ticker from database.

### "unauthorized" (401)

Missing or invalid authentication. Check:
- `KALSHI_KEY_ID` is set
- Private key path/base64 is correct
- Key hasn't expired

### "rate limited" (429)

Too many requests. The client will auto-retry with exponential backoff. Consider upgrading rate tier.

### "No such option"

You're using a CLI option that doesn't exist. Run `--help` to see actual options.
