"""Typer CLI commands for market analysis."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from kalshi_research.cli.utils import console, run_async
from kalshi_research.paths import DEFAULT_DB_PATH

app = typer.Typer(help="Market analysis commands.")


@app.command("calibration")
def analysis_calibration(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    days: Annotated[int, typer.Option("--days", help="Number of days to analyze")] = 30,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output JSON file"),
    ] = None,
) -> None:
    """Analyze market calibration and Brier scores."""
    from kalshi_research.analysis import CalibrationAnalyzer
    from kalshi_research.cli.db import open_db_session

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    async def _analyze() -> None:
        from kalshi_research.data.repositories import PriceRepository

        async with open_db_session(db_path) as session:
            price_repo = PriceRepository(session)
            from kalshi_research.data.repositories import SettlementRepository

            settlement_repo = SettlementRepository(session)
            cutoff = datetime.now(UTC) - timedelta(days=days)
            settlements = await settlement_repo.get_settled_after(cutoff)

            forecasts: list[float] = []
            outcomes: list[int] = []
            for settlement in settlements:
                if settlement.result not in {"yes", "no"}:
                    continue

                snaps = await price_repo.get_for_market(
                    settlement.ticker,
                    end_time=settlement.settled_at,
                    limit=1,
                )
                if not snaps:
                    continue

                snapshot = snaps[0]
                forecasts.append(snapshot.midpoint / 100.0)
                outcomes.append(1 if settlement.result == "yes" else 0)

        if not forecasts:
            console.print("[yellow]No settled markets with price history found[/yellow]")
            return

        analyzer = CalibrationAnalyzer()
        result = analyzer.compute_calibration(forecasts, outcomes)

        # Display results
        table = Table(title="Calibration Analysis")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Brier Score", f"{result.brier_score:.4f}")
        table.add_row("Samples", str(result.n_samples))
        table.add_row("Skill Score", f"{result.brier_skill_score:.4f}")
        table.add_row("Resolution", f"{result.resolution:.4f}")
        table.add_row("Reliability", f"{result.reliability:.4f}")
        table.add_row("Uncertainty", f"{result.uncertainty:.4f}")

        console.print(table)

        # Save to file if requested
        if output:
            output_data = {
                "brier_score": result.brier_score,
                "brier_skill_score": result.brier_skill_score,
                "n_samples": result.n_samples,
                "resolution": result.resolution,
                "reliability": result.reliability,
                "uncertainty": result.uncertainty,
                "bins": result.bins.tolist(),
                "predicted_probs": result.predicted_probs.tolist(),
                "actual_freqs": result.actual_freqs.tolist(),
                "bin_counts": result.bin_counts.tolist(),
            }
            with output.open("w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2)
            console.print(f"\n[dim]Saved to {output}[/dim]")

    run_async(_analyze())


@app.command("metrics")
def analysis_metrics(
    ticker: Annotated[str, typer.Argument(help="Market ticker to analyze")],
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Calculate market metrics for a ticker."""
    from kalshi_research.cli.db import open_db_session

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    async def _metrics() -> None:
        from kalshi_research.data.repositories import PriceRepository

        price = None
        async with open_db_session(db_path) as session:
            price_repo = PriceRepository(session)
            # Get latest price
            price = await price_repo.get_latest(ticker)

            if not price:
                console.print(f"[yellow]No data found for {ticker}[/yellow]")
                return

        # Display metrics
        table = Table(title=f"Metrics: {ticker}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Yes Bid/Ask", f"{price.yes_bid}¢ / {price.yes_ask}¢")
        table.add_row("No Bid/Ask", f"{price.no_bid}¢ / {price.no_ask}¢")
        spread = price.yes_ask - price.yes_bid
        table.add_row("Spread", f"{spread}¢")
        table.add_row("Volume (24h)", f"{price.volume_24h:,}")
        table.add_row("Open Interest", f"{price.open_interest:,}")

        console.print(table)

    run_async(_metrics())


@app.command("correlation")
def analysis_correlation(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    event: Annotated[
        str | None,
        typer.Option("--event", "-e", help="Filter by event ticker"),
    ] = None,
    tickers: Annotated[
        str | None,
        typer.Option("--tickers", "-t", help="Comma-separated list of tickers to analyze"),
    ] = None,
    min_correlation: Annotated[
        float, typer.Option("--min", help="Minimum correlation threshold")
    ] = 0.5,
    top_n: Annotated[int, typer.Option("--top", "-n", help="Number of results")] = 10,
) -> None:
    """Analyze correlations between markets."""
    from kalshi_research.analysis.correlation import CorrelationAnalyzer
    from kalshi_research.cli.db import open_db_session

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    async def _analyze() -> None:
        from kalshi_research.data.repositories import PriceRepository

        async with open_db_session(db_path) as session:
            price_repo = PriceRepository(session)

            # Fetch price snapshots
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Fetching price snapshots...", total=None)

                # Get tickers to analyze
                if tickers:
                    ticker_list = [t.strip() for t in tickers.split(",")]
                elif event:
                    # Get all markets for this event
                    from kalshi_research.data.repositories import MarketRepository

                    market_repo = MarketRepository(session)
                    event_markets = await market_repo.get_by_event(event)
                    ticker_list = [m.ticker for m in event_markets]
                else:
                    console.print("[yellow]Error:[/yellow] Must specify --event or --tickers")
                    raise typer.Exit(1)

                if len(ticker_list) < 2:
                    console.print(
                        "[yellow]Need at least 2 tickers to analyze correlations[/yellow]"
                    )
                    return

                # Fetch snapshots for each ticker
                snapshots = {}
                for ticker in ticker_list:
                    snaps = await price_repo.get_for_market(ticker, limit=1000)
                    if snaps:
                        snapshots[ticker] = list(snaps)

            if len(snapshots) < 2:
                console.print("[yellow]Not enough data to analyze correlations[/yellow]")
                return

            # Analyze correlations
            analyzer = CorrelationAnalyzer(min_correlation=min_correlation)
            results = await analyzer.find_correlated_markets(snapshots, top_n=top_n)

            if not results:
                console.print("[yellow]No significant correlations found[/yellow]")
                return

            # Display results
            table = Table(title="Market Correlations")
            table.add_column("Ticker A", style="cyan")
            table.add_column("Ticker B", style="cyan")
            table.add_column("Correlation", style="green")
            table.add_column("Type", style="yellow")
            table.add_column("Strength", style="magenta")
            table.add_column("Samples", style="dim")

            for result in results:
                table.add_row(
                    result.ticker_a,
                    result.ticker_b,
                    f"{result.pearson:.3f}",
                    result.correlation_type.value,
                    result.strength,
                    str(result.n_samples),
                )

            console.print(table)
            console.print(f"\n[dim]Found {len(results)} correlated pairs[/dim]")

    run_async(_analyze())
