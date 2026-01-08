# Architecture (Explanation)

## Package layout

The core package lives at `src/kalshi_research/`:

- `cli.py` — Typer CLI entrypoint (`kalshi`)
- `api/` — async HTTP clients (`KalshiPublicClient`, `KalshiClient`) + Pydantic models
- `data/` — async SQLite/SQLAlchemy persistence (`DatabaseManager`), repositories, export utilities, scheduler
- `analysis/` — calibration/metrics/correlation/scanning/visualization utilities
- `alerts/` — alert conditions + monitor + notifiers
- `portfolio/` — portfolio persistence + sync from authenticated API + FIFO P&L
- `research/` — thesis tracking + backtesting

## Data flow (typical)

1. **Fetch** live markets/events via `KalshiPublicClient`.
2. **Persist** markets/events and snapshots via `DataFetcher` + repositories into SQLite.
3. **Analyze** using DB-backed commands (metrics/calibration/correlation) and scanners (opportunities/movers/arbitrage).
4. **Automate** using alerts (`alerts monitor`) and periodic collection (`data collect`).
5. **(Optional)** sync portfolio data from authenticated endpoints into the same SQLite DB (`portfolio sync`).

## Database

SQLite is the default runtime store (usually `data/kalshi.db`).

Core tables (see `src/kalshi_research/data/models.py`):

- `events`
- `markets` (FK → `events`)
- `price_snapshots` (FK → `markets`)
- `settlements`
- `positions` / `trades` (portfolio)

## Testing strategy

- **Unit tests** (`tests/unit/`): pure logic with minimal mocking (only at system boundaries).
- **E2E tests** (`tests/e2e/`): CLI pipeline tests with mocked HTTP (respx) + real SQLite.
- **Integration tests** (`tests/integration/`): DB migrations/repositories and (optionally) live API tests.

See `docs/TESTING.md` for the exact commands.
