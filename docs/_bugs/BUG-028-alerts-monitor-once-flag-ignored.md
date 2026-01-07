# BUG-028: `kalshi alerts monitor --once` does not exit (P2)

**Priority:** P2 (Automation/usability regression)
**Status:** 🟡 Open
**Found:** 2026-01-07
**Spec:** SPEC-005-alerts-notifications.md, SPEC-010-cli-completeness.md

---

## Summary

`kalshi alerts monitor` advertises a `--once` option (“Run a single check cycle and exit”), but the command
continues running indefinitely and requires manual Ctrl+C.

---

## Reproduction

```bash
uv run kalshi alerts monitor --once --interval 1
```

Expected:

- Runs one evaluation pass and exits with code `0`.

Actual:

- Prints “Press Ctrl+C to stop” and keeps running.

---

## Root Cause

The monitor loop likely ignores `once` and always enters an infinite loop (or never breaks after the first pass).

---

## Impact

- Cannot be used in cron/CI or scripted workflows.
- Harder to integration test alert evaluation deterministically.

---

## Proposed Fix

- Implement `--once` as “evaluate all alerts once, then exit”.
- Add a regression test using `CliRunner` and a patched client to avoid live network.

---

## Acceptance Criteria

- `uv run kalshi alerts monitor --once` exits within one cycle with code `0`.
- `uv run kalshi alerts monitor --interval 1` continues running until interrupted.

