"""News monitoring and sentiment analysis CLI commands."""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.table import Table

from kalshi_research.cli.utils import console
from kalshi_research.exa.policy import ExaMode
from kalshi_research.paths import DEFAULT_DB_PATH

app = typer.Typer(help="News monitoring and sentiment analysis.")

if TYPE_CHECKING:
    from kalshi_research.api.models.event import Event as KalshiEvent
    from kalshi_research.api.models.market import Market as KalshiMarket
    from kalshi_research.data import DatabaseManager


def _maybe_print_budget_exhausted(obj: object) -> None:
    from kalshi_research.exa.policy import ExaBudget

    if getattr(obj, "budget_exhausted", False) is not True:
        return

    budget = getattr(obj, "budget", None)
    if not isinstance(budget, ExaBudget):
        return

    console.print(
        f"[yellow]Budget exhausted[/yellow] "
        f"(${budget.spent_usd:.4f} / ${budget.limit_usd:.2f}); "
        "results may be partial."
    )


def _default_search_queries(title: str) -> list[str]:
    cleaned = title.replace("?", "").strip()
    return [cleaned, f"{cleaned} news"]


def _parse_search_queries(queries: str | None, *, title: str) -> list[str]:
    """Parse a comma-separated `--queries` override or fall back to title defaults."""
    if queries:
        return [q.strip() for q in queries.split(",") if q.strip()]
    return _default_search_queries(title)


async def _fetch_tracking_targets(
    ticker: str,
    *,
    event: bool,
) -> tuple["KalshiEvent", "KalshiMarket | None", str]:
    """Resolve a market or event ticker into the corresponding API objects.

    Args:
        ticker: Market ticker (default) or event ticker (when `event=True`).
        event: Treat `ticker` as an event ticker when true.

    Returns:
        Tuple of (`event_obj`, `market_obj`, `title`) where `market_obj` is `None` when tracking
        an event directly.

    Raises:
        ValueError: If the ticker cannot be resolved via the Kalshi public API.
    """
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.api.exceptions import KalshiAPIError

    async with KalshiPublicClient() as kalshi:
        try:
            if event:
                event_obj = await kalshi.get_event(ticker)
                return event_obj, None, event_obj.title

            market_obj = await kalshi.get_market(ticker)
            event_obj = await kalshi.get_event(market_obj.event_ticker)
            return event_obj, market_obj, market_obj.title
        except KalshiAPIError as exc:
            raise ValueError("Ticker not found") from exc


async def _upsert_event_and_market(
    *,
    db: "DatabaseManager",
    event_obj: "KalshiEvent",
    market_obj: "KalshiMarket | None",
) -> None:
    from kalshi_research.data.models import Event as EventRow
    from kalshi_research.data.models import Market as MarketRow

    async with db.session_factory() as session, session.begin():
        await session.merge(
            EventRow(
                ticker=event_obj.event_ticker,
                series_ticker=event_obj.series_ticker,
                title=event_obj.title,
                status=None,
                category=event_obj.category,
                mutually_exclusive=event_obj.mutually_exclusive,
            )
        )
        if market_obj is not None:
            await session.merge(
                MarketRow(
                    ticker=market_obj.ticker,
                    event_ticker=market_obj.event_ticker,
                    series_ticker=market_obj.series_ticker,
                    title=market_obj.title,
                    subtitle=market_obj.subtitle,
                    status=market_obj.status.value,
                    result=market_obj.result,
                    open_time=market_obj.open_time,
                    close_time=market_obj.close_time,
                    expiration_time=market_obj.expiration_time,
                    category=None,
                    subcategory=None,
                )
            )


async def _news_track_async(
    *,
    ticker: str,
    event: bool,
    queries: str | None,
    db_path: Path,
) -> tuple[str, str, list[str]]:
    from kalshi_research.cli.db import open_db
    from kalshi_research.news import NewsTracker

    event_obj, market_obj, title = await _fetch_tracking_targets(ticker, event=event)
    search_queries = _parse_search_queries(queries, title=title)

    async with open_db(db_path) as db:
        await _upsert_event_and_market(db=db, event_obj=event_obj, market_obj=market_obj)
        tracked = await NewsTracker(db).track(
            ticker=ticker,
            item_type="event" if event else "market",
            search_queries=search_queries,
        )

    return tracked.ticker, tracked.item_type, search_queries


@app.command("track")
def news_track(
    ticker: Annotated[str, typer.Argument(help="Market or event ticker to track")],
    event: Annotated[
        bool,
        typer.Option("--event", "-e", help="Treat ticker as an event ticker"),
    ] = False,
    queries: Annotated[
        str | None,
        typer.Option("--queries", "-q", help="Comma-separated custom search queries"),
    ] = None,
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to database"),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Start tracking news for a market or event."""
    try:
        tracked_ticker, item_type, search_queries = asyncio.run(
            _news_track_async(
                ticker=ticker,
                event=event,
                queries=queries,
                db_path=db_path,
            )
        )
    except ValueError:
        console.print(f"[red]Error:[/red] Ticker not found: {ticker}")
        raise typer.Exit(2) from None

    console.print(f"[green]✓[/green] Now tracking: {tracked_ticker} ({item_type})")
    console.print(f"[dim]Queries: {search_queries}[/dim]")


@app.command("untrack")
def news_untrack(
    ticker: Annotated[str, typer.Argument(help="Market or event ticker to untrack")],
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to database"),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Stop tracking a market/event."""
    from kalshi_research.cli.db import open_db
    from kalshi_research.news import NewsTracker

    async def _untrack() -> None:
        async with open_db(db_path) as db:
            tracker = NewsTracker(db)
            removed = await tracker.untrack(ticker)
        if not removed:
            console.print(f"[yellow]Not tracked:[/yellow] {ticker}")
            raise typer.Exit(2)
        console.print(f"[green]✓[/green] Untracked: {ticker}")

    asyncio.run(_untrack())


@app.command("list-tracked")
def news_list_tracked(
    include_all: Annotated[
        bool,
        typer.Option("--all", help="Include inactive tracked items"),
    ] = False,
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to database"),
    ] = DEFAULT_DB_PATH,
) -> None:
    """List tracked markets/events."""
    from kalshi_research.cli.db import open_db
    from kalshi_research.news import NewsTracker

    async def _list() -> None:
        async with open_db(db_path) as db:
            tracker = NewsTracker(db)
            items = await tracker.list_tracked(active_only=not include_all)

        if not items:
            console.print("[yellow]No tracked items.[/yellow]")
            return

        table = Table(title="Tracked Items")
        table.add_column("Ticker", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Active", style="yellow")

        for item in items:
            table.add_row(item.ticker, item.item_type, "yes" if item.is_active else "no")

        console.print(table)

    asyncio.run(_list())


@app.command("collect")
def news_collect(
    ticker: Annotated[
        str | None,
        typer.Option("--ticker", help="Collect only for this tracked ticker"),
    ] = None,
    mode: Annotated[
        ExaMode,
        typer.Option("--mode", help="Exa policy mode: fast (cheap), standard, deep (expensive)."),
    ] = ExaMode.STANDARD,
    budget_usd: Annotated[
        float | None,
        typer.Option(
            "--budget-usd",
            help="Max Exa spend (USD) for this command. Default depends on mode.",
        ),
    ] = None,
    lookback_days: Annotated[int, typer.Option("--lookback-days", help="Days to look back")] = 7,
    max_per_query: Annotated[
        int,
        typer.Option("--max-per-query", help="Max articles per query"),
    ] = 25,
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to database"),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Collect news for tracked items."""
    from sqlalchemy import select

    from kalshi_research.cli.db import open_db
    from kalshi_research.data.models import TrackedItem
    from kalshi_research.exa import ExaClient, ExaConfig
    from kalshi_research.exa.policy import ExaPolicy
    from kalshi_research.news import NewsCollector, SentimentAnalyzer

    async def _collect() -> None:
        try:
            config = ExaConfig.from_env()
        except ValueError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from None

        async with open_db(db_path) as db, ExaClient(config) as exa:
            try:
                policy = ExaPolicy.from_mode(mode=mode, budget_usd=budget_usd)
            except ValueError as exc:
                console.print(f"[red]Error:[/red] {exc}")
                console.print("[dim]Check EXA_API_KEY and --budget-usd (must be > 0).[/dim]")
                raise typer.Exit(1) from None

            collector = NewsCollector(
                exa=exa,
                db=db,
                sentiment_analyzer=SentimentAnalyzer(),
                lookback_days=lookback_days,
                max_articles_per_query=max_per_query,
                policy=policy,
            )

            if ticker:
                async with db.session_factory() as session:
                    tracked = (
                        await session.execute(
                            select(TrackedItem).where(TrackedItem.ticker == ticker)
                        )
                    ).scalar_one_or_none()
                if tracked is None or not tracked.is_active:
                    console.print(f"[yellow]Not tracked:[/yellow] {ticker}")
                    raise typer.Exit(1)

                count = await collector.collect_for_tracked_item(tracked)
                console.print(f"[green]✓[/green] {ticker}: {count} new article(s)")
                _maybe_print_budget_exhausted(collector)
                return

            results = await collector.collect_all()
            if not results:
                console.print("[yellow]No tracked items.[/yellow]")
                return
            for key, count in results.items():
                console.print(f"[green]✓[/green] {key}: {count} new article(s)")
            _maybe_print_budget_exhausted(collector)

    asyncio.run(_collect())


@app.command("sentiment")
def news_sentiment(
    ticker: Annotated[str, typer.Argument(help="Market (or event) ticker")],
    event: Annotated[bool, typer.Option("--event", "-e", help="Treat as event ticker")] = False,
    days: Annotated[int, typer.Option("--days", help="Days to analyze")] = 7,
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to database"),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Show a sentiment summary for a market/event."""
    from kalshi_research.cli.db import open_db
    from kalshi_research.news import SentimentAggregator

    async def _report() -> None:
        async with open_db(db_path) as db:
            aggregator = SentimentAggregator(db)
            summary = (
                await aggregator.get_event_summary(ticker, days=days)
                if event
                else await aggregator.get_market_summary(ticker, days=days)
            )

        if summary is None:
            console.print("[yellow]No sentiment data found.[/yellow]")
            raise typer.Exit(1)

        console.print(f"[bold]Ticker:[/bold] {ticker}")
        console.print(f"[bold]Period:[/bold] Last {days} days\n")
        console.print(
            f"[bold]Sentiment:[/bold] {summary.avg_score:+.2f} ({summary.sentiment_label}) "
            f"{summary.trend_indicator} "
            + (f"{summary.score_change:+.2f}" if summary.score_change is not None else "—")
        )
        console.print("─" * 40)
        console.print(f"Articles analyzed: {summary.total_articles}")
        console.print(
            f"Positive: {summary.positive_count} | Neutral: {summary.neutral_count} | "
            f"Negative: {summary.negative_count}"
        )
        if summary.top_keywords:
            console.print("\n[bold]Top keywords:[/bold]")
            for kw, count in summary.top_keywords[:8]:
                console.print(f"• {kw} ({count})")

    asyncio.run(_report())
