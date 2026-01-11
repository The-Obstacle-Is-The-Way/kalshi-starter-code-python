# Backtesting (Explanation)

Backtesting answers the question: **"If I had bet on all my theses, would I have made money?"**

This is the feedback loop that turns prediction market research into a learnable skill.

## Why Backtest?

Without backtesting, you're flying blind:

- You might think you're good at predictions, but you're just lucky
- You might avoid certain markets that you're actually good at
- You can't optimize position sizing without historical performance data
- You can't calculate risk metrics (Sharpe ratio, max drawdown)

Backtesting uses your resolved theses + historical settlement data to simulate what would have happened.

## How It Works

```text
Resolved Theses (data/theses.json)
         │
         ▼
   ThesisBacktester
         │
    ┌────┴────┐
    ▼         ▼
Settlements   Price Snapshots (optional)
(SQLite)      (SQLite)
    │              │
    └──────┬───────┘
           ▼
    BacktestResult
    - Total P&L
    - Win rate
    - Brier score
    - Sharpe ratio
```

## Trade Simulation

For each resolved thesis, the backtester:

1. **Determines entry price**: Uses the `market_probability` at thesis creation (or nearest price snapshot if available)
2. **Determines exit price**: From settlement (YES = 1.0, NO = 0.0)
3. **Determines side**: If your probability > 0.5, you'd bet YES; otherwise NO
4. **Calculates P&L**: Based on entry/exit prices and position size

```python
@dataclass
class BacktestTrade:
    ticker: str
    side: str              # "yes" or "no"
    entry_price: float     # Price when thesis created (0-1)
    exit_price: float      # Settlement price (0 or 1)
    thesis_probability: float
    contracts: int = 1

    @property
    def pnl(self) -> float:
        """Profit/loss in cents per contract."""
        if self.side == "yes":
            return (self.exit_price - self.entry_price) * 100 * self.contracts
        else:
            return (self.entry_price - self.exit_price) * 100 * self.contracts
```

## BacktestResult Metrics

After simulating all trades, you get:

```python
@dataclass
class BacktestResult:
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int

    # P&L
    total_pnl: float       # Total P&L in cents
    avg_pnl: float         # Average P&L per trade
    max_win: float
    max_loss: float

    # Accuracy metrics
    accuracy: float        # % predictions correct
    brier_score: float     # Brier score of predictions
    win_rate: float        # % of trades profitable

    # Risk metrics
    sharpe_ratio: float    # Simplified Sharpe
```

### Understanding the Metrics

**Win Rate vs Accuracy**

These are different:

- **Accuracy**: Did your probability correctly predict the direction? (prob > 0.5 and YES, or prob < 0.5 and NO)
- **Win Rate**: Did you make money on the trade?

You can have high accuracy but low win rate if your edge (difference between your prob and market prob) is small.

**Brier Score**

Aggregate measure of prediction quality:

```python
brier = mean((forecast - outcome)² for all trades)
```

- 0.0 = perfect
- 0.25 = random guessing
- Lower is better

**Sharpe Ratio**

Risk-adjusted return:

```python
sharpe = mean(pnls) / std(pnls)
```

Higher is better. A Sharpe > 1.0 is generally considered good.

## CLI Usage

First, ensure you have settlement data:

```bash
uv run kalshi data sync-settlements --db data/kalshi.db
```

Then run the backtest:

```bash
uv run kalshi research backtest \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --db data/kalshi.db
```

## Position Sizing

The backtester uses a configurable `default_contracts` parameter. In practice, you'd want to:

- Size positions proportional to edge size
- Account for Kelly criterion
- Consider bankroll management

The current implementation uses fixed sizing for simplicity.

## Spread Costs

The current backtester does **not** model spread/slippage costs. Entry prices use:

- `thesis.market_probability` (when no snapshots are available), or
- the closest snapshot midpoint (`(yes_bid + yes_ask) / 2`) when snapshots are available.

Note: `ThesisBacktester` has an `include_spreads` flag, but it is not currently applied in the simulation logic.

## Price Snapshots for Timing

If you have historical price snapshots in your database, the backtester can use them to get more accurate entry prices. This matters because:

- The `market_probability` at thesis creation might not reflect what you'd actually pay
- With snapshots, it finds the closest price to when you created the thesis

```python
if snapshots and settlement.ticker in snapshots:
    entry_price = self._get_price_at_time(
        snapshots[settlement.ticker],
        thesis.created_at,
    )
else:
    entry_price = thesis.market_probability
```

## Void Settlements

Markets that settle as "void" are skipped in backtesting - they don't affect P&L (your money would be returned).

## Key Code

- Backtester: `src/kalshi_research/research/backtest.py`
- CLI command: `src/kalshi_research/cli/research.py`
- Settlement model: `src/kalshi_research/data/models.py`

## Example Output

```text
Backtest Results (thesis-abc123):
  Period: 2024-01-01 to 2024-12-31
  Trades: 15 (10W / 5L)
  Win Rate: 66.7%
  Total P&L: +350c
  Avg P&L: +23.3c/trade
  Brier Score: 0.1823
  Accuracy: 73.3%
```

## See Also

- [Thesis System](thesis-system.md) - How predictions are tracked
- [Calibration Analysis](calibration-analysis.md) - Deeper accuracy metrics
- [Usage: Research](../getting-started/usage.md#research) - CLI commands
