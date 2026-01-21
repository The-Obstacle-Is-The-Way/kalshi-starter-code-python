"""Market liquidity command - analyze market liquidity using orderbook depth."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console, exit_kalshi_api_error, run_async


def market_liquidity(
    ticker: Annotated[str, typer.Argument(help="Market ticker to analyze.")],
    depth: Annotated[
        int,
        typer.Option("--depth", "-d", help="Orderbook depth levels to fetch for analysis."),
    ] = 25,
    max_slippage_cents: Annotated[
        int,
        typer.Option("--max-slippage-cents", help="Max slippage (cents) for 'safe size'."),
    ] = 3,
) -> None:
    """Analyze market liquidity using orderbook depth and slippage estimates."""
    from kalshi_research.cli.client_factory import public_client

    async def _liquidity() -> None:
        from kalshi_research.analysis.liquidity import (
            estimate_slippage,
            liquidity_score,
            max_safe_order_size,
            suggest_execution_timing,
        )
        from kalshi_research.api.exceptions import KalshiAPIError

        async with public_client() as client:
            try:
                market = await client.get_market(ticker)
                orderbook = await client.get_orderbook(ticker, depth=depth)
            except KalshiAPIError as e:
                exit_kalshi_api_error(e)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        analysis = liquidity_score(market, orderbook)
        safe_yes = max_safe_order_size(orderbook, "yes", max_slippage_cents=max_slippage_cents)
        safe_no = max_safe_order_size(orderbook, "no", max_slippage_cents=max_slippage_cents)
        timing = suggest_execution_timing()

        summary = Table(title=f"Liquidity Analysis: {ticker}")
        summary.add_column("Metric", style="cyan")
        summary.add_column("Value", style="green")

        spread = orderbook.spread
        summary.add_row("Score", f"{analysis.score}/100 ({analysis.grade.value.upper()})")
        summary.add_row("Spread", f"{spread}¢" if spread is not None else "N/A")
        summary.add_row(
            "Depth (±10c)",
            f"{analysis.depth.total_contracts:,} contracts "
            f"(YES {analysis.depth.yes_side_depth:,} / NO {analysis.depth.no_side_depth:,})",
        )
        summary.add_row("Imbalance", f"{analysis.depth.imbalance_ratio:+.1%}")
        summary.add_row("Volume (24h)", f"{market.volume_24h:,}")
        summary.add_row("Open Interest", f"{market.open_interest:,}")
        summary.add_row(
            f"Max Safe Size (≤{max_slippage_cents}c)",
            f"Buy YES: {safe_yes:,} | Buy NO: {safe_no:,}",
        )

        console.print(summary)

        slippage_table = Table(title="Order Size Analysis (Buy YES)")
        slippage_table.add_column("Qty", justify="right", style="cyan")
        slippage_table.add_column("Slippage", style="yellow")
        slippage_table.add_column("Avg Fill", style="green")
        slippage_table.add_column("Fillable", justify="right", style="magenta")
        slippage_table.add_column("Levels", justify="right", style="dim")

        for qty in [10, 50, 100, 250, 500]:
            slip = estimate_slippage(orderbook, "yes", "buy", qty)
            fillable = (
                f"{slip.fillable_quantity:,}"
                if slip.remaining_unfilled == 0
                else f"{slip.fillable_quantity:,} (rem {slip.remaining_unfilled:,})"
            )
            avg_fill = f"{slip.avg_fill_price:.1f}¢" if slip.fillable_quantity > 0 else "N/A"
            slippage_table.add_row(
                f"{qty:,}",
                f"{slip.slippage_cents:.1f}¢ ({slip.slippage_pct:.1f}%)",
                avg_fill,
                fillable,
                f"{slip.levels_crossed}",
            )

        console.print(slippage_table)

        optimal = (
            f"{timing.optimal_hours_utc[0]}:00-{timing.optimal_hours_utc[-1]}:00 UTC"
            if timing.optimal_hours_utc
            else "N/A"
        )
        avoid = (
            f"{timing.avoid_hours_utc[0]}:00-{timing.avoid_hours_utc[-1]}:00 UTC"
            if timing.avoid_hours_utc
            else "N/A"
        )
        console.print(
            "\nExecution Timing:",
            f"[green]optimal[/green] {optimal}, [yellow]avoid[/yellow] {avoid}",
        )

        if analysis.warnings:
            console.print("\n[yellow]Warnings:[/yellow]")
            for w in analysis.warnings:
                console.print(f"- {w}")

    run_async(_liquidity())
