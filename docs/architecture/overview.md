# Architecture (Explanation)

This project is a **research platform** around Kalshi’s `trade-api/v2` (REST + WebSocket), with a local SQLite store
and a modular Typer CLI.

## Package Map

The core package lives under `src/kalshi_research/`:

- `cli/` — Typer CLI package (`kalshi`), wiring subcommands and global config
- `api/` — HTTP clients (`KalshiPublicClient`, `KalshiClient`), auth, rate limiting, Pydantic models
- `data/` — SQLite/SQLAlchemy persistence (`DatabaseManager`), repositories, export, schedulers, fetchers
- `analysis/` — metrics/calibration/correlation/scanning/visualization
- `alerts/` — alert conditions, monitor loop, notifiers
- `portfolio/` — authenticated sync into DB + FIFO P&L
- `research/` — thesis tracking (local JSON) + backtesting (DB + settlements)
- `exa/` — typed async Exa client + cache (optional, enables AI-powered research/news)
- `news/` — news tracking + sentiment pipeline (Exa-powered, DB-backed)

## “One Run” Mental Model

Most workflows follow this shape:

```text
Kalshi (REST) ──► kalshi_research.api (public/auth clients)
                     │
                     ▼
               kalshi_research.data (fetch + persist)
                     │
                     ▼
              SQLite (data/kalshi.db)
                     │
        ┌────────────┼─────────────────────┐
        ▼            ▼                     ▼
   analysis/scan   research/backtest   portfolio/pnl
```

## CLI Composition

The CLI is a **multi-file Typer app**. Subcommands live in separate modules:

```text
kalshi (src/kalshi_research/cli/__init__.py)
├─ data       (src/kalshi_research/cli/data.py)
├─ market     (src/kalshi_research/cli/market.py)
├─ scan       (src/kalshi_research/cli/scan.py)
├─ alerts     (src/kalshi_research/cli/alerts.py)
├─ analysis   (src/kalshi_research/cli/analysis.py)
├─ research   (src/kalshi_research/cli/research.py)
├─ portfolio  (src/kalshi_research/cli/portfolio.py)
└─ news       (src/kalshi_research/cli/news.py)
```

See `docs/architecture/cli.md` for details (including daemon spawning for alerts).

## Storage & Persistence

Default runtime paths (configurable via CLI flags):

- SQLite: `data/kalshi.db`
- Alerts JSON: `data/alerts.json`
- Theses JSON: `data/theses.json`
- Exa cache: `data/exa_cache/` (optional)
- Exports: `data/exports/`
- Alerts daemon log: `data/alert_monitor.log`

### Database Schema (where tables live)

Tables are split across modules but share a single SQLAlchemy `Base`:

- Market data tables: `src/kalshi_research/data/models.py`
  - `events`, `markets`, `price_snapshots`, `settlements`
- News/sentiment tables: `src/kalshi_research/data/models.py`
  - `tracked_items`, `news_articles`, `news_article_markets`, `news_article_events`, `news_sentiments`
- Portfolio tables: `src/kalshi_research/portfolio/models.py`
  - `positions`, `trades`, `portfolio_settlements`

`DatabaseManager` imports `kalshi_research.portfolio.models` to ensure those tables are registered in
`Base.metadata` (so `create_tables()` creates everything).

See `docs/architecture/data-pipeline.md` for the fetch/snapshot/export flow.

## Testing Strategy

- **Unit tests** (`tests/unit/`): pure logic; mock only at system boundaries.
- **Integration tests** (`tests/integration/`): DB migrations/repositories + CLI smoke/integration coverage.
- **E2E tests** (`tests/e2e/`): end-to-end pipelines with mocked HTTP + real SQLite.

See `docs/developer/testing.md` for commands and live-test gating.
