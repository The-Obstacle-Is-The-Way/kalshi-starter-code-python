# Remaining Work - Truth vs. Claims Audit

**Audit Date:** 2026-01-07
**Auditor:** Claude (Opus 4.5) - Independent verification

---

## Executive Summary

After deep-diving the codebase, here's what's **actually implemented** vs **claimed/spec'd but not built**:

| Feature | Bug/Spec Tracker Status | Reality |
|---------|------------------------|---------|
| Portfolio Sync | "Fixed" (BUG-019) | ✅ **ACTUALLY WORKS** |
| Demo Environment | SPEC-016 | ✅ **IMPLEMENTED** |
| Bug Fixes (BUG-001 to BUG-039) | All "Fixed" | ✅ **VERIFIED** (spot-checked key ones) |
| WebSocket Real-Time | SPEC-014 | ❌ **SPEC ONLY - NO CODE** |
| Rate Limit Tiers | SPEC-015 | ❌ **SPEC ONLY - NO CODE** |
| Backtest CLI | N/A | ❌ **OUTPUTS MOCK DATA** |
| Order Placement | N/A | ❌ **NOT IMPLEMENTED** |
| Alerts Daemon Mode | BUG-028 | ❌ **NOT IMPLEMENTED** |

---

## ISSUE 1: Backtest CLI Outputs Mock Data (P1)

**File:** `src/kalshi_research/cli.py` (lines 1615-1645)

**Problem:** The `kalshi research backtest` command outputs hardcoded fake results instead of using the actual `ThesisBacktester` class which exists and works.

**Current (broken):**
```python
@research_app.command("backtest")
def research_backtest(start, end, db_path):
    # ... validation ...

    # Mock output for now  <-- THIS IS THE PROBLEM
    table = Table(title="Backtest Results")
    table.add_row("Total Trades", "10")
    table.add_row("Win Rate", "60.0%")
    table.add_row("Total P&L", "$150.00")
    table.add_row("Sharpe Ratio", "1.5")
```

**Fix Required:**

```python
@research_app.command("backtest")
def research_backtest(
    start: Annotated[str, typer.Option("--start", help="Start date (YYYY-MM-DD)")],
    end: Annotated[str, typer.Option("--end", help="End date (YYYY-MM-DD)")],
    thesis_id: Annotated[
        str | None,
        typer.Option("--thesis", "-t", help="Specific thesis ID to backtest"),
    ] = None,
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = Path("data/kalshi.db"),
) -> None:
    """Run backtests on resolved theses using historical settlements."""
    from datetime import datetime
    from sqlalchemy import select
    from kalshi_research.data import DatabaseManager
    from kalshi_research.data.models import Settlement, PriceSnapshot
    from kalshi_research.research.backtest import ThesisBacktester
    from kalshi_research.research.thesis import ThesisManager

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    async def _backtest() -> None:
        db = DatabaseManager(db_path)
        thesis_mgr = ThesisManager()
        backtester = ThesisBacktester()

        try:
            # Parse date range
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)

            # Load theses
            if thesis_id:
                thesis = thesis_mgr.get(thesis_id)
                if not thesis:
                    console.print(f"[red]Error:[/red] Thesis {thesis_id} not found")
                    raise typer.Exit(1)
                theses = [thesis]
            else:
                theses = thesis_mgr.list_all()

            resolved = [t for t in theses if t.status.value == "resolved"]
            if not resolved:
                console.print("[yellow]No resolved theses to backtest[/yellow]")
                return

            # Load settlements from DB
            async with db.session_factory() as session:
                result = await session.execute(
                    select(Settlement).where(
                        Settlement.settled_at >= start_dt,
                        Settlement.settled_at <= end_dt,
                    )
                )
                settlements = list(result.scalars().all())

            if not settlements:
                console.print("[yellow]No settlements found in date range[/yellow]")
                return

            console.print(f"[dim]Backtesting {len(resolved)} theses against {len(settlements)} settlements...[/dim]")

            # Run backtest
            results = await backtester.backtest_all(resolved, settlements)

            if not results:
                console.print("[yellow]No backtest results generated[/yellow]")
                return

            # Display results
            table = Table(title="Backtest Results")
            table.add_column("Thesis ID", style="cyan")
            table.add_column("Trades", justify="right")
            table.add_column("Win Rate", justify="right")
            table.add_column("P&L", justify="right")
            table.add_column("Brier", justify="right")

            for result in results:
                pnl_color = "green" if result.total_pnl >= 0 else "red"
                table.add_row(
                    result.thesis_id[:12],
                    str(result.total_trades),
                    f"{result.win_rate:.1%}",
                    f"[{pnl_color}]{result.total_pnl:+.0f}c[/{pnl_color}]",
                    f"{result.brier_score:.4f}",
                )

            console.print(table)

        finally:
            await db.close()

    asyncio.run(_backtest())
```

---

## ISSUE 2: Order Placement Not Implemented (P2)

**Problem:** There's no way to place trades through the tool. The API client doesn't have order placement methods.

**File to modify:** `src/kalshi_research/api/client.py`

**Methods to add to `KalshiClient` class:**

```python
async def create_order(
    self,
    ticker: str,
    side: Literal["yes", "no"],
    action: Literal["buy", "sell"],
    count: int,
    type: Literal["limit", "market"] = "limit",
    yes_price: int | None = None,
    no_price: int | None = None,
    expiration_ts: int | None = None,
    client_order_id: str | None = None,
) -> dict[str, Any]:
    """
    Place a new order.

    Args:
        ticker: Market ticker
        side: "yes" or "no"
        action: "buy" or "sell"
        count: Number of contracts
        type: "limit" or "market"
        yes_price: Limit price in cents (for YES side)
        no_price: Limit price in cents (for NO side)
        expiration_ts: Unix timestamp for order expiration
        client_order_id: Client-provided order ID for idempotency

    Returns:
        Order response from API
    """
    payload: dict[str, Any] = {
        "ticker": ticker,
        "side": side,
        "action": action,
        "count": count,
        "type": type,
    }
    if yes_price is not None:
        payload["yes_price"] = yes_price
    if no_price is not None:
        payload["no_price"] = no_price
    if expiration_ts is not None:
        payload["expiration_ts"] = expiration_ts
    if client_order_id is not None:
        payload["client_order_id"] = client_order_id

    return await self._auth_post("/portfolio/orders", payload)

async def cancel_order(self, order_id: str) -> dict[str, Any]:
    """Cancel an existing order by ID."""
    return await self._auth_delete(f"/portfolio/orders/{order_id}")

async def batch_create_orders(
    self, orders: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Place multiple orders in a single request.

    Args:
        orders: List of order specifications

    Returns:
        Batch order response
    """
    return await self._auth_post("/portfolio/orders/batched", {"orders": orders})
```

**CLI commands to add:** `kalshi portfolio order buy/sell` and `kalshi portfolio order cancel`

---

## ISSUE 3: WebSocket Not Implemented (P0 - Performance Critical)

**Spec:** `docs/_specs/SPEC-014-websocket-real-time-data.md`
**Status:** Detailed spec exists, NO CODE

**Problem:** Scanner is extremely slow (2-5 minutes) because it polls REST API repeatedly. WebSocket would make it near-instant.

**Files to create:**
```
src/kalshi_research/api/websocket/
├── __init__.py
├── client.py        # KalshiWebSocket class
├── channels.py      # Channel subscription handlers
├── messages.py      # Pydantic models for WS messages
└── reconnect.py     # Auto-reconnection logic
```

**Implementation complexity:** HIGH (~500 lines of code)

**See SPEC-014 for full implementation spec.**

---

## ISSUE 4: Rate Limit Tier Management Not Implemented (P1)

**Spec:** `docs/_specs/SPEC-015-rate-limit-tier-management.md`
**Status:** Detailed spec exists, NO CODE

**Problem:** API client uses basic tenacity retry on 429, but doesn't:
- Know user's rate tier (Basic/Advanced/Premier/Prime)
- Proactively throttle to prevent 429s
- Respect `Retry-After` header
- Use token bucket algorithm

**Files to create:**
```
src/kalshi_research/api/rate_limiter.py
```

**Implementation complexity:** MEDIUM (~200 lines)

**See SPEC-015 for full implementation spec.**

---

## ISSUE 5: Alerts Daemon Mode Not Implemented (P3)

**File:** `src/kalshi_research/cli.py` (line 1073)

**Current (broken):**
```python
if daemon:
    console.print(
        "[yellow]Warning:[/yellow] Daemon mode not yet implemented, running in foreground"
    )
```

**Fix Required:**
- Use `nohup` or `disown` to background the process
- Or use systemd/launchd service file generation
- Or use a proper process manager like supervisor

**Low priority** - foreground mode works fine for most use cases.

---

## What Actually Works (Verified)

1. **Portfolio Sync** - `kalshi portfolio sync` correctly:
   - Fetches positions from `/portfolio/positions`
   - Fetches fills from `/portfolio/fills` with pagination
   - Computes cost basis using FIFO
   - Updates mark prices from live market data
   - Stores everything in SQLite

2. **Demo Environment** - `--env demo` or `KALSHI_ENVIRONMENT=demo` switches:
   - REST base URL to `https://demo-api.kalshi.co/trade-api/v2`
   - WebSocket URL to `wss://demo-api.kalshi.co/trade-api/ws/v2`

3. **All 39 Bug Fixes** - Spot-checked key ones (BUG-027 pagination, BUG-022 truthiness) - code matches specs.

4. **ThesisBacktester class** - The logic exists in `research/backtest.py`, just not wired to CLI.

---

## Priority Order for Implementation

1. **P0: Wire Backtest CLI** - Easy fix, high value (~30 min)
2. **P1: Order Placement** - Medium complexity, enables trading (~2-4 hours)
3. **P1: Rate Limit Tiers** - Prevents API lockouts (~2-4 hours)
4. **P0: WebSocket** - Most complex but biggest performance win (~8-16 hours)
5. **P3: Daemon Mode** - Nice to have (~1 hour)

---

## Wallet/Account Setup Notes

To use authenticated features (portfolio sync, order placement when implemented):

1. Create API key at https://kalshi.com/account/api (or https://demo.kalshi.co for demo)
2. Download the private key PEM file
3. Set environment variables:
   ```bash
   export KALSHI_KEY_ID="your-key-id"
   export KALSHI_PRIVATE_KEY_PATH="./keys/kalshi_private_key.pem"
   # Or for CI: KALSHI_PRIVATE_KEY_B64="base64-encoded-pem"
   export KALSHI_ENVIRONMENT="demo"  # or "prod"
   ```
4. Run `kalshi portfolio sync` to verify connection

---

## Summary

**Previous agent was NOT reward hacking.** Most claimed fixes are real. The issues are:

1. **Backtest CLI** - Easy fix (ThesisBacktester exists, just not wired)
2. **Order placement** - Genuine missing feature (not claimed to exist)
3. **WebSocket** - Spec exists, code doesn't (Status: "Proposed")
4. **Rate limiting** - Spec exists, code doesn't (Status: "Proposed")
5. **Daemon mode** - Explicitly marked "not implemented" in code

The specs with "Proposed" status were never claimed to be implemented. The bug tracker is accurate.
