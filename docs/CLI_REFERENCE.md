# CLI Reference (SSOT)

This file is a **reference index** for the current CLI.

SSOT is always:

- `kalshi --help`
- `kalshi <command> --help`

If you haven’t installed the `kalshi` entrypoint globally, use `uv run kalshi ...`.

## Top-level

- `kalshi version`
- `kalshi data ...`
- `kalshi market ...`
- `kalshi scan ...`
- `kalshi alerts ...`
- `kalshi analysis ...`
- `kalshi research ...`
- `kalshi portfolio ...`

## Common patterns

- DB-backed commands default to `data/kalshi.db` and accept `--db PATH`.
- Public API iterators support `--max-pages N` as a safety cap.
  - If the cap is reached with a next cursor present, the client logs a warning (data may be incomplete).

## `kalshi data`

- `kalshi data init`
- `kalshi data sync-markets [--status open] [--max-pages N]`
- `kalshi data snapshot [--status open] [--max-pages N]`
- `kalshi data collect [--interval MIN] [--once] [--max-pages N]`
- `kalshi data export [--format parquet|csv] [--output DIR]`
- `kalshi data stats`

## `kalshi market`

- `kalshi market list [--status open] [--event EVT] [--limit N]`
- `kalshi market get <TICKER>`
- `kalshi market orderbook <TICKER> [--depth N]`

## `kalshi scan`

- `kalshi scan opportunities [--filter close-race|high-volume|wide-spread|expiring-soon] [--top N] [--max-pages N]`
  - close-race-only: `--min-volume INT`, `--max-spread INT`
- `kalshi scan movers --db PATH [--period 1h|6h|24h] [--top N] [--max-pages N]`
- `kalshi scan arbitrage --db PATH [--threshold FLOAT] [--top N] [--tickers-limit N] [--max-pages N]`

## `kalshi alerts`

- `kalshi alerts list`
- `kalshi alerts add <price|volume|spread> <TICKER> --above FLOAT`
  - price-only: `--below FLOAT` is supported
- `kalshi alerts remove <ALERT_ID_PREFIX>`
- `kalshi alerts monitor [--once] [--interval SEC] [--max-pages N] [--daemon]`
  - `--daemon` starts a detached background process and writes logs to `data/alert_monitor.log`.

Alerts are stored locally at `data/alerts.json`.

## `kalshi analysis`

- `kalshi analysis metrics <TICKER> --db PATH`
- `kalshi analysis calibration [--days N] [--output FILE] --db PATH`
- `kalshi analysis correlation --db PATH (--event EVT | --tickers T1,T2,...) [--min FLOAT] [--top N]`

## `kalshi research`

- `kalshi research backtest --start YYYY-MM-DD --end YYYY-MM-DD [--db PATH] [--thesis THESIS_ID_PREFIX]`
- `kalshi research thesis create <TITLE> --markets T1,T2 --your-prob P --market-prob P --confidence P [--bull TEXT] [--bear TEXT]`
- `kalshi research thesis list`
- `kalshi research thesis show <THESIS_ID_PREFIX>`
- `kalshi research thesis resolve <THESIS_ID_PREFIX> --outcome yes|no|void`

Theses are stored locally at `data/theses.json`.

## `kalshi portfolio` (authenticated)

The CLI loads `.env` automatically. Authenticated commands require:

- `KALSHI_KEY_ID`
- `KALSHI_PRIVATE_KEY_PATH` or `KALSHI_PRIVATE_KEY_B64`
- `KALSHI_ENVIRONMENT` (`demo` or `prod`, default `demo`)

Commands:

- `kalshi portfolio balance [--env demo|prod]`
- `kalshi portfolio sync [--db PATH] [--env demo|prod] [--skip-mark-prices]`
- `kalshi portfolio positions [--db PATH] [--ticker TICKER]`
- `kalshi portfolio pnl [--db PATH] [--ticker TICKER]`
- `kalshi portfolio history [--db PATH] [--limit N] [--ticker TICKER]`
- `kalshi portfolio link <TICKER> --thesis <THESIS_ID> [--db PATH]`
- `kalshi portfolio suggest-links [--db PATH]`
