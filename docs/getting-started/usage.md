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

---

## Market lookup (public)

```bash
uv run kalshi market list --status open --limit 20
uv run kalshi market list --event <EVENT_TICKER> --limit 20
uv run kalshi market get <TICKER>
uv run kalshi market orderbook <TICKER> --depth 5
```

---

## Scanning

### Opportunities

```bash
uv run kalshi scan opportunities --filter close-race --top 10 --min-volume 1000 --max-spread 10 --max-pages 10
uv run kalshi scan opportunities --filter high-volume --top 10 --max-pages 10
uv run kalshi scan opportunities --filter wide-spread --top 10 --max-pages 10
uv run kalshi scan opportunities --filter expiring-soon --top 10 --max-pages 10
```

### Movers (requires snapshots in your DB)

```bash
uv run kalshi scan movers --db data/kalshi.db --period 1h --top 10 --max-pages 10
```

### Arbitrage

```bash
uv run kalshi scan arbitrage --db data/kalshi.db --threshold 0.10 --top 10 --tickers-limit 50 --max-pages 10
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
uv run kalshi alerts remove <ALERT_ID_PREFIX>
```

### Monitor

```bash
uv run kalshi alerts monitor --interval 60
uv run kalshi alerts monitor --once --max-pages 10
uv run kalshi alerts monitor --daemon --interval 60
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
uv run kalshi research thesis resolve <THESIS_ID_PREFIX> --outcome yes
```

Backtesting runs on resolved theses using settlement data in the database:

```bash
uv run kalshi data sync-settlements --db data/kalshi.db
uv run kalshi research backtest --start 2024-01-01 --end 2024-12-31 --db data/kalshi.db
```

---

## Portfolio (authenticated)

The CLI loads `.env` automatically. Configure:

- `KALSHI_KEY_ID`
- `KALSHI_PRIVATE_KEY_PATH` or `KALSHI_PRIVATE_KEY_B64`
- `KALSHI_ENVIRONMENT` (`demo` or `prod`; defaults to `prod` if unset; invalid values exit with an error)

### Balance

```bash
uv run kalshi portfolio balance
uv run kalshi portfolio balance --env prod
```

### Sync positions/trades (and compute P&L)

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
- **Auth errors:** confirm your `.env` values; see `docs/developer/configuration.md`.

## See also

- `docs/developer/cli-reference.md`
- `docs/developer/python-api.md`
- `docs/developer/testing.md`
- `docs/architecture/overview.md`
