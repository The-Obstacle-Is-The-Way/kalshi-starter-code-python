# Market Scanner (Explanation)

The scanner automatically finds opportunities across all Kalshi markets instead of you manually browsing.

It applies filters and heuristics to surface markets worth investigating.

## Scanner Types

### 1. Close Races

Markets priced between 40-60% - the "coin flip" zone where edge has the most value.

**Why this matters:**

- A 50/50 market has maximum uncertainty
- If you have real information, your edge is worth more here
- A 5% edge on a 50% market is worth more than 5% edge on a 95% market (Kelly criterion)

```bash
uv run kalshi scan opportunities --filter close-race --top 10
```

**Filter logic:**

```python
mid_prob = (yes_bid_cents + yes_ask_cents) / 200.0
is_close_race = 0.40 <= mid_prob <= 0.60
```

### 2. High Volume

Markets with significant trading activity - these have liquidity and market attention.

**Why this matters:**

- Liquid markets have tighter spreads (cheaper to trade)
- High volume often means important events
- Price discovery is better in liquid markets

```bash
uv run kalshi scan opportunities --filter high-volume --top 10
```

**Filter logic:**

```python
# Default threshold (not currently configurable via CLI): volume_24h >= 10,000
high_volume = [m for m in markets if m.volume_24h >= 10_000]
sorted_by_volume = sorted(high_volume, key=lambda m: m.volume_24h, reverse=True)
```

### 3. Wide Spread

Markets with large bid-ask spreads - potential opportunities for patient traders.

**Why this matters:**

- Wide spreads mean market makers are uncertain
- If you have conviction, you might get good fills
- Can also indicate illiquidity (trade carefully)

```bash
uv run kalshi scan opportunities --filter wide-spread --top 10
```

**Filter logic:**

```python
spread = yes_ask - yes_bid
is_wide_spread = spread >= threshold  # default: 5 cents (fixed in code today)
```

### 4. Expiring Soon

Markets closing within a time window - resolution is imminent.

**Why this matters:**

- Last chance to trade before settlement
- Late information advantages (you might know outcome before market)
- Prices should converge to 0 or 100

```bash
uv run kalshi scan opportunities --filter expiring-soon --top 10
```

**Filter logic:**

```python
time_remaining = close_time - now
is_expiring_soon = time_remaining <= threshold  # e.g., 24 hours
```

### 5. Movers

Markets that moved significantly since a previous snapshot.

**Why this matters:**

- Large moves indicate new information
- Might be overreaction (mean reversion opportunity)
- Or might be underreaction (momentum opportunity)

```bash
uv run kalshi scan movers --period 1h --top 10
```

**Requires:** Price snapshots in database (run `kalshi data snapshot` periodically)

**Filter logic:**

```python
# Compare current price to snapshot from N hours ago
move = current_price - historical_price
abs_move = abs(move)
percent_move = abs_move / historical_price
```

### 6. Arbitrage

Inverse market pairs that don't sum to 100% - free money (in theory).

**Why this matters:**

- Two markets should sum to 100% if they're true inverses
- If TRUMP-YES + TRUMP-NO < 100%, you can buy both
- Profit = 100% - (cost of YES + cost of NO)

```bash
uv run kalshi scan arbitrage --threshold 0.10 --top 10
```

**Filter logic:**

```python
# Find inverse pairs (e.g., TRUMP-WIN vs TRUMP-LOSE)
for ticker_a, ticker_b in inverse_pairs:
    combined_cost = price_a + (1 - price_b)  # Cost to buy both YES
    if combined_cost < (1 - threshold):
        # Arbitrage opportunity: you pay less than 100%
        edge = 1 - combined_cost
```

**Caveats:**

- Transaction costs eat into edge
- Timing risk (prices move while you execute)
- Capital lockup (money tied until settlement)

## Output Format

Scanner results include:

```text
┌──────────────────┬───────┬────────┬────────┬──────────┐
│ Ticker           │ Price │ Volume │ Spread │ Score    │
├──────────────────┼───────┼────────┼────────┼──────────┤
│ TRUMP-2024       │ 52¢   │ 50,000 │ 2¢     │ 0.85     │
│ BIDEN-RESIGN     │ 48¢   │ 25,000 │ 3¢     │ 0.72     │
│ ...              │ ...   │ ...    │ ...    │ ...      │
└──────────────────┴───────┴────────┴────────┴──────────┘
```

## CLI Options

### Common Filters

```bash
--min-volume 1000    # Minimum 24h volume
--max-spread 10      # Maximum spread in cents
--max-pages 10       # Limit API pagination (safety cap)
--top 10             # Number of results to show
--min-liquidity 50   # Minimum liquidity score (0-100; fetches orderbooks)
--show-liquidity     # Show liquidity score column (fetches orderbooks)
--liquidity-depth 25 # Orderbook depth for liquidity scoring
```

### Examples

```bash
# Close races with decent liquidity
uv run kalshi scan opportunities \
  --filter close-race \
  --min-volume 1000 \
  --max-spread 10 \
  --min-liquidity 50 \
  --top 10

# Big movers in the last hour
uv run kalshi scan movers \
  --period 1h \
  --top 10 \
  --db data/kalshi.db

# Arbitrage with at least 10% edge
uv run kalshi scan arbitrage \
  --threshold 0.10 \
  --db data/kalshi.db
```

## Architecture

```text
Kalshi API (public)
       │
       ▼
  MarketScanner
       │
  ┌────┴────┐
  ▼         ▼
Filter    Sort
  │         │
  └────┬────┘
       ▼
ScanResult[]
       │
       ▼
  CLI Table Output
```

## Database Integration

Some scans require historical data:

- **Movers**: Needs price snapshots to compare against
- **Arbitrage**: Can use cached market data for speed

Build up your database:

```bash
# Initial sync
uv run kalshi data init
uv run kalshi data sync-markets

# Take snapshots periodically
uv run kalshi data snapshot

# Or run continuous collection
uv run kalshi data collect --interval 15
```

## Key Code

- Scanner: `src/kalshi_research/analysis/scanner.py`
- CLI: `src/kalshi_research/cli/scan.py`

## Use Case: Daily Workflow

```bash
# Morning: What moved overnight?
uv run kalshi scan movers --period 12h --top 20

# Find close races worth researching
uv run kalshi scan opportunities --filter close-race --min-volume 5000 --top 10

# Check for arbitrage
uv run kalshi scan arbitrage --threshold 0.05 --top 10

# Take a snapshot for tomorrow's comparison
uv run kalshi data snapshot
```

## See Also

- [Alerts System](alerts-system.md) - Get notified when conditions are met
- [Usage: Scanning](../getting-started/usage.md#scanning) - CLI commands
- [Data Pipeline](../architecture/data-pipeline.md) - How snapshots work
