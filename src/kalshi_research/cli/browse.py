"""Typer CLI commands for discovery browsing (categories, series, sports)."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console, run_async

app = typer.Typer(help="Discovery browsing commands (categories, series, sports).")


@app.command("categories")
def browse_categories(
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """List series categories and their tags (browse pattern step 1)."""
    from kalshi_research.api import KalshiPublicClient

    async def _fetch() -> dict[str, list[str]]:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                return await client.get_tags_by_categories()
            except KalshiAPIError as e:
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(1) from None
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

    tags_by_category = run_async(_fetch())

    if output_json:
        typer.echo(json.dumps(tags_by_category, indent=2, default=str))
        return

    table = Table(title="Series Categories")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Tags", style="white")
    table.add_column("#", justify="right", style="dim")

    for category in sorted(tags_by_category):
        tags = tags_by_category[category]
        tags_preview = ", ".join(tags[:6])
        if len(tags) > 6:
            tags_preview += f", … (+{len(tags) - 6})"
        table.add_row(category, tags_preview, str(len(tags)))

    console.print(table)


@app.command("series")
def browse_series(
    category: Annotated[
        str | None,
        typer.Option("--category", help="Optional category filter (e.g., Politics)."),
    ] = None,
    tags: Annotated[
        str | None,
        typer.Option("--tags", help="Optional tags filter (comma-separated)."),
    ] = None,
    include_product_metadata: Annotated[
        bool,
        typer.Option(
            "--include-product-metadata",
            help="Include internal product metadata fields when available.",
        ),
    ] = False,
    include_volume: Annotated[
        bool,
        typer.Option(
            "--include-volume",
            help="Include total series volume fields (may be slow).",
        ),
    ] = False,
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """List series with optional filters (browse pattern step 2)."""
    from kalshi_research.api import KalshiPublicClient

    async def _fetch() -> list[dict[str, object]]:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                series = await client.get_series_list(
                    category=category,
                    tags=tags,
                    include_product_metadata=include_product_metadata,
                    include_volume=include_volume,
                )
            except KalshiAPIError as e:
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(1) from None
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        return [s.model_dump(mode="json") for s in series]

    series_payload = run_async(_fetch())

    if output_json:
        typer.echo(json.dumps(series_payload, indent=2, default=str))
        return

    table = Table(title="Series")
    table.add_column("Ticker", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Category", style="dim")
    table.add_column("Tags", style="magenta")
    table.add_column("Freq", style="green", no_wrap=True)
    if include_volume:
        table.add_column("Volume", justify="right", style="yellow")

    for raw in series_payload:
        ticker = str(raw.get("ticker") or "")
        title = str(raw.get("title") or "")
        category_value = str(raw.get("category") or "")
        tags_list = raw.get("tags")
        tags_display = ""
        if isinstance(tags_list, list):
            tags_display = ", ".join(str(t) for t in tags_list[:4])
            if len(tags_list) > 4:
                tags_display += f", … (+{len(tags_list) - 4})"
        frequency = str(raw.get("frequency") or "")

        row = [
            ticker,
            title if len(title) <= 60 else f"{title[:57]}...",
            category_value,
            tags_display,
            frequency,
        ]

        if include_volume:
            volume = raw.get("volume")
            row.append(f"{int(volume):,}" if isinstance(volume, int) else "N/A")

        table.add_row(*row)

    console.print(table)


@app.command("sports")
def browse_sports(
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """List sport-specific discovery filters (scopes + competitions)."""
    from kalshi_research.api import KalshiPublicClient

    async def _fetch() -> dict[str, object]:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                filters = await client.get_filters_by_sport()
            except KalshiAPIError as e:
                console.print(f"[red]API Error {e.status_code}:[/red] {e.message}")
                raise typer.Exit(1) from None
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        return filters.model_dump(mode="json")

    payload = run_async(_fetch())

    if output_json:
        typer.echo(json.dumps(payload, indent=2, default=str))
        return

    sport_order = payload.get("sport_ordering")
    filters_by_sport = payload.get("filters_by_sports")

    table = Table(title="Sports Discovery Filters")
    table.add_column("Sport", style="cyan", no_wrap=True)
    table.add_column("Scopes", style="white")
    table.add_column("Competitions", style="magenta")

    ordering: list[str]
    if isinstance(sport_order, list) and all(isinstance(s, str) for s in sport_order):
        ordering = list(sport_order)
    else:
        ordering = []

    if isinstance(filters_by_sport, dict):
        remaining = sorted(k for k in filters_by_sport if k not in ordering)
        ordering.extend(remaining)

    for sport in ordering:
        if not isinstance(filters_by_sport, dict):
            continue
        raw = filters_by_sport.get(sport)
        if not isinstance(raw, dict):
            continue

        scopes = raw.get("scopes")
        scopes_display = ", ".join(scopes[:6]) if isinstance(scopes, list) else ""
        if isinstance(scopes, list) and len(scopes) > 6:
            scopes_display += f", … (+{len(scopes) - 6})"

        competitions = raw.get("competitions")
        competition_names: list[str] = []
        if isinstance(competitions, dict):
            competition_names = sorted(str(k) for k in competitions)
        comp_display = ", ".join(competition_names[:6])
        if len(competition_names) > 6:
            comp_display += f", … (+{len(competition_names) - 6})"

        table.add_row(sport, scopes_display, comp_display)

    console.print(table)
