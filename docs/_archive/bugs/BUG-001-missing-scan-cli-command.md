# BUG-001: Missing `scan` CLI Command

**Priority:** P1
**Status:** ✓ FIXED (2026-01-06)
**Discovered:** 2026-01-06
**Spec Reference:** PROMPT.md Phase 4, SPEC-004

---

## Summary

The CLI is missing the `scan` command required by PROMPT.md Phase 4. The underlying `MarketScanner` class exists in `src/kalshi_research/analysis/scanner.py` but is not exposed via CLI.

## Expected Behavior

Per PROMPT.md Phase 4 requirements:
```bash
kalshi scan --help
kalshi scan opportunities --filter close-race
kalshi scan opportunities --filter high-volume
kalshi scan opportunities --filter wide-spread
kalshi scan opportunities --filter expiring-soon
```

## Current Behavior

```bash
$ kalshi --help
# Shows: version, data, market
# Missing: scan
```

## Root Cause

The `scan` subcommand was never added to `cli.py`. The `MarketScanner` class is fully implemented but not integrated into the CLI.

## Fix

Add `scan_app` typer subgroup to `cli.py`:

```python
scan_app = typer.Typer(help="Market scanning commands.")
app.add_typer(scan_app, name="scan")

@scan_app.command("opportunities")
def scan_opportunities(
    filter_type: Annotated[
        str | None,
        typer.Option("--filter", "-f", help="Filter type: close-race, high-volume, wide-spread, expiring-soon"),
    ] = None,
    top_n: Annotated[int, typer.Option("--top", "-n", help="Number of results")] = 10,
) -> None:
    """Scan markets for opportunities."""
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.analysis.scanner import MarketScanner, ScanFilter

    async def _scan() -> None:
        async with KalshiPublicClient() as client:
            markets = [m async for m in client.get_all_markets(status="open")]

        scanner = MarketScanner()

        if filter_type:
            filter_map = {
                "close-race": scanner.scan_close_races,
                "high-volume": scanner.scan_high_volume,
                "wide-spread": scanner.scan_wide_spread,
                "expiring-soon": scanner.scan_expiring_soon,
            }
            results = filter_map[filter_type](markets, top_n)
            # Display results...
        else:
            all_results = scanner.scan_all(markets, top_n)
            # Display all results...

    asyncio.run(_scan())
```

## Acceptance Criteria

- [x] `kalshi scan --help` shows available scan subcommands
- [x] `kalshi scan opportunities --filter close-race` runs successfully
- [x] `kalshi scan opportunities --filter high-volume` runs successfully
- [x] `kalshi scan opportunities --filter wide-spread` runs successfully
- [x] `kalshi scan opportunities --filter expiring-soon` runs successfully
- [x] Results are displayed in a formatted Rich table (or a clear "no markets found" message)
