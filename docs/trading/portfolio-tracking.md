# Portfolio Tracking (Explanation)

The portfolio module syncs your actual Kalshi positions, fills (trades), and settlement records, calculates P&L using
FIFO cost basis, and tracks performance over time.

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
    ┌────┼──────────┐
    ▼    ▼          ▼
Positions  Fills   Settlements
    │      │          │
    └──────┴─────┬────┘
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
KALSHI_ENVIRONMENT=demo  # or "prod"

# Prod creds (used when KALSHI_ENVIRONMENT=prod)
KALSHI_KEY_ID=your-prod-key-id
KALSHI_PRIVATE_KEY_PATH=/path/to/prod_private_key.pem
# Or base64-encoded:
KALSHI_PRIVATE_KEY_B64=base64-encoded-prod-key

# Demo creds (preferred when KALSHI_ENVIRONMENT=demo)
KALSHI_DEMO_KEY_ID=your-demo-key-id
KALSHI_DEMO_PRIVATE_KEY_PATH=/path/to/demo_private_key.pem
# Or base64-encoded:
KALSHI_DEMO_PRIVATE_KEY_B64=base64-encoded-demo-key

# Optional: tune authenticated rate limits (only used for portfolio commands)
KALSHI_RATE_TIER=basic  # basic|advanced|premier|prime
```

The CLI loads `.env` automatically.

## Data Model

Data is stored in SQLite via SQLAlchemy models in `src/kalshi_research/portfolio/models.py`:

- `Position` (`positions`): current and historical positions with `avg_price_cents`, mark prices, and unrealized P&L.
- `Trade` (`trades`): fills from `GET /portfolio/fills` (cents-denominated prices).
- `PortfolioSettlement` (`portfolio_settlements`): settlement records from `GET /portfolio/settlements`.

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

We use FIFO because it's a standard accounting method and works well for local cost basis estimation.

## Sync Process

When you run `kalshi portfolio sync`:

1. **Fetch fills**: `GET /portfolio/fills`
2. **Fetch settlements**: `GET /portfolio/settlements`
3. **Fetch positions**: `GET /portfolio/positions`
4. **Compute cost basis**: estimate `avg_price_cents` from synced trades (FIFO)
5. **Mark to market**: fetch current prices (optional) to compute unrealized P&L

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
uv run kalshi portfolio balance --rate-tier advanced
```

### Sync

Sync positions, fills, and settlements from Kalshi:

```bash
uv run kalshi portfolio sync --db data/kalshi.db
uv run kalshi portfolio sync --db data/kalshi.db --rate-tier advanced
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

This prints a summary table including realized/unrealized/total P&L plus trade stats (win rate, average win/loss,
profit factor).

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

The schema is managed by Alembic migrations. The key portfolio tables are:

- `positions`
- `trades`
- `portfolio_settlements`

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
# Kalshi returns settlement fees as a dollar string (fee_cost_dollars).
# We convert to cents (best-effort) and compute:
fee_cents = int(Decimal(fee_cost_dollars) * 100)
settlement_pnl_cents = revenue - yes_total_cost - no_total_cost - fee_cents
```

## Performance Metrics

The CLI currently reports:

- **Realized / unrealized / total P&L**
- **Trade stats**: total trades, win rate, average win/loss, profit factor
- **Data quality notes**: missing mark prices/cost basis (unrealized P&L may be partial) and orphan sell quantity
  skipped (trade history incomplete; trade stats are partial)

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
