"""Portfolio sync command - syncs positions, trades, and settlements from Kalshi API."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - Required at runtime for Typer introspection
from typing import Annotated

import typer

from kalshi_research.cli.portfolio._helpers import (
    require_auth_env,
    resolve_rate_tier_override,
    validate_environment_override,
)
from kalshi_research.cli.utils import console, exit_kalshi_api_error, run_async
from kalshi_research.paths import DEFAULT_DB_PATH


def portfolio_sync(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    environment: Annotated[
        str | None,
        typer.Option("--env", help="Override global environment (demo or prod)."),
    ] = None,
    rate_tier: Annotated[
        str | None,
        typer.Option(
            "--rate-tier",
            help=(
                "API rate limit tier (basic/advanced/premier/prime). "
                "Defaults to KALSHI_RATE_TIER or basic."
            ),
            show_default=False,
        ),
    ] = None,
    skip_mark_prices: Annotated[
        bool,
        typer.Option(
            "--skip-mark-prices",
            help="Skip fetching current market prices (faster sync).",
        ),
    ] = False,
) -> None:
    """Sync positions and trades from Kalshi API.

    Syncs positions, fills, settlements, cost basis (FIFO), mark prices, and unrealized P&L.
    """
    from kalshi_research.api.exceptions import KalshiAPIError
    from kalshi_research.cli.client_factory import authed_client, public_client
    from kalshi_research.cli.db import open_db
    from kalshi_research.portfolio.syncer import PortfolioSyncer

    environment_override = validate_environment_override(environment)
    key_id, private_key_path, private_key_b64 = require_auth_env(
        purpose="Portfolio sync", environment=environment_override
    )
    rate_tier_override = resolve_rate_tier_override(rate_tier)

    async def _sync() -> None:
        try:
            async with (
                authed_client(
                    key_id=key_id,
                    private_key_path=private_key_path,
                    private_key_b64=private_key_b64,
                    environment=environment_override,
                    rate_tier=rate_tier_override,
                ) as client,
                open_db(db_path) as db,
            ):
                syncer = PortfolioSyncer(client=client, db=db)

                # Sync trades first (needed for cost basis calculation)
                console.print("[dim]Syncing trades...[/dim]")
                trades_count = await syncer.sync_trades()
                console.print(f"[green]✓[/green] Synced {trades_count} trades")

                # Sync settlements (needed for complete history and backtesting)
                console.print("[dim]Syncing settlements...[/dim]")
                settlements_count = await syncer.sync_settlements()
                console.print(f"[green]✓[/green] Synced {settlements_count} settlements")

                # Sync positions (computes cost basis from trades via FIFO)
                console.print("[dim]Syncing positions + cost basis (FIFO)...[/dim]")
                positions_count = await syncer.sync_positions()
                console.print(f"[green]✓[/green] Synced {positions_count} positions")

                # Update mark prices + unrealized P&L (requires public API)
                if not skip_mark_prices and positions_count > 0:
                    console.print("[dim]Fetching mark prices...[/dim]")
                    # Use same environment override for public client
                    async with public_client(environment=environment_override) as pub_client:
                        updated = await syncer.update_mark_prices(pub_client)
                        console.print(
                            f"[green]✓[/green] Updated mark prices for {updated} positions"
                        )

                console.print(
                    f"\n[green]✓[/green] Portfolio sync complete: "
                    f"{positions_count} positions, {trades_count} trades, "
                    f"{settlements_count} settlements"
                )

        except KalshiAPIError as e:
            exit_kalshi_api_error(e)
        except (OSError, ValueError) as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

    run_async(_sync())
