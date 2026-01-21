"""Market history command - fetch candlestick history for a market."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console, exit_kalshi_api_error, run_async


def market_history(
    ticker: Annotated[str, typer.Argument(help="Market ticker to fetch candlesticks for.")],
    series_ticker: Annotated[
        str | None,
        typer.Option(
            "--series",
            help="Optional series ticker (uses series candlesticks endpoint).",
        ),
    ] = None,
    interval: Annotated[
        str,
        typer.Option("--interval", "-i", help="Candle interval: 1m, 1h, 1d."),
    ] = "1h",
    days: Annotated[
        int,
        typer.Option("--days", help="Lookback window in days (used when --start-ts is not set)."),
    ] = 7,
    start_ts: Annotated[
        int | None,
        typer.Option("--start-ts", help="Start timestamp (Unix seconds)."),
    ] = None,
    end_ts: Annotated[
        int | None,
        typer.Option("--end-ts", help="End timestamp (Unix seconds). Defaults to now."),
    ] = None,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Fetch candlestick history for a market."""
    import json
    from datetime import UTC, datetime

    from kalshi_research.cli.client_factory import public_client

    interval_map = {"1m": 1, "1h": 60, "1d": 1440}
    if interval not in interval_map:
        allowed = ", ".join(sorted(interval_map))
        console.print(
            f"[red]Error:[/red] Invalid interval '{interval}'. Expected one of: {allowed}"
        )
        raise typer.Exit(2)

    if end_ts is None:
        end_ts = int(datetime.now(UTC).timestamp())
    if start_ts is None:
        if days <= 0:
            console.print("[red]Error:[/red] --days must be > 0 when --start-ts is not set.")
            raise typer.Exit(2)
        start_ts = end_ts - days * 24 * 60 * 60

    if start_ts >= end_ts:
        console.print("[red]Error:[/red] start-ts must be < end-ts.")
        raise typer.Exit(2)

    async def _history() -> None:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with public_client() as client:
            try:
                if series_ticker is not None:
                    candles = await client.get_series_candlesticks(
                        series_ticker=series_ticker,
                        ticker=ticker,
                        start_ts=start_ts,
                        end_ts=end_ts,
                        period_interval=interval_map[interval],
                    )
                else:
                    responses = await client.get_candlesticks(
                        market_tickers=[ticker],
                        start_ts=start_ts,
                        end_ts=end_ts,
                        period_interval=interval_map[interval],
                    )
                    candles = responses[0].candlesticks if responses else []
            except KalshiAPIError as e:
                exit_kalshi_api_error(e)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        if not candles:
            console.print("[yellow]No candlesticks returned for the given window.[/yellow]")
            return

        if output_json:
            payload = [c.model_dump(mode="json") for c in candles]
            typer.echo(json.dumps(payload, indent=2, default=str))
            return

        table = Table(title=f"Candlestick History: {ticker}")
        table.add_column("Period End (UTC)", style="cyan", no_wrap=True)
        table.add_column("Close", justify="right", style="green")
        table.add_column("Volume", justify="right", style="magenta")
        table.add_column("OI", justify="right", style="yellow")

        for candle in candles[-50:]:
            close_price = candle.price.close
            close_str = f"{close_price}¢" if close_price is not None else "N/A"
            table.add_row(
                candle.period_end.isoformat(),
                close_str,
                f"{candle.volume:,}",
                f"{candle.open_interest:,}",
            )

        console.print(table)

    run_async(_history())
