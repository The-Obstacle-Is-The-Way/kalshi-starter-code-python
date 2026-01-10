# DEBT-009: Finish Halfway Implementations

**Status:** ✅ Resolved
**Priority:** P3
**Owner:** TBD
**Created:** 2026-01-10
**Last Verified:** 2026-01-10
**Resolved:** 2026-01-10
**Audit Source:** [`bloat.md`](../../_debt/bloat.md)

## Summary

Several valuable features were implemented in the core logic but never wired into the CLI or configuration. These are "Halfway Implementations"—functional code that is currently unreachable by the user.

## Scope (Wire In or Document)

### 1. Alerts Notifiers
- **Files:** `src/kalshi_research/alerts/notifiers.py`
- **Items:** `FileNotifier`, `WebhookNotifier`
- **Resolution:** Wired into `kalshi alerts monitor` via `--output-file` and `--webhook-url`.
- **Files Changed:** `src/kalshi_research/cli/alerts.py`, `tests/unit/cli/test_alerts.py`

### 2. Trade History Sync
- **File:** `src/kalshi_research/api/client.py`
- **Item:** `get_trades()`
- **Resolution:** Added `kalshi data sync-trades` with `--output` (CSV) and `--json` (stdout) modes.
- **Files Changed:** `src/kalshi_research/cli/data.py`, `tests/unit/cli/test_data.py`

### 3. Exa "Find Similar"
- **File:** `src/kalshi_research/exa/client.py`
- **Item:** `find_similar()`
- **Resolution:** Added `kalshi research similar <url>`.
- **Files Changed:** `src/kalshi_research/cli/research.py`, `tests/unit/cli/test_research.py`

### 4. Market Open Verification
- **File:** `src/kalshi_research/analysis/scanner.py`
- **Item:** `verify_market_open`
- **Resolution:** `MarketStatusVerifier` now supports optional `exchange_status` and `scan opportunities` fetches
  `/exchange/status` to respect exchange-wide halts when available.
- **Files Changed:** `src/kalshi_research/analysis/scanner.py`, `src/kalshi_research/cli/scan.py`

### 5. Candlestick History
- **File:** `src/kalshi_research/api/client.py`
- **Items:** `get_candlesticks()`, `get_series_candlesticks()`
- **Resolution:** Added `kalshi market history <ticker>` with `--series`, `--interval`, `--start-ts`/`--end-ts`, `--json`.
- **Files Changed:** `src/kalshi_research/cli/market.py`, `tests/unit/cli/test_market.py`

### 6. Exchange Status Check
- **File:** `src/kalshi_research/api/client.py`
- **Item:** `get_exchange_status()`
- **Resolution:** Added `kalshi status` for operational visibility; `scan opportunities` now uses exchange status.
- **Files Changed:** `src/kalshi_research/cli/__init__.py`, `tests/unit/cli/test_app.py`

### 7. Exa Deep Research
- **File:** `src/kalshi_research/exa/client.py`
- **Items:** `create_research_task()`, `wait_for_research()`
- **Resolution:** Added `kalshi research deep <topic> [--wait] [--schema <json>]`.
- **Files Changed:** `src/kalshi_research/cli/research.py`, `tests/unit/cli/test_research.py`

### 8. WebSocket Real-time Data
- **File:** `src/kalshi_research/api/websocket/client.py`
- **Items:** `subscribe_orderbook()`, `subscribe_ticker()`, `subscribe_trade()`
- **Resolution:** Deferred; module explicitly marked `# RESERVED` for future real-time CLI/daemon features.
- **Files Changed:** `src/kalshi_research/api/websocket/client.py`

## Success Criteria

- ✅ All "Halfway" items are either reachable via CLI/Config OR explicitly marked as `# RESERVED`.
- ✅ No functional code remains impossible to execute without an explicit deferment note.
