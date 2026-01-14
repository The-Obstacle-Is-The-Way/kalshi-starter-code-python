# BUG-077: Timezone Inconsistency in Alert Monitor Display

**Priority:** P4 (Cosmetic)
**Status:** ✅ Fixed
**Found:** 2026-01-13
**Verified:** 2026-01-14 - Manual run + code inspection
**Fixed:** 2026-01-14
**Affected Code:** `_run_alert_monitor_loop()` in `src/kalshi_research/cli/alerts.py`

---

## Summary

`kalshi alerts monitor` printed a timezone-naive timestamp via `datetime.now()` when alerts triggered, which was
inconsistent with the rest of the CLI’s UTC timestamps.

---

## Root Cause

The alert monitor printed local time:

```python
console.print(
    f"... triggered at {datetime.now()}"
)
```

---

## Fix

Use a timezone-aware UTC timestamp:

```python
console.print(
    f"... triggered at {datetime.now(UTC)}"
)
```

---

## Verification

1. Run `uv run kalshi alerts monitor`
2. Trigger an alert
3. Confirm the printed timestamp includes `+00:00`
