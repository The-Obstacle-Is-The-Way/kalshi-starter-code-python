"""Typer CLI commands for multivariate event (MVE) discovery."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console

app = typer.Typer(help="Multivariate event (MVE) discovery commands.")

if TYPE_CHECKING:
    from kalshi_research.api.models.event import Event
    from kalshi_research.api.models.multivariate import (
        GetMultivariateEventCollectionsResponse,
        MultivariateEventCollection,
    )


def _render_mve_events_table(events: list[Event]) -> None:
    table = Table(title="Multivariate Events (MVEs)")
    table.add_column("Event", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Series", style="magenta", no_wrap=True)
    table.add_column("Category", style="dim")

    for event in events:
        title = event.title
        table.add_row(
            event.event_ticker,
            title if len(title) <= 60 else f"{title[:57]}...",
            event.series_ticker,
            event.category or "",
        )

    console.print(table)


def _render_mve_collections_table(page: GetMultivariateEventCollectionsResponse) -> None:
    table = Table(title="MVE Collections")
    table.add_column("Collection", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Series", style="magenta", no_wrap=True)
    table.add_column("Open", style="green", no_wrap=True)
    table.add_column("Close", style="green", no_wrap=True)
    table.add_column("Size", style="yellow", no_wrap=True)
    table.add_column("#Events", justify="right", style="dim")

    for coll in page.multivariate_contracts:
        title = coll.title
        size = f"{coll.size_min}-{coll.size_max}"
        table.add_row(
            coll.collection_ticker,
            title if len(title) <= 60 else f"{title[:57]}...",
            coll.series_ticker,
            coll.open_date.isoformat(),
            coll.close_date.isoformat(),
            size,
            str(len(coll.associated_events)),
        )

    console.print(table)
    if page.cursor:
        console.print(
            "[dim]More results available (cursor present). Use the API for pagination.[/dim]"
        )


def _render_mve_collection_detail(collection: MultivariateEventCollection) -> None:
    summary = Table(title=f"MVE Collection: {collection.collection_ticker}")
    summary.add_column("Field", style="cyan")
    summary.add_column("Value", style="green")
    summary.add_row("Title", collection.title)
    summary.add_row("Series", collection.series_ticker)
    summary.add_row("Open", collection.open_date.isoformat())
    summary.add_row("Close", collection.close_date.isoformat())
    summary.add_row("Size Range", f"{collection.size_min}-{collection.size_max}")
    summary.add_row("Ordered", str(collection.is_ordered))
    summary.add_row("All YES", str(collection.is_all_yes))
    summary.add_row("Single Market/Event", str(collection.is_single_market_per_event))
    console.print(summary)

    events_table = Table(title="Associated Events")
    events_table.add_column("Event", style="cyan", no_wrap=True)
    events_table.add_column("YES Only", style="magenta")
    events_table.add_column("Size Min", justify="right", style="dim")
    events_table.add_column("Size Max", justify="right", style="dim")
    events_table.add_column("Active Quoters", justify="right", style="green")

    for event in collection.associated_events:
        events_table.add_row(
            event.ticker,
            str(event.is_yes_only),
            str(event.size_min or ""),
            str(event.size_max or ""),
            str(len(event.active_quoters)),
        )

    console.print(events_table)


@app.command("list")
def mve_list(
    limit: Annotated[int, typer.Option("--limit", help="Max number of MVEs to fetch.")] = 50,
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """List multivariate events (MVEs)."""
    from kalshi_research.api import KalshiPublicClient

    if limit <= 0:
        console.print("[red]Error:[/red] --limit must be positive.")
        raise typer.Exit(2)

    async def _fetch() -> list[Event]:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                return await client.get_multivariate_events(limit=limit)
            except KalshiAPIError as e:
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(2 if e.status_code == 404 else 1) from None
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

    events = asyncio.run(_fetch())

    if output_json:
        payload = [e.model_dump(mode="json") for e in events]
        typer.echo(json.dumps(payload, indent=2, default=str))
        return

    _render_mve_events_table(events)


@app.command("collections")
def mve_collections(
    status: Annotated[
        str | None,
        typer.Option("--status", help="Optional filter: unopened/open/closed."),
    ] = None,
    associated_event_ticker: Annotated[
        str | None,
        typer.Option("--associated-event-ticker", help="Optional associated event ticker filter."),
    ] = None,
    series: Annotated[
        str | None,
        typer.Option("--series", help="Optional series ticker filter (series_ticker)."),
    ] = None,
    limit: Annotated[
        int, typer.Option("--limit", help="Max number of collections to fetch.")
    ] = 100,
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """List multivariate event collections (single page)."""
    from kalshi_research.api import KalshiPublicClient

    if limit <= 0:
        console.print("[red]Error:[/red] --limit must be positive.")
        raise typer.Exit(2)

    async def _fetch() -> GetMultivariateEventCollectionsResponse:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                return await client.get_multivariate_event_collections(
                    status=status,
                    associated_event_ticker=associated_event_ticker,
                    series_ticker=series,
                    limit=limit,
                )
            except KalshiAPIError as e:
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(2 if e.status_code == 404 else 1) from None
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

    page = asyncio.run(_fetch())

    if output_json:
        typer.echo(json.dumps(page.model_dump(mode="json"), indent=2, default=str))
        return

    _render_mve_collections_table(page)


@app.command("collection")
def mve_collection(
    ticker: Annotated[str, typer.Argument(help="MVE collection ticker to fetch.")],
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """Get a single MVE collection by ticker."""
    from kalshi_research.api import KalshiPublicClient

    async def _fetch() -> MultivariateEventCollection:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                return await client.get_multivariate_event_collection(ticker)
            except KalshiAPIError as e:
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(2 if e.status_code == 404 else 1) from None
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

    collection = asyncio.run(_fetch())

    if output_json:
        typer.echo(json.dumps(collection.model_dump(mode="json"), indent=2, default=str))
        return

    _render_mve_collection_detail(collection)
