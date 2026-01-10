# DEBT-009: Finish Halfway Implementations

**Status:** 🔴 Active
**Priority:** P3
**Owner:** TBD
**Created:** 2026-01-10
**Audit Source:** [`bloat.md`](bloat.md)

## Summary

Several valuable features were implemented in the core logic but never wired into the CLI or configuration. These are "Halfway Implementations"—functional code that is currently unreachable by the user.

## Scope (Wire In or Document)

### 1. Alerts Notifiers
- **Files:** `src/kalshi_research/alerts/notifiers.py`
- **Items:** `FileNotifier`, `WebhookNotifier`
- **Current State:** Classes exist and are tested, but CLI `kalshi alerts watch` only uses `ConsoleNotifier`.
- **Action:**
    - Add `--output-file <path>` to `kalshi alerts watch`.
    - Add `--webhook-url <url>` to `kalshi alerts watch`.
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

## Success Criteria

- All "Halfway" items are either reachable via CLI/Config OR explicitly marked as `# RESERVED` / `# TODO` if they are to be deferred further.
- No functional code should exist that is impossible to execute.
