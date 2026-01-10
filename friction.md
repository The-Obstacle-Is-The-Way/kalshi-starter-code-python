# Friction Log

**Session:** 2026-01-09
**Purpose:** Track CLI friction, bugs, and issues encountered during research session

---

## Confirmed Issues

### 1. BUG-047: Portfolio positions sync shows 0 despite portfolio_value > 0

**Encountered:** 2026-01-09 18:15
**Command:** `uv run kalshi portfolio positions`
**Output:** "No open positions found"
**But:** `portfolio balance` shows portfolio_value = 8822 ($88.22)

**Impact:** Cannot see current positions through CLI. Must query Kalshi API directly or check trades table.

**Workaround:** Calculate net positions from trades table:
```sql
SELECT ticker, side, SUM(CASE WHEN action='buy' THEN quantity ELSE -quantity END) as net
FROM trades GROUP BY ticker, side HAVING net > 0;
```

**Status:** Known bug, tracked in docs/_bugs/BUG-047-portfolio-positions-sync.md

---

## CLI Friction Notes

### Ticker Truncation
- `portfolio history` truncates long tickers with `...`
- Need to query database for full tickers
- Example: `KXNFLAFCCHAMP-25-…` should be queried from `trades` table

---

## Commands That Worked Well

- `kalshi portfolio balance` - Clean output
- `kalshi portfolio history -n 50` - Shows trades correctly

---

## To Investigate

- [ ] Why positions sync fails but balance works
- [ ] Full ticker names for truncated entries

---

## Market Scan Friction

### Scanner Shows Illiquid Garbage
- `kalshi scan opportunities` returns multivariate sports markets with 0 volume and 98¢ spreads
- Need better filtering to exclude KXMVE (multivariate) markets
- Should prioritize by volume AND spread quality

### Database Sync Dominated by Sports Parlays
- `data sync-markets --max-pages 10` syncs 10,000 markets
- ~15,000 are KXMVE (multivariate sports parlays)
- Interesting political/economic markets not captured in default sync
- **Workaround:** Query API directly with `mve_filter=exclude`

### Missing Category Filter
- `markets` table has `category` column but it's empty
- Cannot filter by Politics/Economics/AI in database
- Need to use event_ticker patterns (KXFED, KXTRUMP, KXBTC, etc.)

---

## API Notes

### Useful Event Ticker Patterns
- `KXFED*` - Federal Reserve markets
- `KXTRUMP*` - Trump administration markets
- `KXBTCD-*` - Bitcoin daily price markets
- `KXOAIANTH*` - OpenAI vs Anthropic
- `KXSB-*` - Super Bowl
- `KXNCAAFSPREAD-*` - College football spreads

### Good Query for Non-Sports Markets
```bash
# Use mve_filter=exclude to skip multivariate parlays
GET /markets?status=open&limit=500&mve_filter=exclude
```
