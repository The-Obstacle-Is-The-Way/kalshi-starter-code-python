# BUG-006: Missing Alerts System

**Priority:** P1
**Status:** Fixed
**Discovered:** 2026-01-06
**Fixed:** 2026-01-07
**Spec Reference:** Original CONTEXT FOR CLAUDE, SPEC-005 (new)

---

## Summary

The user explicitly requested an alerts system: "notify me when conditions met". The alerts module and CLI commands are now implemented with unit + CLI integration coverage.

## User's Original Request

From CONTEXT FOR CLAUDE:
```
├── alerts.py            # NEW - notify me when conditions met
```

And under "Key Research Features":
> "Notify me when conditions met"

## Expected Behavior

A system to:
1. Define alert conditions (price thresholds, spread changes, volume spikes)
2. Monitor markets against those conditions
3. Notify the user when conditions are triggered
4. Support multiple notification channels (console, file, optionally email/webhook)

## Current Behavior

Alerting infrastructure exists:

- `src/kalshi_research/alerts/conditions.py`: condition + alert models
- `src/kalshi_research/alerts/monitor.py`: condition evaluation + notifier fanout
- `src/kalshi_research/alerts/notifiers.py`: console/file/webhook channels
- `src/kalshi_research/cli.py`: `kalshi alerts add/list/remove/monitor` with JSON persistence (`data/alerts.json`)
- Tests:
  - `tests/unit/alerts/`
  - `tests/integration/cli/test_cli_commands.py::test_alerts_commands`

## Root Cause

The alerts system was originally missing; it has now been implemented and covered by tests.

## Impact

- **HIGH** - User cannot be notified when research conditions trigger
- This was explicitly requested in the original context
- Makes the platform passive-only (must manually check for opportunities)

## Fix

Implemented `src/kalshi_research/alerts/` modules and CLI integration per SPEC-005.

## Acceptance Criteria

- [x] `alerts/` module exists with conditions, monitor, notifiers
- [x] Can define alert conditions programmatically
- [x] AlertMonitor checks markets against conditions
- [x] ConsoleNotifier prints alerts to terminal with Rich formatting
- [x] FileNotifier logs alerts to JSON file
- [x] CLI command `kalshi alerts` to manage/view alerts
- [x] Tests cover alerts module behavior
- [x] mypy --strict passes
