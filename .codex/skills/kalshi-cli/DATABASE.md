# Database Reference

SQLite database schema and common queries. The database is the authoritative source when CLI options are insufficient.

---

## Connection

```bash
sqlite3 data/kalshi.db "YOUR QUERY"
```

Or for interactive mode:
```bash
sqlite3 data/kalshi.db
```

---

## Schema

### events
Market events/categories that group related markets.

| Column | Type | Description |
|--------|------|-------------|
| `ticker` | VARCHAR (PK) | Event identifier |
| `series_ticker` | VARCHAR | Series identifier |
| `title` | VARCHAR | Event title |
| `status` | VARCHAR | Event status |
| `category` | VARCHAR | Category name |
| `mutually_exclusive` | BOOLEAN | Whether markets are mutually exclusive |
| `created_at` | DATETIME | Creation timestamp |
| `updated_at` | DATETIME | Last update timestamp |

### markets
Individual prediction markets.

| Column | Type | Description |
|--------|------|-------------|
| `ticker` | VARCHAR (PK) | Market identifier |
| `event_ticker` | VARCHAR (FK) | Parent event |
| `series_ticker` | VARCHAR | Series identifier |
| `title` | VARCHAR | Market title |
| `subtitle` | VARCHAR | Market subtitle |
| `status` | VARCHAR | `active`, `closed`, `determined`, `finalized` |
| `result` | VARCHAR | `yes`, `no`, `void`, or NULL |
| `open_time` | DATETIME | When market opened |
| `close_time` | DATETIME | When market closes |
| `expiration_time` | DATETIME | When market expires |
| `category` | VARCHAR | Category |
| `subcategory` | VARCHAR | Subcategory |
| `created_at` | DATETIME | Creation timestamp |
| `updated_at` | DATETIME | Last update timestamp |

**Indexes**: `idx_markets_event`, `idx_markets_expiration`, `idx_markets_status`

### price_snapshots
Historical price data for backtesting and analysis.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-increment ID |
| `ticker` | VARCHAR (FK) | Market ticker |
| `snapshot_time` | DATETIME | When snapshot was taken |
| `yes_bid` | INTEGER | Best YES bid (cents) |
| `yes_ask` | INTEGER | Best YES ask (cents) |
| `no_bid` | INTEGER | Best NO bid (cents) |
| `no_ask` | INTEGER | Best NO ask (cents) |
| `last_price` | INTEGER | Last trade price |
| `volume` | INTEGER | Total volume |
| `volume_24h` | INTEGER | 24-hour volume |
| `open_interest` | INTEGER | Open interest |
| `liquidity` | INTEGER | Liquidity measure |

**Indexes**: `idx_snapshots_ticker_time`, `idx_snapshots_time`

### settlements
Resolved market outcomes for calibration analysis.

| Column | Type | Description |
|--------|------|-------------|
| `ticker` | VARCHAR (PK/FK) | Market ticker |
| `event_ticker` | VARCHAR | Parent event |
| `settled_at` | DATETIME | Settlement timestamp |
| `result` | VARCHAR | `yes`, `no`, or `void` |
| `final_yes_price` | INTEGER | Final YES price (cents) |
| `final_no_price` | INTEGER | Final NO price (cents) |
| `yes_payout` | INTEGER | YES payout (cents) |
| `no_payout` | INTEGER | NO payout (cents) |

### positions
Synced portfolio positions from Kalshi API.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-increment ID |
| `ticker` | VARCHAR(100) | Market ticker |
| `side` | VARCHAR(10) | `yes` or `no` |
| `quantity` | INTEGER | Number of contracts |
| `avg_price_cents` | INTEGER | Average cost basis (FIFO) |
| `current_price_cents` | INTEGER | Current mark price |
| `unrealized_pnl_cents` | INTEGER | Unrealized P&L |
| `realized_pnl_cents` | INTEGER | Realized P&L (default 0) |
| `thesis_id` | INTEGER | Linked thesis ID (optional) |
| `opened_at` | DATETIME | Position open time |
| `closed_at` | DATETIME | Position close time (NULL if open) |
| `last_synced` | DATETIME | Last sync timestamp |

**Indexes**: `idx_positions_ticker`, `idx_positions_thesis`

### trades
Synced trade history from Kalshi API.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-increment ID |
| `kalshi_trade_id` | VARCHAR(100) UNIQUE | Kalshi's trade ID |
| `ticker` | VARCHAR(100) | Market ticker |
| `side` | VARCHAR(10) | `yes` or `no` |
| `action` | VARCHAR(10) | `buy` or `sell` |
| `quantity` | INTEGER | Number of contracts |
| `price_cents` | INTEGER | Trade price (cents) |
| `total_cost_cents` | INTEGER | Total cost |
| `fee_cents` | INTEGER | Fees paid (default 0) |
| `position_id` | INTEGER (FK) | Linked position (optional) |
| `executed_at` | DATETIME | Execution timestamp |
| `synced_at` | DATETIME | When synced to database |

### tracked_items
Markets/events being tracked for news collection.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-increment ID |
| `ticker` | VARCHAR(100) UNIQUE | Market or event ticker |
| `item_type` | VARCHAR(20) | `market` or `event` |
| `search_queries` | TEXT | JSON array of search queries |
| `created_at` | DATETIME | When tracking was created |
| `last_collected_at` | DATETIME | Last collection time |
| `is_active` | BOOLEAN | Whether collection is enabled |

### news_articles
Collected articles returned by Exa.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-increment ID |
| `url` | VARCHAR(2000) UNIQUE | Canonical URL |
| `url_hash` | VARCHAR(64) | SHA256 URL hash |
| `title` | VARCHAR(500) | Article title |
| `source_domain` | VARCHAR(200) | Domain (normalized) |
| `published_at` | DATETIME | Published date (nullable) |
| `collected_at` | DATETIME | Collected timestamp |
| `text_snippet` | TEXT | Highlight/snippet |
| `full_text` | TEXT | Full text (if requested) |
| `exa_request_id` | VARCHAR(100) | Exa request identifier |

### news_article_markets
Many-to-many mapping from articles → markets.

| Column | Type | Description |
|--------|------|-------------|
| `article_id` | INTEGER (FK) | Article ID |
| `ticker` | VARCHAR(100) (FK) | Market ticker |

### news_article_events
Many-to-many mapping from articles → events.

| Column | Type | Description |
|--------|------|-------------|
| `article_id` | INTEGER (FK) | Article ID |
| `event_ticker` | VARCHAR(100) (FK) | Event ticker |

### news_sentiments
Sentiment analysis results for articles.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-increment ID |
| `article_id` | INTEGER (FK) | Article ID |
| `analyzed_at` | DATETIME | Analysis timestamp |
| `score` | FLOAT | Sentiment score (-1..+1) |
| `label` | VARCHAR(20) | `positive`/`negative`/`neutral` |
| `confidence` | FLOAT | 0..1 confidence |
| `method` | VARCHAR(50) | Analysis method |
| `keywords_matched` | TEXT | JSON list of matched keywords |

---

## Common Queries

### Finding Markets

```sql
-- Find markets by keyword (substitute for --search)
SELECT ticker, title, status
FROM markets
WHERE title LIKE '%Super Bowl%' AND status = 'open';

-- Find markets by partial ticker
SELECT ticker, title
FROM markets
WHERE ticker LIKE 'KXFED%';

-- Get all open markets in a category
SELECT ticker, title, close_time
FROM markets
WHERE category = 'Politics' AND status = 'active'
ORDER BY close_time;

-- Find markets expiring soon
SELECT ticker, title, expiration_time
FROM markets
WHERE status = 'active'
  AND expiration_time < datetime('now', '+7 days')
ORDER BY expiration_time;
```

### Trade Analysis

```sql
-- Get all trades sorted by date
SELECT ticker, side, action, quantity, price_cents, executed_at
FROM trades
ORDER BY executed_at DESC
LIMIT 20;

-- Get trades for a specific ticker
SELECT * FROM trades
WHERE ticker = 'KXSB-26-DEN'
ORDER BY executed_at;

-- Calculate net position from trades (when positions table empty)
SELECT
  ticker,
  side,
  SUM(CASE WHEN action='buy' THEN quantity ELSE -quantity END) as net_qty,
  AVG(price_cents) as avg_price
FROM trades
GROUP BY ticker, side
HAVING net_qty > 0;

-- Daily trade volume
SELECT
  date(executed_at) as trade_date,
  COUNT(*) as trade_count,
  SUM(total_cost_cents) / 100.0 as total_usd
FROM trades
GROUP BY date(executed_at)
ORDER BY trade_date DESC;
```

### News Tracking

```sql
-- List tracked items
SELECT ticker, item_type, is_active, last_collected_at
FROM tracked_items
ORDER BY created_at DESC;

-- Recent collected articles
SELECT title, source_domain, published_at, collected_at
FROM news_articles
ORDER BY collected_at DESC
LIMIT 20;

-- Latest sentiment for a specific market
SELECT a.title, s.score, s.label, a.source_domain, a.published_at
FROM news_articles a
JOIN news_article_markets m ON m.article_id = a.id
JOIN news_sentiments s ON s.article_id = a.id
WHERE m.ticker = 'MKT1'
ORDER BY s.analyzed_at DESC
LIMIT 20;
```

### Position Analysis

```sql
-- Get all open positions
SELECT ticker, side, quantity, avg_price_cents, unrealized_pnl_cents
FROM positions
WHERE closed_at IS NULL AND quantity > 0;

-- Positions with linked theses
SELECT p.ticker, p.side, p.quantity, p.thesis_id
FROM positions p
WHERE p.thesis_id IS NOT NULL;

-- Total portfolio value
SELECT
  SUM(quantity * current_price_cents) / 100.0 as portfolio_value_usd,
  SUM(unrealized_pnl_cents) / 100.0 as unrealized_pnl_usd,
  SUM(realized_pnl_cents) / 100.0 as realized_pnl_usd
FROM positions
WHERE closed_at IS NULL;
```

### Price History

```sql
-- Get price history for a market
SELECT snapshot_time, yes_bid, yes_ask, volume_24h
FROM price_snapshots
WHERE ticker = 'KXSB-26-DEN'
ORDER BY snapshot_time DESC
LIMIT 100;

-- Price change over time
SELECT
  ticker,
  MIN(yes_bid) as min_bid,
  MAX(yes_bid) as max_bid,
  MAX(yes_bid) - MIN(yes_bid) as range
FROM price_snapshots
WHERE snapshot_time > datetime('now', '-24 hours')
GROUP BY ticker
ORDER BY range DESC
LIMIT 10;

-- Latest prices for all markets
SELECT DISTINCT ON (ticker)
  ticker, yes_bid, yes_ask, volume_24h, snapshot_time
FROM price_snapshots
ORDER BY ticker, snapshot_time DESC;
```

### Settlement Analysis

```sql
-- Get all settled markets
SELECT ticker, result, settled_at, final_yes_price
FROM settlements
ORDER BY settled_at DESC;

-- Win rate by category
SELECT
  m.category,
  COUNT(*) as total,
  SUM(CASE WHEN s.result = 'yes' THEN 1 ELSE 0 END) as yes_count,
  ROUND(100.0 * SUM(CASE WHEN s.result = 'yes' THEN 1 ELSE 0 END) / COUNT(*), 1) as yes_pct
FROM settlements s
JOIN markets m ON s.ticker = m.ticker
GROUP BY m.category;

-- Markets settled in last 7 days
SELECT s.ticker, m.title, s.result, s.settled_at
FROM settlements s
JOIN markets m ON s.ticker = m.ticker
WHERE s.settled_at > datetime('now', '-7 days')
ORDER BY s.settled_at DESC;
```

### Database Statistics

```sql
-- Table row counts
SELECT 'events' as tbl, COUNT(*) as cnt FROM events
UNION ALL SELECT 'markets', COUNT(*) FROM markets
UNION ALL SELECT 'price_snapshots', COUNT(*) FROM price_snapshots
UNION ALL SELECT 'settlements', COUNT(*) FROM settlements
UNION ALL SELECT 'positions', COUNT(*) FROM positions
UNION ALL SELECT 'trades', COUNT(*) FROM trades
UNION ALL SELECT 'tracked_items', COUNT(*) FROM tracked_items
UNION ALL SELECT 'news_articles', COUNT(*) FROM news_articles
UNION ALL SELECT 'news_sentiments', COUNT(*) FROM news_sentiments;

-- Date range of data
SELECT
  'snapshots' as data_type,
  MIN(snapshot_time) as earliest,
  MAX(snapshot_time) as latest
FROM price_snapshots
UNION ALL
SELECT
  'trades',
  MIN(executed_at),
  MAX(executed_at)
FROM trades;
```

---

## Notes

- All prices are stored in **cents** (1-100 scale)
- Timestamps are stored as ISO 8601 strings with timezone
- The database uses SQLite WAL mode for better concurrent access
- `kalshi_trade_id` is the idempotency key for trades
