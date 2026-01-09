# BUG-028: `kalshi alerts monitor --once` UX issue (P2)

**Priority:** P2 (Automation/usability regression)
**Status:** 🟢 Fixed (2026-01-07)
**Found:** 2026-01-07
**Spec:** SPEC-005-alerts-notifications.md, SPEC-010-cli-completeness.md
**Checklist Ref:** code-audit-checklist.md Section 11 (Incomplete Implementations)

---

## Summary

`kalshi alerts monitor` advertises a `--once` option ("Run a single check cycle and exit"), but:

1. The command prints "Press Ctrl+C to stop" even when `--once=True` (misleading UX)
2. The `get_all_markets()` call inside the loop can take a VERY long time due to BUG-027 pagination
   (100+ pages), making it seem "stuck" when it's actually iterating

---

## Reproduction

```bash
uv run kalshi alerts monitor --once --interval 1
```

Expected:

- Runs one evaluation pass and exits with code `0` quickly.

Actual:

- Prints "Press Ctrl+C to stop" (misleading for `--once` mode)
- Takes a long time due to iterating 100k+ markets
- Eventually exits (the `once` check at line 1006 is correct)

---

## Root Cause

**Code Analysis (cli.py lines 983-1014):**

```python
console.print(f"[green]✓[/green] Monitoring {len(conditions_data)} alerts (checking every {interval}s)")
console.print("[dim]Press Ctrl+C to stop[/dim]\n")  # BUG: Printed even when once=True

async def _monitor_loop() -> None:
    async with KalshiPublicClient() as client:
        try:
            while True:
                # This takes a LONG time (100k+ markets due to BUG-027)
                markets = [m async for m in client.get_all_markets(status="open")]

                alerts = await monitor.check_conditions(markets)
                # ...
                if once:  # This IS checked correctly
                    return
```

**Issues:**
1. "Press Ctrl+C to stop" printed unconditionally (should skip when `once=True`)
2. No progress indicator during long `get_all_markets()` call
3. Should use `max_pages=None` to avoid truncation (depends on BUG-027 fix)

---

## Impact

- Misleading UX for `--once` mode
- Cannot easily use in cron/CI (appears stuck)
- No feedback during long-running market fetch

---

## Ironclad Fix Specification

**File:** `src/kalshi_research/cli.py`

**Changes to `alerts_monitor` command (lines 983-1014):**

```python
console.print(
    f"[green]✓[/green] Monitoring {len(conditions_data)} alerts "
    f"{'(single check)' if once else f'(checking every {interval}s)'}"
)

if not once:  # FIX: Only show Ctrl+C message for continuous mode
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
else:
    console.print("[dim]Running single check...[/dim]\n")

async def _monitor_loop() -> None:
    async with KalshiPublicClient() as client:
        try:
            while True:
                # FIX: Show progress during market fetch
                console.print("[dim]Fetching markets...[/dim]", end="")
                markets = [m async for m in client.get_all_markets(status="open")]
                console.print(f"[dim] ({len(markets)} markets)[/dim]")

                alerts = await monitor.check_conditions(markets)

                if alerts:
                    console.print(
                        f"\n[green]✓[/green] {len(alerts)} alert(s) triggered at "
                        f"{datetime.now()}"
                    )

                if once:
                    console.print("[green]✓[/green] Single check complete")
                    return

                await asyncio.sleep(interval)
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped[/yellow]")
```

---

## Acceptance Criteria

- [x] `--once` mode does NOT print "Press Ctrl+C to stop"
- [x] `--once` mode prints "Running single check..." and "Single check complete"
- [x] Progress shown during market fetch ("Fetching markets... (N markets)")
- [x] `kalshi alerts monitor --once` exits after one cycle (unit test: `tests/unit/test_cli_extended.py::test_alerts_monitor_once_exits`)
- [x] Continuous mode still shows Ctrl+C message (unit test: `tests/unit/test_cli_extended.py::test_alerts_monitor_continuous_shows_ctrl_c`)

---

## Test Plan

```python
def test_alerts_monitor_once_exits(
    cli_runner: CliRunner,
    mock_public_client: MagicMock,
) -> None:
    """--once mode should exit after single check."""
    mock_public_client.get_all_markets.return_value = async_iter([])

    result = cli_runner.invoke(app, ["alerts", "monitor", "--once"])

    assert result.exit_code == 0
    assert "Press Ctrl+C" not in result.output
    assert "Single check complete" in result.output


def test_alerts_monitor_continuous_shows_ctrl_c(
    cli_runner: CliRunner,
) -> None:
    """Continuous mode should show Ctrl+C message."""
    # Mock to immediately raise KeyboardInterrupt
    with patch("asyncio.sleep", side_effect=KeyboardInterrupt):
        result = cli_runner.invoke(app, ["alerts", "monitor", "--interval", "1"])

    assert "Press Ctrl+C" in result.output
```
