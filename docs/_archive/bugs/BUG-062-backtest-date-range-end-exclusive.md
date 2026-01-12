# BUG-062: Backtest Date Range End-Date Excludes Full Day

**Priority:** P2 (Medium - correctness / UX)
**Status:** ✅ Fixed
**Found:** 2026-01-10
**Fixed:** 2026-01-10
**Owner:** Platform

---

## Summary

`kalshi research backtest --start YYYY-MM-DD --end YYYY-MM-DD` treats `--end` as **midnight at the start
of the end date**, so settlements that occur later on the end date are excluded.

This is an **off-by-one day** behavior that can make backtests undercount (or incorrectly show “No
settlements found”) for the specified range.

---

## Evidence (SSOT)

### 1) Date parsing produces midnight datetimes

`src/kalshi_research/cli/research.py` parses the CLI inputs using `datetime.fromisoformat()`:

- `start_dt = datetime.fromisoformat(start)`
- `end_dt = datetime.fromisoformat(end)`

When users follow the printed guidance (“Use `YYYY-MM-DD` format”), `datetime.fromisoformat("YYYY-MM-DD")`
returns a datetime at `00:00:00` (start of day).

### 2) DB query uses inclusive `<= end_dt`

`src/kalshi_research/cli/research.py` filters settlements using:

- `Settlement.settled_at >= start_dt`
- `Settlement.settled_at <= end_dt`

This excludes all settlements occurring on the end date after midnight.

---

## Impact

- Backtest results can be silently wrong for common inputs (date-only end ranges).
- Users may be told “No settlements found between X and Y” when settlements exist on day `Y`.
- Trust in analysis tooling drops (a “looks like it works” but is systematically biased problem).

---

## Repro (Minimal)

1. Insert any settlement with `settled_at = 2024-06-30T12:00:00+00:00`
2. Run:

```bash
uv run kalshi research backtest --start 2024-01-01 --end 2024-06-30
```

Expected: the settlement is included.

Actual: it is excluded because `end_dt == 2024-06-30T00:00:00` (start of day).

---

## Fix Plan

Treat date-only inputs as an **inclusive day-range in UTC** by converting to an **exclusive** end bound.

Recommended approach:

1. Parse `start`/`end` as `date` (strict `YYYY-MM-DD`).
2. Convert to UTC datetimes:
   - `start_dt = datetime.combine(start_date, time.min, tzinfo=UTC)`
   - `end_dt_exclusive = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)`
3. Query:
   - `Settlement.settled_at >= start_dt`
   - `Settlement.settled_at < end_dt_exclusive`

Optional improvements:
- Support ISO 8601 datetimes (with timezone) in addition to `YYYY-MM-DD`, but keep semantics explicit.
- Populate `BacktestResult.period_start/period_end` using the actual requested range rather than `now`.

---

## Acceptance Criteria

- [x] `--end YYYY-MM-DD` includes all settlements on that end date (UTC) by default.
- [x] CLI help text clearly describes date semantics (inclusive start/end).
- [x] Unit test covers boundary behavior (settlement on end date at noon is included).
- [x] `uv run pre-commit run --all-files` passes.

---

## Resolution

- Updated `kalshi research backtest` to parse `--start/--end` as UTC date ranges (inclusive end-date).
- Query now uses `< end_dt_exclusive` instead of `<= end_dt` for correct end-date inclusion.
- Added unit coverage: `tests/unit/cli/test_research.py::test_parse_backtest_dates_includes_end_date`.
