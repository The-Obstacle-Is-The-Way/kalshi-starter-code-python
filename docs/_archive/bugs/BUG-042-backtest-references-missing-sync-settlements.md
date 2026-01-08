# BUG-042: Backtest references missing `data sync-settlements` command (P1)

**Priority:** P1 (Feature broken: backtesting cannot be unblocked via documented CLI)
**Status:** 🟢 Fixed (2026-01-08)
**Found:** 2026-01-08
**Area:** `src/kalshi_research/cli.py`, `src/kalshi_research/data/`

---

## Summary

`kalshi research backtest` instructs users to run `kalshi data sync-settlements`, but the CLI has no such command and
the data layer has no settlements sync orchestrator. This is a broken user flow: the backtester queries the
`settlements` table, but there is no supported way to populate it.

---

## Evidence / Reproduction

- Message exists in CLI:
  - `src/kalshi_research/cli.py`: prints `Run 'kalshi data sync-settlements' to fetch settlement data.`
- There is no `@data_app.command("sync-settlements")` in `src/kalshi_research/cli.py`.
- `Settlement` ORM model exists and backtest queries it:
  - `src/kalshi_research/data/models.py` (`Settlement`)
  - `src/kalshi_research/cli.py` (`research backtest` selects `Settlement` rows)

---

## Root Cause

The `settlements` storage model exists, but the ingestion path was never implemented/wired into the CLI.

---

## Ironclad Fix

- Add a `SettlementRepository.upsert(...)` method (matching existing repo patterns).
  - File: `src/kalshi_research/data/repositories/settlements.py`
- Implement `DataFetcher.sync_settlements(...)` to fetch `status=settled` markets and materialize `Settlement` rows.
  - File: `src/kalshi_research/data/fetcher.py`
  - `settled_at` is stored using `Market.expiration_time` as an explicit proxy.
- Add CLI command: `kalshi data sync-settlements [--db PATH] [--max-pages N]`.
  - File: `src/kalshi_research/cli.py`

---

## Acceptance Criteria

- [x] `uv run kalshi data sync-settlements --db ...` populates `settlements` rows.
- [x] `kalshi research backtest` no longer points to a nonexistent command.
- [x] Unit tests cover the new CLI command wiring and settlement upsert behavior.
- [x] `uv run pre-commit run --all-files` passes.
- [x] `uv run pytest -m "not integration and not slow"` passes.
