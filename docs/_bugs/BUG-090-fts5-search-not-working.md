# BUG-090: `market search` Defaults to Invalid Status Filter (`open`)

## Priority: P2 (Medium)

## Summary
`kalshi market search <QUERY>` returns "No markets found" by default even when matching markets exist in the local database.

Root cause: the command defaults `--status open`, but the local DB stores **API response status values** (e.g., `active`, `initialized`, `closed`, `finalized`), not **filter status values** (e.g., `open`, `unopened`, `settled`).

## Steps to Reproduce
```bash
# Verify the DB contains markets (no network required if you already have data/kalshi.db)
sqlite3 data/kalshi.db "SELECT count(*) FROM markets;"

# Confirm stored status values (these are API response statuses)
sqlite3 data/kalshi.db "SELECT DISTINCT status FROM markets LIMIT 10;"
# Example output: active, initialized, closed, determined, finalized

# Default search uses --status open (filter value), which does not exist in the DB
uv run kalshi market search "MOUZ"
# Output: No markets found.

# Passing a DB status value works
uv run kalshi market search "MOUZ" --status active --top 5 --format json
# Output: JSON results
```

## Expected Behavior
The default invocation should produce results when matches exist (or the CLI should make the status-domain mismatch explicit).

## Actual Behavior
Returns "No markets found." because it filters by `status == "open"` against a DB that stores `status` as `active`/`initialized`/etc.

## Root Cause (Verified)
- `src/kalshi_research/cli/market/search.py` sets `--status` default to `open` and passes it through to the repository.
- `src/kalshi_research/data/repositories/search.py` applies `Market.status == status` in SQL.
- The DB stores API response status values, so `open` never matches.

## Affected Code
- `src/kalshi_research/cli/market/search.py`
- `src/kalshi_research/data/repositories/search.py`

## Workaround
- Pass a response status value explicitly, e.g. `--status active` or `--status initialized`.

## Discovered
2026-01-21 during stress test session

## Status
Open
