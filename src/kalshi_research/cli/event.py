"""Typer CLI commands for event discovery and analysis."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console, exit_kalshi_api_error, run_async

app = typer.Typer(help="Event discovery and analysis commands.")


if TYPE_CHECKING:
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.api.models.candlestick import EventCandlesticksResponse
    from kalshi_research.api.models.event import Event, EventMetadataResponse, MarketMetadata


def _normalize_event_status(status: str | None) -> str | None:
    if status is None:
        return None

    from kalshi_research.api.models.market import MarketFilterStatus

    raw = status
    normalized = raw.strip().lower()

    # Common footgun: response status values differ from filter values.
    if normalized == "active":
        console.print(
            "[yellow]Warning:[/yellow] 'active' is a response status, not a valid filter. "
            "Using '--status open'."
        )
        return MarketFilterStatus.OPEN.value

    allowed = {s.value for s in MarketFilterStatus}
    if normalized not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        console.print(f"[red]Error:[/red] Invalid status filter '{raw}'.")
        console.print(f"[dim]Expected one of: {allowed_str}[/dim]")
        raise typer.Exit(2)

    return normalized


def _interval_minutes(interval: str) -> int:
    interval_map = {"1m": 1, "1h": 60, "1d": 1440}
    if interval not in interval_map:
        allowed = ", ".join(sorted(interval_map))
        console.print(
            f"[red]Error:[/red] Invalid interval '{interval}'. Expected one of: {allowed}"
        )
        raise typer.Exit(2)
    return interval_map[interval]


def _resolve_time_window(
    *,
    days: int,
    start_ts: int | None,
    end_ts: int | None,
) -> tuple[int, int]:
    from datetime import UTC, datetime

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

    return start_ts, end_ts


async def _fetch_event_with_metadata(
    client: KalshiPublicClient,
    *,
    ticker: str,
    warn: bool = True,
) -> tuple[Event, EventMetadataResponse | None]:
    from kalshi_research.api.exceptions import KalshiAPIError

    event = await client.get_event(ticker)

    try:
        metadata = await client.get_event_metadata(ticker)
    except KalshiAPIError as e:
        if warn:
            console.print(
                f"[yellow]Warning:[/yellow] Event metadata unavailable "
                f"(API Error {e.status_code}): {e.message}"
            )
        return event, None
    except Exception as e:
        if warn:
            console.print(f"[yellow]Warning:[/yellow] Event metadata unavailable: {e}")
        return event, None

    return event, metadata


def _render_market_metadata_table(market_details: list[MarketMetadata] | None) -> None:
    if not market_details:
        return

    details_table = Table(title="Market Metadata")
    details_table.add_column("Market", style="cyan", no_wrap=True)
    details_table.add_column("Color", style="magenta")
    details_table.add_column("Image", style="green")

    for item in market_details[:50]:
        details_table.add_row(item.market_ticker, item.color_code, item.image_url)

    console.print(details_table)


def _render_event_tables(
    *,
    ticker: str,
    event: Event,
    metadata: EventMetadataResponse | None,
) -> None:
    table = Table(title=f"Event: {ticker}")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Title", event.title)
    if event.sub_title:
        table.add_row("Sub-title", event.sub_title)
    table.add_row("Series", event.series_ticker)
    table.add_row("Category", event.category or "")
    table.add_row("Mutually Exclusive", str(event.mutually_exclusive))
    console.print(table)

    if metadata is None:
        return

    meta_table = Table(title="Event Metadata")
    meta_table.add_column("Field", style="cyan")
    meta_table.add_column("Value", style="green")
    meta_table.add_row("Image", metadata.image_url)
    if metadata.featured_image_url:
        meta_table.add_row("Featured Image", metadata.featured_image_url)

    settlement_sources = metadata.settlement_sources or []
    if settlement_sources:
        sources_preview = ", ".join((s.url or s.name or "") for s in settlement_sources[:3])
        if len(settlement_sources) > 3:
            sources_preview += f", … (+{len(settlement_sources) - 3})"
        meta_table.add_row("Settlement Sources", sources_preview)

    console.print(meta_table)
    _render_market_metadata_table(metadata.market_details)


async def _fetch_event_candlesticks(
    client: KalshiPublicClient,
    *,
    ticker: str,
    series: str | None,
    start_ts: int,
    end_ts: int,
    period_interval: int,
) -> tuple[str, EventCandlesticksResponse]:
    if series is None:
        event = await client.get_event(ticker)
        series = event.series_ticker

    response = await client.get_event_candlesticks(
        series_ticker=series,
        event_ticker=ticker,
        start_ts=start_ts,
        end_ts=end_ts,
        period_interval=period_interval,
    )
    return series, response


def _render_event_candlesticks_table(
    *,
    ticker: str,
    series_ticker: str,
    interval: str,
    response: EventCandlesticksResponse,
) -> None:
    title = f"Event Candlesticks: {ticker} ({interval}) | series={series_ticker}"
    table = Table(title=title)
    table.add_column("Market", style="cyan", no_wrap=True)
    table.add_column("Candles", justify="right", style="dim")
    table.add_column("Last Period End (UTC)", style="white", no_wrap=True)
    table.add_column("Last Close", justify="right", style="green")
    table.add_column("Last Volume", justify="right", style="magenta")

    for market, candles in zip(response.market_tickers, response.market_candlesticks, strict=False):
        last = candles[-1] if candles else None
        volume_str = f"{(last.volume or 0):,}" if last else "0"
        table.add_row(
            market,
            str(len(candles)),
            last.period_end.isoformat() if last else "",
            f"{last.price.close}¢" if last and last.price.close is not None else "N/A",
            volume_str,
        )

    console.print(table)


@app.command("list")
def event_list(
    status: Annotated[
        str | None,
        typer.Option("--status", help="Optional event status filter (open/closed/settled/...)."),
    ] = None,
    series: Annotated[
        str | None,
        typer.Option("--series", help="Optional series ticker filter (series_ticker)."),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="Max number of events to fetch.")] = 50,
    with_markets: Annotated[
        bool,
        typer.Option("--with-markets", help="Include nested markets in the response."),
    ] = False,
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """List events (single page) with optional filters."""
    from kalshi_research.api import KalshiPublicClient

    status_filter = _normalize_event_status(status)

    if limit <= 0:
        console.print("[red]Error:[/red] --limit must be positive.")
        raise typer.Exit(2)

    async def _fetch() -> list[dict[str, object]]:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                events = await client.get_events(
                    status=status_filter,
                    series_ticker=series,
                    limit=limit,
                    with_nested_markets=with_markets,
                )
            except KalshiAPIError as e:
                exit_kalshi_api_error(e)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        return [e.model_dump(mode="json") for e in events]

    events_payload = run_async(_fetch())

    if output_json:
        typer.echo(json.dumps(events_payload, indent=2, default=str))
        return

    table = Table(title="Events")
    table.add_column("Event", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Series", style="magenta", no_wrap=True)
    table.add_column("Category", style="dim")
    if with_markets:
        table.add_column("#Markets", justify="right", style="green")

    for raw in events_payload:
        ticker_value = str(raw.get("event_ticker") or "")
        title = str(raw.get("title") or "")
        series_ticker = str(raw.get("series_ticker") or "")
        category_value = raw.get("category")
        category_display = str(category_value) if isinstance(category_value, str) else ""

        row = [
            ticker_value,
            title if len(title) <= 60 else f"{title[:57]}...",
            series_ticker,
            category_display,
        ]

        if with_markets:
            markets = raw.get("markets")
            market_count = len(markets) if isinstance(markets, list) else 0
            row.append(str(market_count))

        table.add_row(*row)

    console.print(table)


@app.command("get")
def event_get(
    ticker: Annotated[str, typer.Argument(help="Event ticker to fetch.")],
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """Get event fundamentals plus best-effort metadata enrichment."""
    from kalshi_research.api import KalshiPublicClient

    async def _fetch() -> tuple[Event, EventMetadataResponse | None]:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                return await _fetch_event_with_metadata(client, ticker=ticker, warn=not output_json)
            except KalshiAPIError as e:
                exit_kalshi_api_error(e)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

    event, metadata = run_async(_fetch())

    if output_json:
        payload: dict[str, object] = {"event": event.model_dump(mode="json")}
        payload["metadata"] = metadata.model_dump(mode="json") if metadata else None
        typer.echo(json.dumps(payload, indent=2, default=str))
        return

    _render_event_tables(ticker=ticker, event=event, metadata=metadata)


@app.command("candlesticks")
def event_candlesticks(
    ticker: Annotated[str, typer.Argument(help="Event ticker to fetch candlesticks for.")],
    series: Annotated[
        str | None,
        typer.Option("--series", help="Optional series ticker (derived when omitted)."),
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
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """Fetch event-level candlesticks (OHLC aligned across markets)."""
    from kalshi_research.api import KalshiPublicClient

    period_interval = _interval_minutes(interval)
    resolved_start_ts, resolved_end_ts = _resolve_time_window(
        days=days, start_ts=start_ts, end_ts=end_ts
    )

    async def _fetch() -> tuple[str, EventCandlesticksResponse]:
        from kalshi_research.api.exceptions import KalshiAPIError

        async with KalshiPublicClient() as client:
            try:
                return await _fetch_event_candlesticks(
                    client,
                    ticker=ticker,
                    series=series,
                    start_ts=resolved_start_ts,
                    end_ts=resolved_end_ts,
                    period_interval=period_interval,
                )
            except KalshiAPIError as e:
                exit_kalshi_api_error(e)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

    resolved_series, response = run_async(_fetch())

    if output_json:
        payload = response.model_dump(mode="json")
        payload["series_ticker"] = resolved_series
        typer.echo(json.dumps(payload, indent=2, default=str))
        return

    _render_event_candlesticks_table(
        ticker=ticker,
        series_ticker=resolved_series,
        interval=interval,
        response=response,
    )
