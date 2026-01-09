# Portfolio Tracking (Explanation)

The portfolio module syncs your actual Kalshi positions and trades, calculates P&L using FIFO cost basis, and tracks
performance over time.

This is where research meets reality - you can compare your actual trading results to your thesis predictions.

## Why Track Portfolio?

Without portfolio tracking:

- You don't know your actual P&L (Kalshi's UI is limited)
- You can't compare predictions to actual trades
- You can't measure if your research is making money
- No historical record of your trades

## Architecture

```text
Kalshi API (authenticated)
         │
         ▼
  PortfolioSyncer
         │
    ┌────┴────┐
    ▼         ▼
Positions   Fills (trades)
    │           │
    └─────┬─────┘
          ▼
    SQLite (portfolio tables)
          │
          ▼
    P&L Calculator (FIFO)
          │
          ▼
    Performance Metrics
```

## Authentication

Portfolio operations require API credentials:

```bash
# In .env file
KALSHI_KEY_ID=your-key-id
KALSHI_PRIVATE_KEY_PATH=/path/to/private_key.pem
# Or base64-encoded:
KALSHI_PRIVATE_KEY_B64=base64-encoded-key

KALSHI_ENVIRONMENT=demo  # or "prod"
```

The CLI loads `.env` automatically.

## Data Model

### Position

Current open position in a market:

```python
@dataclass
class Position:
    ticker: str              # Market ticker
    side: str                # "yes" or "no"
    quantity: int            # Number of contracts
    average_cost: float      # Average entry price (cents)
    market_price: float      # Current mark price
    unrealized_pnl: float    # Paper P&L
    thesis_id: str | None    # Optional link to thesis
```

### Trade

A filled order:

```python
@dataclass
class Trade:
    id: str                  # Kalshi trade ID
    ticker: str
    side: str                # "yes" or "no"
    action: str              # "buy" or "sell"
    price: float             # Fill price (cents)
    quantity: int
    timestamp: datetime
    fees: float
```

## FIFO Cost Basis

The P&L calculator uses **First In, First Out** accounting:

```text
Buy 10 @ 50c
Buy 10 @ 60c
Sell 10 @ 70c

FIFO: Sell 10 that were bought at 50c
P&L = (70 - 50) * 10 = 200c profit

Remaining position: 10 @ 60c average
```

This is the standard accounting method and matches what you'd report for taxes.

### Why FIFO Matters

Different methods give different P&L:

| Method | Description | P&L Calculation |
| ------ | ----------- | --------------- |
| FIFO   | Sell oldest first | Usually accurate for tax purposes |
| LIFO   | Sell newest first | Can defer gains |
| Average | Use average cost | Simpler but less precise |

We use FIFO because it's the standard and Kalshi uses it for tax reporting.

## Sync Process

When you run `kalshi portfolio sync`:

1. **Fetch fills**: Get all trades from Kalshi API
2. **Upsert trades**: Store in SQLite (idempotent)
3. **Calculate positions**: Aggregate trades per ticker
4. **Mark to market**: Fetch current prices (optional)
5. **Compute P&L**: FIFO calculation

```bash
uv run kalshi portfolio sync --db data/kalshi.db

# Skip marking to current prices (faster)
uv run kalshi portfolio sync --db data/kalshi.db --skip-mark-prices
```

## CLI Commands

### Balance

Check your account balance:

```bash
uv run kalshi portfolio balance
uv run kalshi portfolio balance --env demo
```

### Sync

Sync positions and trades from Kalshi:

```bash
uv run kalshi portfolio sync --db data/kalshi.db
```

### View Positions

```bash
# All positions
uv run kalshi portfolio positions --db data/kalshi.db

# Specific ticker
uv run kalshi portfolio positions --db data/kalshi.db --ticker TRUMP-2024
```

### View P&L

```bash
uv run kalshi portfolio pnl --db data/kalshi.db
```

Output:

```text
Portfolio P&L Summary
─────────────────────
Realized P&L:    +$45.20
Unrealized P&L:  +$12.50
Total P&L:       +$57.70

Fees Paid:       $8.30
Net P&L:         +$49.40
```

### Trade History

```bash
uv run kalshi portfolio history --db data/kalshi.db --limit 20
```

## Thesis Linking

Connect positions to research theses:

```bash
# Manual link
uv run kalshi portfolio link TRUMP-2024 --thesis abc123 --db data/kalshi.db

# Auto-suggest links based on ticker matches
uv run kalshi portfolio suggest-links --db data/kalshi.db
```

This lets you answer: "How did my actual trades perform vs my thesis predictions?"

## Database Schema

Portfolio tables (in `src/kalshi_research/portfolio/models.py`):

```sql
-- positions table
CREATE TABLE positions (
    ticker TEXT PRIMARY KEY,
    side TEXT,
    quantity INTEGER,
    average_cost REAL,
    market_price REAL,
    unrealized_pnl REAL,
    thesis_id TEXT,
    updated_at TIMESTAMP
);

-- trades table
CREATE TABLE trades (
    id TEXT PRIMARY KEY,
    ticker TEXT,
    side TEXT,
    action TEXT,
    price REAL,
    quantity INTEGER,
    timestamp TIMESTAMP,
    fees REAL
);
```

## P&L Calculation Details

### Realized P&L

Profit/loss on closed positions:

```python
realized_pnl = sum(
    (sell_price - buy_price) * quantity
    for matched in fifo_matches
)
```

### Unrealized P&L

Paper profit/loss on open positions:

```python
unrealized_pnl = sum(
    (market_price - average_cost) * quantity
    for position in open_positions
)
```

### Settlement P&L

When markets settle:

```python
if outcome == "yes":
    pnl = (100 - cost) * quantity  # YES paid 100c
else:
    pnl = (0 - cost) * quantity    # YES paid 0c (you lost)
```

## Performance Metrics

The portfolio can calculate:

- **Total Return**: (ending value - starting value) / starting value
- **Win Rate**: % of trades that were profitable
- **Average Win**: Average P&L on winning trades
- **Average Loss**: Average P&L on losing trades
- **Profit Factor**: Total wins / Total losses
- **Max Drawdown**: Largest peak-to-trough decline

## Key Code

- Models: `src/kalshi_research/portfolio/models.py`
- P&L Calculator: `src/kalshi_research/portfolio/pnl.py`
- Syncer: `src/kalshi_research/portfolio/syncer.py`
- CLI: `src/kalshi_research/cli/portfolio.py`

## Privacy Note

Portfolio data is stored locally in your SQLite database. Nothing is sent to external services.

## See Also

- [Thesis System](../research/thesis-system.md) - Track predictions
- [Backtesting](../research/backtesting.md) - Simulate P&L on theses
- [Configuration](../developer/configuration.md) - API credentials setup
- [Usage: Portfolio](../getting-started/usage.md#portfolio-authenticated) - CLI commands
