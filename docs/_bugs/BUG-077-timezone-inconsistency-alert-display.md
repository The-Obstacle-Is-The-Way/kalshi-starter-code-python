# BUG-077: Timezone Inconsistency in Alert Monitor Display

**Status:** Open
**Priority:** P4 (Cosmetic)
**Created:** 2026-01-13
**Found by:** Deep Audit
**Effort:** ~5 min

---

## Summary

The alert monitor display uses `datetime.now()` without timezone, while the rest of the codebase consistently uses `datetime.now(UTC)`.

---

## Impact

- **Severity:** Low - Display-only issue
- **Financial Impact:** None
- **User Impact:** Minor confusion if user is not in local timezone

The timestamp shown in alert notifications uses local time instead of UTC, inconsistent with other CLI output.

---

## Root Cause

At `src/kalshi_research/cli/alerts.py:191`:

```python
console.print(
    f"\n[green]✓[/green] {len(alerts)} alert(s) triggered at {datetime.now()}"
)
```

Should be:

```python
console.print(
    f"\n[green]✓[/green] {len(alerts)} alert(s) triggered at {datetime.now(UTC)}"
)
```

---

## Reproduction

```bash
# Start alert monitor
uv run kalshi alerts monitor

# Wait for alert to trigger
# Observe timestamp in output - uses local time, not UTC
```

---

## Fix

Change line 191 of `cli/alerts.py`:

```diff
- f"\n[green]✓[/green] {len(alerts)} alert(s) triggered at {datetime.now()}"
+ f"\n[green]✓[/green] {len(alerts)} alert(s) triggered at {datetime.now(UTC)}"
```

Note: UTC is already imported at line 8.

---

## Verification

1. Run `uv run kalshi alerts monitor`
2. Trigger an alert
3. Confirm timestamp shows UTC (ends with `+00:00`)
