# DEBT-009: Finish Halfway Implementations

**Status:** 🔴 Active
**Priority:** P3
**Owner:** TBD
**Created:** 2026-01-10
**Last Verified:** 2026-01-10
**Audit Source:** [`bloat.md`](bloat.md)

## Summary

Several valuable features were implemented in the core logic but never wired into the CLI or configuration. These are "Halfway Implementations"—functional code that is currently unreachable by the user.

## Scope (Wire In or Document)

### 1. Alerts Notifiers
- **Files:** `src/kalshi_research/alerts/notifiers.py`
- **Items:** `FileNotifier`, `WebhookNotifier`
- **Current State:** Classes exist and are tested, but CLI `kalshi alerts monitor` only uses `ConsoleNotifier`.
- **Action:**
    - Add `--output-file <path>` to `kalshi alerts monitor`.
    - Add `--webhook-url <url>` to `kalshi alerts monitor`.
    - Instantiate the respective notifiers when flags are present.

### 2. Trade History Sync
- **File:** `src/kalshi_research/api/client.py`
- **Item:** `get_trades()`
- **Current State:** Client method wraps `GET /markets/trades`, but no CLI command exposes it.
- **Action:**
    - Create `kalshi data sync-trades --ticker <ticker>` command.
    - Persist results to a new `trades` table or CSV export.

### 3. Exa "Find Similar"
- **File:** `src/kalshi_research/exa/client.py`
- **Item:** `find_similar()`
- **Current State:** Client method wraps Exa's `findSimilar` endpoint.
- **Action:**
    - Create `kalshi research similar <url>` command.

### 4. Market Open Verification
- **File:** `src/kalshi_research/analysis/scanner.py`
- **Item:** `verify_market_open`
- **Current State:** Implements custom logic but doesn't check the official `GET /exchange/status` endpoint.
- **Action:**
    - Update `verify_market_open` to optionally check `client.get_exchange_status()` to respect exchange-wide halts.

### 5. Candlestick History
- **File:** `src/kalshi_research/api/client.py`
- **Items:** `get_candlesticks()`, `get_series_candlesticks()`
- **Current State:** Client methods wrap `GET /markets/{ticker}/candlesticks` and `GET /markets/candlesticks`, but no CLI exposes them.
- **Action:**
    - Create `kalshi market history <ticker> [--interval 1h|1d]` command for single market.
    - Consider `kalshi data export-candlesticks` for batch export.

### 6. Exchange Status Check
- **File:** `src/kalshi_research/api/client.py`
- **Item:** `get_exchange_status()`
- **Current State:** Client method wraps `GET /exchange/status`, but not integrated into trading safety checks.
- **Action:**
    - Wire into `MarketStatusVerifier` (TODO-007) when implemented.
    - Consider `kalshi status` command for operational visibility.

### 7. Exa Deep Research
- **File:** `src/kalshi_research/exa/client.py`
- **Items:** `create_research_task()`, `wait_for_research()`
- **Current State:** Client methods wrap Exa's async research API, but no CLI exposes them.
- **Action:**
    - Create `kalshi research deep <topic> [--wait]` command.
    - Consider cost implications (Exa API usage).

### 8. WebSocket Real-time Data
- **File:** `src/kalshi_research/api/websocket/client.py`
- **Items:** `subscribe_orderbook()`, `subscribe_ticker()`, `subscribe_trade()`
- **Current State:** Full WebSocket client exists but isn't exposed via CLI or used by any feature.
- **Action:**
    - Decision needed: Wire into `kalshi stream <ticker>` command OR extract to optional package.
    - If not wiring in, add `# RESERVED: future real-time features` comment.

## Success Criteria

- All "Halfway" items are either reachable via CLI/Config OR explicitly marked as `# RESERVED` / `# TODO` if they are to be deferred further.
- No functional code should exist that is impossible to execute.
