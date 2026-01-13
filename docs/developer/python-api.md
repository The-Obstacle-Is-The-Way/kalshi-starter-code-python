# Python API (Reference)

This repo is a normal `src/` layout package. The main public entrypoints are exported from:

- `kalshi_research.api` — HTTP clients + Pydantic models
- `kalshi_research.data` — SQLite/SQLAlchemy persistence + repositories + fetcher
- `kalshi_research.analysis` — analysis/scanning/visualization utilities
- `kalshi_research.alerts` — alert conditions + monitor
- `kalshi_research.portfolio` — portfolio models + sync + P&L
- `kalshi_research.research` — thesis tracking + backtesting
- `kalshi_research.exa` — Exa async client + cache + models (optional, requires `EXA_API_KEY`)
- `kalshi_research.news` — news tracking + sentiment pipeline (Exa-powered, DB-backed)

You can also import the core API clients directly from `kalshi_research`:

```python
from kalshi_research import Environment, KalshiClient, KalshiPublicClient
```

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

## Series discovery (public API)

Kalshi’s intended browse pattern is:

`get_tags_by_categories()` → `get_series_list()` → `get_all_markets(series_ticker=...)`

Related endpoints are also available:

- `get_series(series_ticker)`
- `get_series_fee_changes()`

```python
import asyncio

from kalshi_research.api import KalshiPublicClient


async def main() -> None:
    async with KalshiPublicClient() as client:
        tags_by_category = await client.get_tags_by_categories()
        series = await client.get_series_list(category="Politics", include_volume=True)

    print(len(tags_by_category), len(series))


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

## Exa client (async search + deep research + crash recovery)

```python
import asyncio

from kalshi_research.exa import ExaClient


async def main() -> None:
    async with ExaClient.from_env() as exa:
        results = await exa.search("Kalshi prediction markets", num_results=5)

        # Deep research runs asynchronously via /research/v1.
        task = await exa.create_research_task(
            instructions="Summarize what could cause this market to resolve YES.",
            model="exa-research-fast",  # also: exa-research, exa-research-pro
        )

        # Crash recovery: list tasks, find a likely match, then fetch by ID.
        page = await exa.list_research_tasks(limit=10)
        recovered = await exa.find_recent_research_task(instructions_prefix="Summarize what could cause")

    print(len(results.results), len(page.data), task.status, recovered is not None)


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
- `Edge` / `EdgeType`
- plotting helpers (`plot_probability_timeline`, `plot_spread_timeline`, etc.)

Some analyzers live in submodules (e.g. `kalshi_research.analysis.correlation.CorrelationAnalyzer`).
