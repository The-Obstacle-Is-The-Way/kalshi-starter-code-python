# Usage Guide

Comprehensive guide to using the Kalshi Research Platform.

## Table of Contents

- [Installation](#installation)
- [CLI Commands](#cli-commands)
- [Python API](#python-api)
- [Alerts System](#alerts-system)
- [Research Workflow](#research-workflow)
- [Data Export](#data-export)
- [Authentication](#authentication)
- [Troubleshooting](#troubleshooting)

---

## Installation

### Requirements

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

### Install with uv (Recommended)

```bash
git clone <repo-url>
cd kalshi-research
uv sync
```

This installs the package and all dependencies in a virtual environment.

### Install with pip

```bash
git clone <repo-url>
cd kalshi-research
pip install -e ".[dev,research]"
```

---

## CLI Commands

### Data Management

#### Initialize Database

```bash
kalshi data init
```

Creates SQLite database at `data/kalshi.db` with schema for markets, events, trades, and price history.

#### Sync Markets

```bash
# Sync all markets
kalshi data sync-markets

# Sync specific event
kalshi data sync-event EVENT-TICKER
```

Fetches market data from Kalshi API and stores in local database.

#### Continuous Data Collection

```bash
# Collect every 15 minutes
kalshi data collect --interval 15

# Collect every hour
kalshi data collect --interval 60

# Run once (no interval)
kalshi data collect
```

Continuously fetches price snapshots and stores them for historical analysis.

#### Export Data

```bash
# Export to Parquet (best for pandas/DuckDB)
kalshi data export --format parquet --output data/export/

# Export to CSV
kalshi data export --format csv --output data/export/

# Export specific tables
kalshi data export --tables markets,trades --format parquet
```

### Market Exploration

#### List Markets

```bash
# List all markets
kalshi market list

# Limit results
kalshi market list --limit 10

# Filter by status
kalshi market list --status open
```

#### Get Market Details

```bash
kalshi market get KXBTC-25JAN01-60000
```

Shows detailed information about a specific market including current prices, volume, and metadata.

#### View Orderbook

```bash
kalshi market orderbook KXBTC-25JAN01-60000
```

Shows current bids and asks for the market.

#### Get Trade History

```bash
# Recent trades
kalshi market trades KXBTC-25JAN01-60000

# Last 100 trades
kalshi market trades KXBTC-25JAN01-60000 --limit 100
```

### Market Scanning

#### Scan for Opportunities

```bash
# Close races (near 50/50)
kalshi scan opportunities --filter close-race

# High volume markets
kalshi scan opportunities --filter high-volume

# Wide spread (arbitrage potential)
kalshi scan opportunities --filter wide-spread

# Combine filters
kalshi scan opportunities --filter close-race --filter high-volume

# Limit results
kalshi scan opportunities --filter close-race --top 10
```

#### Scan by Category

```bash
# Scan specific event
kalshi scan opportunities --event KXBTC

# Scan by series
kalshi scan opportunities --series bitcoin
```

### Analysis Commands

#### Calibration Analysis

```bash
# Analyze market calibration
kalshi analysis calibration --market TICKER-NAME

# Analyze across all markets
kalshi analysis calibration --all

# Historical calibration
kalshi analysis calibration --from 2024-01-01 --to 2024-12-31
```

Shows Brier scores and calibration curves to measure how well market prices predict outcomes.

#### Correlation Analysis

```bash
# Find correlated markets
kalshi analysis correlation --market TICKER-NAME

# Correlation threshold
kalshi analysis correlation --market TICKER-NAME --threshold 0.7

# Time window
kalshi analysis correlation --market TICKER-NAME --window 7d
```

#### Edge Detection

```bash
# Find potential mispricing
kalshi analysis edge --thesis-file my-thesis.json

# Specific market
kalshi analysis edge --market TICKER-NAME --expected-prob 0.65
```

### Alerts (SPEC-005)

#### List Alerts

```bash
kalshi alerts list
```

#### Add Alert

```bash
# Price threshold alert
kalshi alerts add --market TICKER-NAME --condition "yes_price > 0.60" --notify email

# Volume alert
kalshi alerts add --market TICKER-NAME --condition "volume > 10000" --notify webhook

# Spread alert
kalshi alerts add --market TICKER-NAME --condition "spread < 0.05" --notify email
```

#### Remove Alert

```bash
kalshi alerts remove ALERT-ID
```

#### Monitor Alerts

```bash
# Run alert monitoring (continuous)
kalshi alerts monitor

# Check once
kalshi alerts check
```

### Research Commands

#### Create Thesis

```bash
kalshi research thesis create --name "My Thesis" --description "Market is underpriced"
```

#### Track Thesis

```bash
# Add market to thesis
kalshi research thesis add-market THESIS-ID TICKER-NAME --expected-prob 0.70

# View thesis performance
kalshi research thesis show THESIS-ID
```

#### Backtest Strategy

```bash
# Backtest thesis
kalshi research backtest --thesis-file thesis.json --from 2024-01-01 --to 2024-12-31

# Backtest with parameters
kalshi research backtest --strategy momentum --params params.json
```

---

## Python API

### Using the Kalshi Client

```python
from kalshi_research.api import KalshiPublicClient
import asyncio

async def main():
    async with KalshiPublicClient() as client:
        # Get all markets
        markets = await client.get_markets()

        # Get specific market
        market = await client.get_market("KXBTC-25JAN01-60000")

        # Get orderbook
        orderbook = await client.get_orderbook("KXBTC-25JAN01-60000")

        # Get trades
        trades = await client.get_trades("KXBTC-25JAN01-60000")

asyncio.run(main())
```

### Using the Data Layer

```python
from kalshi_research.data import DatabaseManager, MarketRepository
import asyncio

async def main():
    db = DatabaseManager("sqlite+aiosqlite:///data/kalshi.db")
    await db.init_db()

    market_repo = MarketRepository(db)

    # Get markets from database
    markets = await market_repo.list_markets(status="open", limit=10)

    # Get specific market
    market = await market_repo.get_market("KXBTC-25JAN01-60000")

    # Get price history
    prices = await market_repo.get_price_history(
        "KXBTC-25JAN01-60000",
        from_date="2024-01-01"
    )

asyncio.run(main())
```

### Market Scanning

```python
from kalshi_research.analysis import MarketScanner, ScanFilter
import asyncio

async def main():
    scanner = MarketScanner(db_manager)

    # Find close races
    opportunities = await scanner.scan_opportunities([
        ScanFilter.CLOSE_RACE,
        ScanFilter.HIGH_VOLUME
    ])

    for opp in opportunities:
        print(f"{opp.ticker}: {opp.yes_price:.2f} ({opp.score:.2f})")

asyncio.run(main())
```

### Calibration Analysis

```python
from kalshi_research.analysis import CalibrationAnalyzer
import asyncio

async def main():
    analyzer = CalibrationAnalyzer(db_manager)

    # Analyze specific market
    metrics = await analyzer.analyze_market("KXBTC-25JAN01-60000")
    print(f"Brier Score: {metrics.brier_score:.4f}")

    # Get calibration curve
    curve = await analyzer.get_calibration_curve("KXBTC-25JAN01-60000")

asyncio.run(main())
```

### Edge Detection

```python
from kalshi_research.analysis import EdgeDetector, Thesis
import asyncio

async def main():
    detector = EdgeDetector(db_manager)

    # Create thesis
    thesis = Thesis(
        market_ticker="KXBTC-25JAN01-60000",
        expected_prob=0.70,
        confidence=0.80,
        rationale="Technical analysis suggests..."
    )

    # Detect edge
    edge = await detector.detect_edge(thesis)

    if edge.has_edge:
        print(f"Edge detected! EV: {edge.expected_value:.2f}")

asyncio.run(main())
```

---

## Alerts System

### Setting Up Email Alerts

Configure email settings in `config.toml`:

```toml
[alerts.email]
smtp_host = "smtp.gmail.com"
smtp_port = 587
username = "your-email@gmail.com"
password = "your-app-password"
from_address = "your-email@gmail.com"
to_addresses = ["alerts@example.com"]
```

### Setting Up Webhook Alerts

```toml
[alerts.webhook]
url = "https://your-webhook-url.com/alerts"
headers = {Authorization = "Bearer your-token"}
```

### Custom Alert Conditions

```python
from kalshi_research.alerts import AlertCondition, AlertMonitor
import asyncio

async def main():
    # Create custom condition
    condition = AlertCondition(
        market_ticker="KXBTC-25JAN01-60000",
        condition_expr="yes_price > 0.60 and volume > 5000",
        notify_channel="email"
    )

    # Add to monitor
    monitor = AlertMonitor(db_manager)
    await monitor.add_alert(condition)

    # Run monitoring
    await monitor.monitor_continuous(check_interval=60)

asyncio.run(main())
```

---

## Research Workflow

### 1. Create a Thesis

```python
from kalshi_research.research import Thesis, ThesisTracker
import asyncio

async def main():
    tracker = ThesisTracker(db_manager)

    thesis = Thesis(
        name="Bitcoin Rally Thesis",
        description="BTC will hit 60k by Jan 31",
        markets={
            "KXBTC-25JAN31-60000": {
                "expected_prob": 0.70,
                "confidence": 0.80,
                "rationale": "Technical breakout + institutional inflows"
            }
        }
    )

    thesis_id = await tracker.create_thesis(thesis)
    print(f"Created thesis: {thesis_id}")

asyncio.run(main())
```

### 2. Monitor Performance

```python
async def check_performance():
    tracker = ThesisTracker(db_manager)

    performance = await tracker.get_thesis_performance(thesis_id)
    print(f"Accuracy: {performance.accuracy:.2%}")
    print(f"Brier Score: {performance.brier_score:.4f}")
    print(f"ROI: {performance.roi:.2%}")
```

### 3. Backtest Strategy

```python
from kalshi_research.research import Backtester

async def run_backtest():
    backtester = Backtester(db_manager)

    results = await backtester.backtest_thesis(
        thesis_id=thesis_id,
        from_date="2024-01-01",
        to_date="2024-12-31",
        initial_capital=10000,
        position_size=0.05  # 5% per trade
    )

    print(f"Total Return: {results.total_return:.2%}")
    print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
    print(f"Win Rate: {results.win_rate:.2%}")
```

---

## Data Export

### Export to Pandas

```python
import pandas as pd
from kalshi_research.data import DataExporter

async def export_to_pandas():
    exporter = DataExporter(db_manager)

    # Export markets
    df_markets = await exporter.export_markets_to_df()

    # Export price history
    df_prices = await exporter.export_price_history_to_df(
        from_date="2024-01-01"
    )

    # Export trades
    df_trades = await exporter.export_trades_to_df()
```

### Export to Parquet

```bash
# CLI export
kalshi data export --format parquet --output data/export/

# Then use with DuckDB
duckdb data/export/kalshi.db
```

```sql
-- Query in DuckDB
SELECT ticker, yes_price, volume, timestamp
FROM markets
WHERE status = 'open'
ORDER BY volume DESC
LIMIT 10;
```

### Export to CSV

```bash
kalshi data export --format csv --output data/export/
```

---

## Authentication

For authenticated endpoints (trading, portfolio tracking):

### Set Up Credentials

Create `.env` file:

```env
KALSHI_EMAIL=your-email@example.com
KALSHI_PASSWORD=your-password
```

Or set environment variables:

```bash
export KALSHI_EMAIL=your-email@example.com
export KALSHI_PASSWORD=your-password
```

### Use Authenticated Client

```python
from kalshi_research.api import KalshiClient
import asyncio

async def main():
    async with KalshiClient() as client:
        # Get your portfolio
        portfolio = await client.get_portfolio()

        # Get positions
        positions = await client.get_positions()

        # Get balance
        balance = await client.get_balance()

asyncio.run(main())
```

**Note:** The platform is designed for research, not automated trading. Use manual trading through the Kalshi web interface.

---

## Troubleshooting

### Database Issues

**Problem:** `sqlite3.OperationalError: no such table`

**Solution:**
```bash
kalshi data init  # Reinitialize database
```

### API Rate Limits

**Problem:** `HTTPException: 429 Too Many Requests`

**Solution:** The client has built-in rate limiting. If you still hit limits:
- Increase delay between requests
- Use data collection with longer intervals
- Cache results in local database

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'kalshi_research'`

**Solution:**
```bash
pip install -e .
# or
uv sync
```

### Test Failures

```bash
# Run tests with verbose output
uv run pytest -vv

# Run specific test
uv run pytest tests/unit/test_api/test_client.py -k test_get_markets

# Clear pytest cache
rm -rf .pytest_cache
```

### Type Checking Errors

```bash
# Run mypy with verbose output
uv run mypy src/ --show-error-codes

# Ignore specific errors
# Add to pyproject.toml:
# [tool.mypy]
# disable_error_code = ["import-untyped"]
```

---

## Advanced Topics

### Custom Strategies

Create custom scanning strategies:

```python
from kalshi_research.analysis import MarketScanner, OpportunityScore

class CustomScanner(MarketScanner):
    async def custom_scan(self) -> list[OpportunityScore]:
        """Find markets with your custom criteria."""
        markets = await self.market_repo.list_markets(status="open")

        opportunities = []
        for market in markets:
            # Your custom logic here
            if self._meets_criteria(market):
                score = self._calculate_score(market)
                opportunities.append(OpportunityScore(
                    ticker=market.ticker,
                    score=score,
                    reason="Custom criteria met"
                ))

        return sorted(opportunities, key=lambda x: x.score, reverse=True)
```

### Jupyter Notebooks

Use the platform in Jupyter notebooks:

```python
# notebooks/exploration.ipynb
from kalshi_research import *
import pandas as pd
import matplotlib.pyplot as plt

# Initialize
db = DatabaseManager("sqlite+aiosqlite:///data/kalshi.db")
await db.init_db()

# Load data
markets = await MarketRepository(db).list_markets()
df = pd.DataFrame([m.dict() for m in markets])

# Analyze
df.plot(x='timestamp', y='yes_price')
plt.show()
```

---

## Further Reading

- [Technical Specifications](docs/_specs/) - Detailed spec docs
- [API Reference](https://trading-api.readme.io/reference) - Kalshi API docs
- [Python API Docs](https://docs.python.org/3/) - Python documentation

---

## Support

For issues, questions, or contributions:

- GitHub Issues: [your-repo]/issues
- Email: your-email@example.com
