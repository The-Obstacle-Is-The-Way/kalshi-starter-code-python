# Common Workflows

Step-by-step guides for common tasks.

---

## CRITICAL: Research Workflow (Follow This Order!)

When researching markets for recommendations, follow this exact order to avoid catastrophic errors:

### Step 1: Check User's Portfolio First

```bash
# What does user already own?
uv run kalshi portfolio history -n 50
# or
sqlite3 data/kalshi.db "SELECT DISTINCT ticker, side FROM trades"
```

**Exclude these tickers from new recommendations.**

### Step 2: Get Market Details INCLUDING Open Time

```bash
uv run kalshi market get TICKER
```

**Important**: `market get` does **not** currently display `open_time` / `created_time` (see SPEC-025).

**Workaround (use SQLite)**:
```bash
# Ensure market metadata is current
uv run kalshi data sync-markets

# DB columns: open_time, created_at, close_time
sqlite3 data/kalshi.db "SELECT open_time, created_at, close_time FROM markets WHERE ticker = 'TICKER'"
```

Use `market get` for current prices/volume and `markets.open_time` for timing validation.

### Step 3: Temporal Validation (CRITICAL)

Ask yourself:
- When did the market open?
- Is the event I'm researching AFTER the open time?
- If market opened recently, events before that DON'T count

**Example**: Market opened Jan 5, 2026. An event from Dec 2025 does NOT satisfy "Will X happen before Y?" because the event predates the market.

### Step 4: Run Exa Research

```bash
# Only research events AFTER market open_time
uv run kalshi research context TICKER
# or
uv run kalshi research topic "your research question"
```

### Step 5: Cross-Validate Price vs Research

If your research says "obvious YES" but price is 10-15%:
1. **STOP** - something is wrong
2. Re-check market timing
3. Re-read market rules carefully
4. Check for ambiguity in resolution criteria

**Rule**: If research and price disagree, investigate. Don't assume the market is wrong.

### Step 6: Make Recommendation

Only after all validation passes, make your recommendation with:
- Confidence level
- Key risks
- What could invalidate the thesis

---

## Ticker Discovery Workflow

Kalshi tickers are unpredictable. Don't guess.

### Option 1: Search Database (if synced)

```bash
# Sync markets first (if not done recently)
uv run kalshi data sync-markets

# Search by keyword
sqlite3 data/kalshi.db "SELECT ticker, title FROM markets WHERE title LIKE '%keyword%' AND status = 'active'"

# Search by partial ticker
sqlite3 data/kalshi.db "SELECT ticker, title FROM markets WHERE ticker LIKE 'KXFED%'"
```

### Option 2: Use Kalshi Website

1. Go to kalshi.com
2. Find the market you want
3. The ticker is often in the URL: `kalshi.com/markets/.../TICKER-HERE`
4. If `market get` returns 404, the URL may be an **event** page (not a single market ticker):
   - Use the event ticker from the page (or from `market get` output on a related market)
   - Run `uv run kalshi market list --event EVENT_TICKER --limit 50` and pick a real market ticker

### Option 3: List Markets by Event

```bash
uv run kalshi market list --event EVENT_TICKER --limit 50
```

---

## Initial Setup

### First-Time Database Setup

```bash
# 1. Initialize database tables
uv run kalshi data init

# 2. Sync markets from Kalshi API
uv run kalshi data sync-markets

# 3. Take initial price snapshot
uv run kalshi data snapshot

# 4. Verify setup
uv run kalshi data stats
```

### Configure Authentication (for Portfolio)

```bash
# Set environment variables
export KALSHI_KEY_ID="your-key-id"
export KALSHI_PRIVATE_KEY_PATH="/path/to/private-key.pem"
# OR use base64-encoded key:
export KALSHI_PRIVATE_KEY_B64="base64-encoded-key"

# Optional: Set environment
export KALSHI_ENVIRONMENT="prod"  # or "demo"
```

---

## Portfolio Sync & Thesis Tracking

### Sync Portfolio and View Trades

```bash
# 1. Sync trades and positions from Kalshi API
uv run kalshi portfolio sync

# 2. View trade history
uv run kalshi portfolio history -n 50

# 3. View current positions
uv run kalshi portfolio positions

# 4. View P&L summary
uv run kalshi portfolio pnl

# 5. View account balance
uv run kalshi portfolio balance
```

### Create Thesis for Open Position

```bash
# 1. Get the exact ticker from your trades
sqlite3 data/kalshi.db "SELECT DISTINCT ticker FROM trades"

# 2. Get current market price
uv run kalshi market get KXSB-26-DEN

# 3. Create thesis with your prediction
uv run kalshi research thesis create "Denver wins Super Bowl" \
  -m KXSB-26-DEN \
  --your-prob 0.18 \
  --market-prob 0.13 \
  --confidence 0.70 \
  --bull "Strong defense, experienced QB" \
  --bear "Tough playoff path, injuries"

# 4. Link position to thesis
uv run kalshi portfolio link KXSB-26-DEN --thesis <THESIS_ID>
```

### Track Thesis Outcomes

```bash
# 1. List all theses
uv run kalshi research thesis list

# 2. View thesis details
uv run kalshi research thesis show <THESIS_ID> --with-positions

# 3. When market resolves, record outcome
uv run kalshi research thesis resolve <THESIS_ID> --outcome yes

# 4. Run backtest to see calibration
uv run kalshi research backtest --start 2024-01-01 --end 2025-12-31
```

---

## Exa-Powered Research

Requires `EXA_API_KEY` (set in your environment or `.env`).

### Market Context Research (Per Ticker)

```bash
# Research the market using Exa sources (news + papers)
uv run kalshi research context KXFEDCHAIRNOM-29-KW --days 30 --max-news 10 --max-papers 5

# JSON output for downstream tooling
uv run kalshi research context KXFEDCHAIRNOM-29-KW --json
```

### Topic Research / Thesis Ideation

```bash
# Research a question or topic
uv run kalshi research topic "Will the Fed cut rates in 2026?"

# Skip summary generation (faster/cheaper)
uv run kalshi research topic "Will the Fed cut rates in 2026?" --no-summary

# JSON output
uv run kalshi research topic "Will the Fed cut rates in 2026?" --json
```

---

## News Monitoring & Sentiment

Requires `EXA_API_KEY`.

### Track → Collect → Sentiment

```bash
# 1. Track a market (defaults to 2 queries: title + "title news")
uv run kalshi news track KXFEDCHAIRNOM-29-KW

# Or track an event
uv run kalshi news track KXFEDCHAIRNOM-29 --event

# Or provide custom queries
uv run kalshi news track KXFEDCHAIRNOM-29-KW --queries "Powell nominee, Fed chair nominee"

# 2. Collect news + run sentiment
uv run kalshi news collect

# Collect only for one tracked item
uv run kalshi news collect --ticker KXFEDCHAIRNOM-29-KW

# 3. View sentiment summary
uv run kalshi news sentiment KXFEDCHAIRNOM-29-KW --days 7
```

### Housekeeping

```bash
# List tracked items
uv run kalshi news list-tracked
uv run kalshi news list-tracked --all

# Stop tracking
uv run kalshi news untrack KXFEDCHAIRNOM-29-KW
```

---

## Finding Markets

### Search for Markets (No --search Exists!)

Since CLI has no search option, use database queries:

```bash
# Find by keyword in title
sqlite3 data/kalshi.db "SELECT ticker, title FROM markets WHERE title LIKE '%Super Bowl%' AND status = 'open'"

# Find by partial ticker
sqlite3 data/kalshi.db "SELECT ticker, title FROM markets WHERE ticker LIKE 'KXFED%'"

# Find by category
sqlite3 data/kalshi.db "SELECT ticker, title FROM markets WHERE category = 'Politics' AND status = 'active' LIMIT 20"

# Then use exact ticker with CLI
uv run kalshi market get KXSB-26-DEN
```

### Get Market Details

```bash
# Basic market info
uv run kalshi market get KXSB-26-DEN

# Orderbook with depth
uv run kalshi market orderbook KXSB-26-DEN --depth 10

# List markets for an event
uv run kalshi market list --event KXSB-26 --limit 50
```

---

## Opportunity Scanning

### Find Close Races

```bash
# Markets with prices near 50%
uv run kalshi scan opportunities --filter close-race --top 20

# With volume filter (reduce noise)
uv run kalshi scan opportunities --filter close-race --min-volume 1000 --top 10
```

### Find Arbitrage Opportunities

```bash
# Sync historical data first
uv run kalshi data sync-markets
uv run kalshi data snapshot

# Find correlated markets with divergence
uv run kalshi scan arbitrage --threshold 0.05 --top 20
```

### Track Price Movers

```bash
# Need historical snapshots first
uv run kalshi data collect --once

# Find biggest movers
uv run kalshi scan movers --period 24h --top 20
uv run kalshi scan movers --period 1h --top 10
```

---

## Continuous Data Collection

### Background Collection

```bash
# Run continuously (every 15 minutes)
uv run kalshi data collect --interval 15

# Single sync and exit
uv run kalshi data collect --once
```

### Alert Monitoring

```bash
# Add price alerts
uv run kalshi alerts add price KXSB-26-DEN --above 0.20
uv run kalshi alerts add price KXSB-26-DEN --below 0.10

# Add volume/spread alerts
uv run kalshi alerts add volume KXSB-26-DEN --above 5000
uv run kalshi alerts add spread KXSB-26-DEN --above 5

# Start monitoring
uv run kalshi alerts monitor

# Or run in background
uv run kalshi alerts monitor --daemon

# One-time check
uv run kalshi alerts monitor --once
```

---

## Analysis & Calibration

### Analyze Market Calibration

```bash
# Sync settlements first
uv run kalshi data sync-settlements

# Run calibration analysis
uv run kalshi analysis calibration --days 90 --output calibration.json

# View Brier scores and reliability
cat calibration.json | python -m json.tool
```

### Correlation Analysis

```bash
# Need price history
uv run kalshi data collect --once

# Find correlated markets
uv run kalshi analysis correlation --min 0.7 --top 20

# Analyze specific tickers
uv run kalshi analysis correlation --tickers KXSB-26-DEN,KXSB-26-KC

# Filter by event
uv run kalshi analysis correlation --event KXSB-26
```

### Market Metrics

```bash
# Get metrics for a specific market
uv run kalshi analysis metrics KXSB-26-DEN
```

---

## Data Export

### Export for Analysis

```bash
# Export to Parquet (default)
uv run kalshi data export

# Export to CSV
uv run kalshi data export --format csv

# Custom output directory
uv run kalshi data export --output /path/to/exports --format parquet
```

### Work with Exported Data

```python
# Python example with Parquet
import pandas as pd

snapshots = pd.read_parquet('data/exports/price_snapshots/')
markets = pd.read_parquet('data/exports/markets.parquet')
```

---

## Troubleshooting Workflows

### When Positions Table is Empty

If `kalshi portfolio sync` shows 0 positions but you have trades:

```bash
# 1. Check trades exist
sqlite3 data/kalshi.db "SELECT COUNT(*) FROM trades"

# 2. Calculate positions from trades
sqlite3 data/kalshi.db "SELECT ticker, side, SUM(CASE WHEN action='buy' THEN quantity ELSE -quantity END) as net FROM trades GROUP BY ticker, side HAVING net > 0"

# 3. Use trade data for thesis creation
```

### When Ticker Not Found

CLI display truncates long tickers. Get full ticker from database:

```bash
# Search for partial match
sqlite3 data/kalshi.db "SELECT ticker FROM markets WHERE ticker LIKE 'KXFED%'"

# Use full ticker
uv run kalshi market get KXFEDCHAIRNOM-29-KW
```

### When API Returns 404

The ticker might not exist or market might be closed:

```bash
# Check market status in database
sqlite3 data/kalshi.db "SELECT ticker, status, result FROM markets WHERE ticker = 'KXSB-26-DEN'"

# Re-sync markets
uv run kalshi data sync-markets
```
