# Data Pipeline (Explanation)

This doc explains how market data flows from Kalshi into your local SQLite database, how snapshots/settlements work,
and how exports are generated.

## Components

```text
Kalshi REST (public) ──► KalshiPublicClient (api/)
                              │
                              ▼
                         DataFetcher (data/)
                              │
                              ▼
                         Repositories (data/repositories/)
                              │
                              ▼
                       SQLite (data/kalshi.db)
```

Key code:

- HTTP: `src/kalshi_research/api/client.py`
- Fetch loop: `src/kalshi_research/data/fetcher.py`
- DB manager: `src/kalshi_research/data/database.py`
- Repos: `src/kalshi_research/data/repositories/`

## Schema (what’s stored)

Market data tables:

- `events` (`src/kalshi_research/data/models.py`)
- `markets` (FK → `events`) (`src/kalshi_research/data/models.py`)
- `price_snapshots` (FK → `markets`) (`src/kalshi_research/data/models.py`)
- `settlements` (`src/kalshi_research/data/models.py`)

Portfolio tables (optional/authenticated):

- `positions`, `trades` (`src/kalshi_research/portfolio/models.py`)

News/sentiment tables (optional, Exa-powered):

- `tracked_items`, `news_articles`, `news_article_markets`, `news_article_events`, `news_sentiments`
  (`src/kalshi_research/data/models.py`)

## Snapshots (why movers/correlation work)

Snapshots are point-in-time rows in `price_snapshots`. A single snapshot is enough for “latest metrics”; multiple
snapshots are what makes “movers” and time-based correlation meaningful.

Common pattern:

```text
sync markets/events  -> snapshot -> (wait) -> snapshot -> analyze movers/correlation
```

## Settlements (and backtests)

The pipeline can sync settlements into `settlements`, and the research backtester uses:

- resolved theses (local JSON at `data/theses.json`)
- settlements in SQLite

to compute P&L/accuracy/Brier score over a date range.

## Exports

Exports are generated from the SQLite database and written under `data/exports/`:

- Parquet: `events.parquet`, `markets.parquet`, `settlements.parquet`, plus partitioned `price_snapshots/`
- CSV: `events.csv`, `markets.csv`, `settlements.csv`, `price_snapshots.csv`

The CLI entrypoint for exports is `kalshi data export` (see `docs/developer/cli-reference.md`).
