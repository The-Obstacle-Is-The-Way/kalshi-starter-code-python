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

Flags potential consistency / divergence opportunities across related markets.

**Why this matters:**

- Related markets often move together (or sum to ~100% when they represent two outcomes).
- If they diverge, it can signal mispricing or stale quotes.

```bash
uv run kalshi scan arbitrage --threshold 0.10 --top 10
```

This command does **not** place trades. It:

1. Uses historical **price snapshots** (if available in your DB) to find correlated market pairs and flags:
   - `divergence`: positively correlated pairs whose midpoint probabilities differ by more than `--threshold`.
   - `inverse_sum`: negatively correlated pairs whose midpoint probabilities no longer sum to ~100% within
     `--threshold`.
2. Always checks events with **exactly two priced markets** and flags `inverse_sum` when their midpoint probabilities
   deviate from 100% by more than `--threshold`.

Use `--tickers-limit` to bound how many tickers are included in the historical correlation analysis.

**Filter logic (simplified):**

In the implementation, `corr_type` is derived from historical correlation analysis of the two markets' midpoint
probabilities (from your local price snapshot history). It is the string value of `CorrelationType`
(`positive`, `negative`, `lead_lag`, or `none`) from `src/kalshi_research/analysis/correlation.py`.

```python
if corr_type == "positive" and abs(price_a - price_b) > threshold:
    opportunity_type = "divergence"

if corr_type == "negative" and abs((price_a + price_b) - 1.0) > threshold:
    opportunity_type = "inverse_sum"

if event_has_exactly_two_priced_markets and abs((p1 + p2) - 1.0) > threshold:
    opportunity_type = "inverse_sum"
```

**Caveats:**

- Transaction costs eat into edge
- Timing risk (prices move while you execute)
- Capital lockup (money tied until settlement)

## Output Format

Scanner commands print tables (exact columns depend on the command).

### Opportunities

```text
┌──────────────────┬──────────────────────┬─────────────┬────────┬─────────┐
│ Ticker           │ Title                │ Probability  │ Spread │ Volume  │
├──────────────────┼──────────────────────┼─────────────┼────────┼─────────┤
│ TRUMP-2024       │ ...                  │ 52.0%        │ 2¢     │ 50,000  │
│ ...              │ ...                  │ ...          │ ...    │ ...     │
└──────────────────┴──────────────────────┴─────────────┴────────┴─────────┘
```

### Arbitrage

```text
┌────────────────────────────┬────────────┬─────────────────────────┬───────────┬────────────┐
│ Tickers                     │ Type       │ Expected                │ Divergence │ Confidence │
├────────────────────────────┼────────────┼─────────────────────────┼───────────┼────────────┤
│ AAA, BBB                    │ divergence │ Move together (r=0.72)  │ 12.00%     │ 0.72       │
│ ...                         │ ...        │ ...                     │ ...        │ ...        │
└────────────────────────────┴────────────┴─────────────────────────┴───────────┴────────────┘
```

## CLI Options

Add `--full/-F` to disable truncation in table output.

### Opportunities

```bash
--min-volume 1000    # Minimum 24h volume
--max-spread 10      # Maximum spread in cents
--max-pages 10       # Optional pagination safety limit (omit for full)
--top 10             # Number of results to show
--category ai        # Filter by category (e.g. Politics, Economics, AI)
--no-sports          # Exclude Sports markets
--event-prefix KXFED # Filter by event ticker prefix
--min-liquidity 50   # Minimum liquidity score (0-100; fetches orderbooks)
--show-liquidity     # Show liquidity score column (fetches orderbooks)
--liquidity-depth 25 # Orderbook depth for liquidity scoring
--full               # Show full tickers/titles without truncation
```

### Arbitrage

```bash
--db data/kalshi.db      # DB used for historical correlation analysis (optional)
--threshold 0.10         # Min divergence to flag (0-1)
--tickers-limit 50       # Correlation analysis cap (0 = analyze all tickers)
--top 10                 # Number of results to show
--max-pages 10           # Optional pagination safety limit (omit for full)
--full                   # Show full tickers/relationships without truncation
```

### Examples

```bash
# Close races with decent liquidity
uv run kalshi scan opportunities \
  --filter close-race \
  --min-volume 1000 \
  --max-spread 10 \
  --min-liquidity 50 \
  --full \
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
