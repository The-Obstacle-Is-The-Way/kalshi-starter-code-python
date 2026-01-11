# CLI Reference (SSOT)

This file is a **reference index** for the current CLI.

SSOT is always:

- `uv run kalshi --help`
- `uv run kalshi <command> --help`

If you haven’t installed the `kalshi` entrypoint globally, use `uv run kalshi ...`.

## Command map (implementation)

This is the “where to find it in code” map for CLI commands:

```text
kalshi
├─ (status, version) -> src/kalshi_research/cli/__init__.py
├─ data       -> src/kalshi_research/cli/data.py
├─ market     -> src/kalshi_research/cli/market.py
├─ scan       -> src/kalshi_research/cli/scan.py
├─ alerts     -> src/kalshi_research/cli/alerts.py
├─ analysis   -> src/kalshi_research/cli/analysis.py
├─ research   -> src/kalshi_research/cli/research.py
├─ portfolio  -> src/kalshi_research/cli/portfolio.py
└─ news       -> src/kalshi_research/cli/news.py
```

Notes:
- Global `--env/-e` lives in `src/kalshi_research/cli/__init__.py`.
- `python -m kalshi_research.cli ...` is enabled by `src/kalshi_research/cli/__main__.py` (required for daemon mode).

## Top-level

- Global option: `--env/-e` (defaults to `KALSHI_ENVIRONMENT` or `prod`; invalid values exit with an error)
- `kalshi version`
- `kalshi status [--json]`
- `kalshi data ...`
- `kalshi market ...`
- `kalshi scan ...`
- `kalshi alerts ...`
- `kalshi analysis ...`
- `kalshi research ...`
- `kalshi portfolio ...`
- `kalshi news ...`

## Common patterns

- DB-backed commands default to `data/kalshi.db` and accept `--db/-d PATH`.
- Public API iterators support `--max-pages N` as a safety cap (omit for full iteration).
  - If the cap is reached with a next cursor present, the client logs a warning (data may be incomplete).

## `kalshi data`

- `kalshi data init`
- `kalshi data migrate [--dry-run|--apply]`
- `kalshi data sync-markets [--status open] [--max-pages N]`
- `kalshi data sync-settlements [--max-pages N]`
- `kalshi data sync-trades [--ticker TICKER] [--limit N] [--min-ts TS] [--max-ts TS] [--output FILE] [--json]`
- `kalshi data snapshot [--status open] [--max-pages N]`
- `kalshi data collect [--interval MINUTES] [--once] [--max-pages N]`
- `kalshi data export [--format parquet|csv] [--output DIR]`
- `kalshi data stats`
- `kalshi data prune [--snapshots-older-than-days N] [--news-older-than-days N] [--dry-run|--apply]`
- `kalshi data vacuum`

## `kalshi market`

- `kalshi market list [--status unopened|open|paused|closed|settled] [--event EVT] [--limit N]`
- `kalshi market get <TICKER>`
- `kalshi market orderbook <TICKER> [--depth N]`
- `kalshi market liquidity <TICKER> [--depth N] [--max-slippage-cents N]`
- `kalshi market history <TICKER> [--series SERIES] [--interval 1m|1h|1d] [--days N] [--start-ts TS] [--end-ts TS] [--json]`

Note: Kalshi's **response** `status` values (e.g. `active`) differ from the `/markets` **filter** values. The CLI maps `--status active` → `open` with a warning.

## `kalshi scan`

- `kalshi scan opportunities [--filter close-race|high-volume|wide-spread|expiring-soon] [--top N] [--max-pages N]`
  - close-race-only: `--min-volume INT`, `--max-spread INT`
  - optional liquidity scoring: `--min-liquidity INT`, `--show-liquidity`, `--liquidity-depth INT`
- `kalshi scan movers --db PATH [--period 1h|6h|24h] [--top N] [--max-pages N]`
- `kalshi scan arbitrage --db PATH [--threshold FLOAT] [--top N] [--tickers-limit N] [--max-pages N]`

## `kalshi alerts`

- `kalshi alerts list`
- `kalshi alerts add <price|volume|spread|sentiment> <TICKER> (--above FLOAT | --below FLOAT)`
  - `volume`, `spread`, and `sentiment` support `--above` only (no `--below`)
- `kalshi alerts remove <ALERT_ID_PREFIX>`
- `kalshi alerts monitor [--once] [--interval SEC] [--max-pages N] [--daemon] [--output-file PATH] [--webhook-url URL]`
  - `--daemon` starts a detached background process and writes logs to `data/alert_monitor.log`.
- `kalshi alerts trim-log [--log PATH] [--max-mb N] [--keep-mb N] [--dry-run|--apply]`

Alerts are stored locally at `data/alerts.json`.

## `kalshi analysis`

- `kalshi analysis metrics <TICKER> --db PATH`
- `kalshi analysis calibration [--days N] [--output FILE] --db PATH`
- `kalshi analysis correlation --db PATH (--event EVT | --tickers T1,T2,...) [--min FLOAT] [--top N]`

## `kalshi research`

- `kalshi research backtest --start YYYY-MM-DD --end YYYY-MM-DD [--db PATH] [--thesis THESIS_ID_PREFIX]` (`--end` is inclusive)
- `kalshi research context <TICKER> [--max-news N] [--max-papers N] [--days N] [--json]`
- `kalshi research topic <TOPIC> [--no-summary] [--json]`
- `kalshi research similar <URL> [--num-results N] [--json]`
- `kalshi research deep <TOPIC> [--model exa-research|exa-research-pro] [--wait] [--schema FILE] [--json]`
- `kalshi research cache clear [--all] [--cache-dir DIR]`
- `kalshi research thesis create <TITLE> --markets T1,T2 --your-prob P --market-prob P --confidence P [--bull TEXT] [--bear TEXT]`
  - optional: `--with-research` (requires `EXA_API_KEY`)
- `kalshi research thesis list`
- `kalshi research thesis show <THESIS_ID_PREFIX>`
- `kalshi research thesis resolve <THESIS_ID_PREFIX> --outcome yes|no|void`
- `kalshi research thesis check-invalidation <THESIS_ID_PREFIX> [--hours N]`
- `kalshi research thesis suggest [--category TEXT]`

Theses are stored locally at `data/theses.json`.

## `kalshi news` (Exa-powered, DB-backed)

News data is stored in SQLite (default: `data/kalshi.db`).

- `kalshi news track <TICKER> [--event] [--queries Q1,Q2,...] [--db PATH]`
- `kalshi news untrack <TICKER> [--db PATH]`
- `kalshi news list-tracked [--all] [--db PATH]`
- `kalshi news collect [--ticker TICKER] [--lookback-days N] [--max-per-query N] [--db PATH]`
- `kalshi news sentiment <TICKER> [--event] [--days N] [--db PATH]`

## `kalshi portfolio` (authenticated)

The CLI loads `.env` automatically. Authenticated commands require:

- `KALSHI_KEY_ID`
- `KALSHI_PRIVATE_KEY_PATH` or `KALSHI_PRIVATE_KEY_B64`
- `KALSHI_ENVIRONMENT` (`demo` or `prod`; defaults to `prod` if unset; invalid values exit with an error)

Commands:

- `kalshi portfolio balance [--env demo|prod]`
- `kalshi portfolio sync [--db PATH] [--env demo|prod] [--skip-mark-prices]`
- `kalshi portfolio positions [--db PATH] [--ticker TICKER]`
- `kalshi portfolio pnl [--db PATH] [--ticker TICKER]`
- `kalshi portfolio history [--db PATH] [--limit N] [--ticker TICKER]`
- `kalshi portfolio link <TICKER> --thesis <THESIS_ID> [--db PATH]`
- `kalshi portfolio suggest-links [--db PATH]`
