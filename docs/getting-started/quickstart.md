# Quickstart (Tutorial)

Get a working local research pipeline: create a database, sync markets, take snapshots, run scans, and (optionally)
enable authenticated portfolio commands.

## Prerequisites

- Python 3.11+
- `uv` (recommended) or any virtualenv + `pip`

## Install

```bash
uv sync --all-extras
```

Run the CLI without installing globally:

```bash
uv run kalshi version
uv run kalshi --help
```

## 1) Create a database

```bash
uv run kalshi data init
```

Default DB path is `data/kalshi.db` (override with `--db` on any DB-backed command).

## 2) Sync markets/events (start small)

For a quick smoke test, use a small pagination cap:

```bash
uv run kalshi data sync-markets --max-pages 1
```

When you want a complete sync, omit `--max-pages` (or set it to `None` via Python).

## 3) Take snapshots (for metrics/movers/correlation)

```bash
uv run kalshi data snapshot --max-pages 1
```

Taking at least two snapshots makes “movers” meaningful.

## 4) Inspect the database

```bash
uv run kalshi data stats
```

## 5) Pick a ticker and inspect live market data

```bash
uv run kalshi market list --status open --limit 5
uv run kalshi market get <TICKER>
uv run kalshi market orderbook <TICKER> --depth 5
```

## 6) Run scans

```bash
uv run kalshi scan opportunities --filter close-race --top 10 --max-pages 1 --min-volume 1000 --max-spread 10
uv run kalshi scan movers --period 1h --top 10 --db data/kalshi.db --max-pages 1
uv run kalshi scan arbitrage --top 10 --db data/kalshi.db --max-pages 1
```

## 7) Set up alerts (optional)

```bash
uv run kalshi alerts add price <TICKER> --above 0.60
uv run kalshi alerts monitor --once --max-pages 1
```

Alerts are stored locally at `data/alerts.json`.

## 8) Enable authenticated portfolio commands (optional)

Create a `.env` file (the CLI loads it automatically):

```bash
cp .env.example .env
```

Populate:
- `KALSHI_KEY_ID`
- `KALSHI_PRIVATE_KEY_PATH` or `KALSHI_PRIVATE_KEY_B64`
- `KALSHI_ENVIRONMENT` (`demo` or `prod`)

Then:

```bash
uv run kalshi portfolio balance
uv run kalshi portfolio sync --skip-mark-prices
uv run kalshi portfolio positions
```

## 9) Enable Exa-powered research + news (optional)

Copy `.env.example` (or add to your existing `.env`) and set:

- `EXA_API_KEY`

Then you can run Exa-powered commands like:

```bash
uv run kalshi research context <TICKER> --max-news 5 --max-papers 3
uv run kalshi news track <TICKER>
uv run kalshi news collect
uv run kalshi news sentiment <TICKER> --days 7
```

## Next

- `docs/getting-started/usage.md` for task-based workflows
- `docs/developer/cli-reference.md` for the command index
- `docs/architecture/overview.md` for system structure
