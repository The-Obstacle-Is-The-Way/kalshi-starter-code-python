# DEBT-011: Unbounded Disk Growth (DB Snapshots, Logs, Caches)

**Priority:** P2 (Operational reliability / performance risk)
**Status:** ✅ Complete
**Created:** 2026-01-10
**Last Verified:** 2026-01-10
**Resolved:** 2026-01-10

---

## Summary

The platform intentionally supports long-running collection modes (e.g., periodic market snapshots and alert
monitoring). Today, several storage surfaces can grow without bound:

- SQLite database tables (especially `price_snapshots`, `news_articles`, related joins)
- Alert daemon log file (`data/alert_monitor.log`)
- Exa response cache directory (`data/exa_cache/*.json`)

This is acceptable for short-lived experimentation, but becomes a reliability/performance risk as soon as
`kalshi data collect` (or similar periodic jobs) run over weeks/months.

---

## Evidence (SSOT)

### 1) Price snapshots accumulate indefinitely

- `src/kalshi_research/cli/data.py` implements `data collect` which periodically calls
  `DataFetcher.take_snapshot(...)` on an interval.
- There is no pruning/retention command in `src/kalshi_research/cli/` (confirmed via grep for “prune/vacuum/retention”).

### 2) Alert monitor log file appends forever

- `src/kalshi_research/cli/alerts.py` spawns the daemon and opens `_ALERT_MONITOR_LOG_PATH` with mode `"a"`.
- No rotation / max-size policy is implemented.

### 3) Exa cache grows unless explicitly cleared

- `src/kalshi_research/exa/cache.py` stores responses to `data/exa_cache/*.json` with TTLs.
- Entries are evicted on read when expired, but expired entries can persist if they’re never read again.
- No CLI command exists to clear cache or clear expired entries.

---

## Why This Matters

**Failure modes:**
- Disk fills (agent crash / CLI failures / OS issues)
- SQLite performance degradation as tables grow (query latency, larger exports)
- Developer confusion when local DB becomes huge and slow without an obvious cleanup path

This is a classic “it works until it doesn’t” operational gap.

---

## Fix Plan (Clean, Minimal, SSOT-Aligned)

### 1) Add explicit retention commands (CLI-first)

Implement `kalshi data prune` with conservative defaults and explicit flags. Example scope:

- `--snapshots-older-than-days N` (delete `price_snapshots` older than N days)
- `--news-older-than-days N` (delete old `news_articles` + join rows + sentiments)
- `--settlements-older-than-days N` (optional; usually keep indefinitely)
- `--dry-run/--apply` parity with `kalshi data migrate`

### 2) Provide a “vacuum” maintenance option

After large deletes, optionally run SQLite `VACUUM` (with a warning about locking/time).

### 3) Add cache maintenance commands

Implement `kalshi research cache clear` (or `kalshi exa cache clear`) with:

- `--expired-only` (calls `ExaCache.clear_expired()`)
- `--all` (calls `ExaCache.clear()`)

### 4) Log rotation (minimal)

Add a size cap for `data/alert_monitor.log`:

- If file > N MB, rotate to `.1`, `.2` (keep last K files), or truncate with a warning.
- Keep this opt-in if desired (env var / flag), but provide a clear default recommendation.

---

## Acceptance Criteria

- [x] CLI offers a supported path to prune `price_snapshots` and news tables (dry-run default).
- [x] Exa cache can be cleared/expired-cleared via CLI.
- [x] Documentation explains expected data growth and recommended maintenance cadence.
- [x] Unit/integration tests cover the prune selection logic on a temporary DB.
- [x] Quality gates pass: `ruff`, `mypy`, `pytest`.

---

## Implementation Notes (2026-01-10)

**New commands:**
- `kalshi data prune` (dry-run default; explicit prune targets via `--snapshots-older-than-days` / `--news-older-than-days`)
- `kalshi data vacuum` (manual `VACUUM` after large deletes)
- `kalshi research cache clear` / `kalshi research cache clear --all`
- `kalshi alerts trim-log` (dry-run default; manual log trimming)

**Core logic:**
- `src/kalshi_research/data/maintenance.py` (`compute_prune_counts`, `apply_prune`)

**Tests:**
- `tests/unit/data/test_maintenance.py`
