# Usage (How-to Guides)

Task-oriented workflows for the current CLI and Python package.

If you haven’t installed the `kalshi` entrypoint globally, use `uv run kalshi ...`.

---

## Data pipeline

### Initialize a database

```bash
uv run kalshi data init
uv run kalshi data init --db /tmp/kalshi.db
```

### Validate/apply DB schema migrations

For a brand new database, `kalshi data init` is enough. If you’re upgrading an existing DB (or pulling new
migrations), use:

```bash
# Dry-run by default: validates migrations on a temporary DB copy
uv run kalshi data migrate --db data/kalshi.db

# Apply migrations to the real DB
uv run kalshi data migrate --db data/kalshi.db --apply
```

### Sync markets/events from the public API

```bash
uv run kalshi data sync-markets
uv run kalshi data sync-markets --status open
uv run kalshi data sync-markets --max-pages 10
```

If `--max-pages` is reached while a cursor still exists, the client logs a warning (data may be incomplete).

### Take a snapshot of current prices

```bash
uv run kalshi data snapshot
uv run kalshi data snapshot --status open --max-pages 10
```

### Sync settlements (resolved outcomes)

Settlements power `kalshi research backtest` and calibration analysis.

```bash
uv run kalshi data sync-settlements --db data/kalshi.db
uv run kalshi data sync-settlements --db data/kalshi.db --max-pages 10
```

### Fetch public trade history (market trades)

This hits Kalshi’s public `/markets/trades` endpoint (not your authenticated fills).

```bash
uv run kalshi data sync-trades --limit 100 --json
uv run kalshi data sync-trades --ticker <TICKER> --limit 100 --output trades.csv
```

### Run collection continuously (or once)

```bash
uv run kalshi data collect --interval 15
uv run kalshi data collect --once --max-pages 10
```

### Export to Parquet/CSV

```bash
uv run kalshi data export --format parquet --output data/exports
uv run kalshi data export --format csv --output data/exports
```

Export layout:

- Parquet:
  - `events.parquet`, `markets.parquet`, `settlements.parquet`
  - `price_snapshots/` partitioned by month (`price_snapshots/month=YYYY-MM/*.parquet`)
- CSV:
  - `events.csv`, `markets.csv`, `settlements.csv`, `price_snapshots.csv`

### View database stats

```bash
uv run kalshi data stats
uv run kalshi data stats --db /tmp/kalshi.db
```

### Maintenance (keep disk usage bounded)

```bash
# Preview deletes (dry-run default)
uv run kalshi data prune --db data/kalshi.db --snapshots-older-than-days 30 --news-older-than-days 30

# Apply deletes
uv run kalshi data prune --db data/kalshi.db --snapshots-older-than-days 30 --news-older-than-days 30 --apply

# Reclaim disk space after large deletes (SQLite VACUUM)
uv run kalshi data vacuum --db data/kalshi.db
```

---

## Market lookup (public)

```bash
uv run kalshi market list --status open --limit 20 --full
uv run kalshi market list --event <EVENT_TICKER> --limit 20
uv run kalshi market list --event-prefix KXFED --limit 20
uv run kalshi market list --category Politics --limit 20
uv run kalshi market list --exclude-category Sports --limit 20
uv run kalshi market get <TICKER>
uv run kalshi market orderbook <TICKER> --depth 5
uv run kalshi market liquidity <TICKER> --depth 25
uv run kalshi market history <TICKER> --interval 1h --days 7
```

---

## Scanning

### Opportunities

```bash
uv run kalshi scan opportunities --filter close-race --top 10 --min-volume 1000 --max-spread 10 --max-pages 10
uv run kalshi scan opportunities --filter close-race --category ai --top 10 --min-volume 1000 --max-spread 10 --max-pages 10 --full
uv run kalshi scan opportunities --filter high-volume --top 10 --max-pages 10
uv run kalshi scan opportunities --filter wide-spread --top 10 --max-pages 10
uv run kalshi scan opportunities --filter expiring-soon --top 10 --max-pages 10
```

### New Markets

```bash
uv run kalshi scan new-markets --hours 24 --limit 20
uv run kalshi scan new-markets --hours 24 --include-unpriced --category econ,ai --limit 20
```

### Movers (requires snapshots in your DB)

```bash
uv run kalshi scan movers --db data/kalshi.db --period 1h --top 10 --max-pages 10 --full
```

### Arbitrage

```bash
uv run kalshi scan arbitrage --db data/kalshi.db --threshold 0.10 --top 10 --tickers-limit 50 --max-pages 10 --full
```

---

## Alerts

Alerts are stored in `data/alerts.json`.

### Add / list / remove

```bash
uv run kalshi alerts list
uv run kalshi alerts add price <TICKER> --above 0.60
uv run kalshi alerts add price <TICKER> --below 0.40
uv run kalshi alerts add volume <TICKER> --above 10000
uv run kalshi alerts add spread <TICKER> --above 5
uv run kalshi alerts add sentiment <TICKER> --above 0.20
uv run kalshi alerts remove <ALERT_ID_PREFIX>
```

Notes:

- `--below` is only valid for `price` alerts; `volume`/`spread`/`sentiment` will error if you pass `--below`.
- `sentiment` alerts trigger on absolute change in rolling sentiment; they depend on news/sentiment data being present
  in `data/kalshi.db` (run `kalshi news collect` periodically).

### Monitor

```bash
uv run kalshi alerts monitor --interval 60
uv run kalshi alerts monitor --once --max-pages 10
uv run kalshi alerts monitor --daemon --interval 60
uv run kalshi alerts monitor --output-file data/alerts_triggered.jsonl
uv run kalshi alerts monitor --webhook-url https://example.com/webhook
```

If you run the alerts daemon long-term, keep the log size bounded:

```bash
# Dry-run by default
uv run kalshi alerts trim-log

# Apply trimming
uv run kalshi alerts trim-log --apply
```

---

## Analysis (DB-backed)

### Metrics

```bash
uv run kalshi analysis metrics <TICKER> --db data/kalshi.db
```

### Calibration (Brier score)

```bash
uv run kalshi analysis calibration --db data/kalshi.db --days 30
uv run kalshi analysis calibration --db data/kalshi.db --days 30 --output calibration.json
```

### Correlation

```bash
uv run kalshi analysis correlation --db data/kalshi.db --event <EVENT_TICKER> --top 10
uv run kalshi analysis correlation --db data/kalshi.db --tickers T1,T2,T3 --top 10
```

---

## Research

Theses are stored in `data/theses.json`.

```bash
uv run kalshi research thesis create "My thesis title" \\
  --markets TICK1,TICK2 \\
  --your-prob 0.65 \\
  --market-prob 0.55 \\
  --confidence 0.8

uv run kalshi research thesis list
uv run kalshi research thesis show <THESIS_ID_PREFIX>
uv run kalshi research thesis edit <THESIS_ID_PREFIX> --title "New title"
uv run kalshi research thesis resolve <THESIS_ID_PREFIX> --outcome yes
```

### Exa-powered research (optional)

Set `EXA_API_KEY` in your environment or `.env` to use these commands:

```bash
uv run kalshi research context <TICKER> --max-news 5 --max-papers 3 --days 30
uv run kalshi research topic "Fed rate cuts 2026" --json
uv run kalshi research similar "https://example.com/some-article" --num-results 10 --json
uv run kalshi research thesis create "My thesis title" ... --with-research
uv run kalshi research thesis check-invalidation <THESIS_ID_PREFIX> --hours 48
uv run kalshi research thesis suggest --category crypto
```

Use `--mode fast|standard|deep` and `--budget-usd` on `kalshi research context/topic` to cap Exa spend per run.

Exa deep research is a paid endpoint:

```bash
uv run kalshi research deep "What would make this market resolve YES?" --wait
```

Cache maintenance:

```bash
uv run kalshi research cache clear          # expired-only (default)
uv run kalshi research cache clear --all    # delete everything
```

Backtesting runs on resolved theses using settlement data in the database:

```bash
uv run kalshi data sync-settlements --db data/kalshi.db
uv run kalshi research backtest --start 2024-01-01 --end 2024-12-31 --db data/kalshi.db
```

---

## News & sentiment (Exa-powered, DB-backed)

News and sentiment data is stored in SQLite (default: `data/kalshi.db`).

```bash
uv run kalshi news track <TICKER>
uv run kalshi news collect
uv run kalshi news sentiment <TICKER> --days 7
```

---

## Portfolio (authenticated)

The CLI loads `.env` automatically. Configure:

- `KALSHI_KEY_ID`
- `KALSHI_PRIVATE_KEY_PATH` or `KALSHI_PRIVATE_KEY_B64`
- `KALSHI_ENVIRONMENT` (`demo` or `prod`; defaults to `prod` if unset; invalid values exit with an error)

Optional (recommended if you keep both demo + prod keys in one `.env`):

- `KALSHI_DEMO_KEY_ID`
- `KALSHI_DEMO_PRIVATE_KEY_PATH` or `KALSHI_DEMO_PRIVATE_KEY_B64`

### Balance

```bash
uv run kalshi portfolio balance
uv run kalshi portfolio balance --env prod
```

### Sync positions/fills/settlements (and compute P&L)

```bash
uv run kalshi portfolio sync --db data/kalshi.db
uv run kalshi portfolio sync --db data/kalshi.db --skip-mark-prices
```

### View positions, P&L, history

```bash
uv run kalshi portfolio positions --db data/kalshi.db
uv run kalshi portfolio positions --db data/kalshi.db --ticker <TICKER>
uv run kalshi portfolio pnl --db data/kalshi.db
uv run kalshi portfolio history --db data/kalshi.db --limit 20
```

### Link positions to theses

```bash
uv run kalshi portfolio link <TICKER> --thesis <THESIS_ID> --db data/kalshi.db
uv run kalshi portfolio suggest-links --db data/kalshi.db
```

---

## Troubleshooting

- **“Pagination truncated …” warning:** you set `--max-pages` and hit the safety cap. Increase it or remove it for
  full iteration.
- **“Database not found …”:** run `kalshi data init --db ...` first, or pass the correct `--db`.
- **“Migrations required …”:** run `kalshi data migrate` (dry-run by default; use `--apply` to execute).
- **Auth errors:** confirm your `.env` values; see `docs/developer/configuration.md`.

## See also

- `docs/developer/cli-reference.md`
- `docs/developer/python-api.md`
- `docs/developer/testing.md`
- `docs/architecture/overview.md`
