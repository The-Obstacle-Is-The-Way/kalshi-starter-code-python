# Python API (Reference)

This repo is a normal `src/` layout package. The main public entrypoints are exported from:

- `kalshi_research.api` — HTTP clients + Pydantic models
- `kalshi_research.data` — SQLite/SQLAlchemy persistence + repositories + fetcher
- `kalshi_research.analysis` — analysis/scanning/visualization utilities
- `kalshi_research.alerts` — alert conditions + monitor
- `kalshi_research.portfolio` — portfolio models + sync + P&L
- `kalshi_research.research` — thesis tracking + backtest scaffolding

## Public API client (no auth)

```python
import asyncio

from kalshi_research.api import KalshiPublicClient


async def main() -> None:
    async with KalshiPublicClient() as client:
        market = await client.get_market("TICKER")
        orderbook = await client.get_orderbook("TICKER", depth=5)
        markets = [m async for m in client.get_all_markets(status="open", max_pages=1)]

    print(market.ticker, orderbook.spread, len(markets))


asyncio.run(main())
```

## Authenticated API client

```python
import asyncio

from kalshi_research.api import KalshiClient


async def main() -> None:
    async with KalshiClient(
        key_id="...",
        private_key_path="/path/to/key.pem",
        environment="demo",
    ) as client:
        balance = await client.get_balance()
        positions = await client.get_positions()

    print(balance, len(positions))


asyncio.run(main())
```

## Data pipeline (DB + fetcher)

```python
import asyncio

from kalshi_research.data import DatabaseManager, DataFetcher


async def main() -> None:
    async with DatabaseManager("data/kalshi.db") as db:
        await db.create_tables()
        async with DataFetcher(db) as fetcher:
            await fetcher.sync_markets(status="open", max_pages=1)
            await fetcher.take_snapshot(status="open", max_pages=1)


asyncio.run(main())
```

## Analysis utilities

High-level exports live in `kalshi_research.analysis`:

- `MarketScanner` (opportunity scanning)
- `CalibrationAnalyzer` / `CalibrationResult`
- `EdgeDetector` / `Edge` / `EdgeType`
- plotting helpers (`plot_probability_timeline`, `plot_spread_timeline`, etc.)

Some analyzers live in submodules (e.g. `kalshi_research.analysis.correlation.CorrelationAnalyzer`).
