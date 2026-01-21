"""Typer CLI commands for database setup and data synchronization."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from kalshi_research.cli.utils import console, exit_kalshi_api_error, run_async
from kalshi_research.paths import DEFAULT_DB_PATH, DEFAULT_EXPORTS_DIR

app = typer.Typer(help="Data management commands.")


def _find_alembic_ini() -> Path:
    alembic_ini = Path("alembic.ini")
    if alembic_ini.exists():
        return alembic_ini

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "alembic.ini"
        if candidate.exists():
            return candidate

    raise FileNotFoundError("alembic.ini not found")


def _validate_migrations_on_temp_db(*, alembic_ini: Path, db_path: Path) -> None:
    """Validate Alembic migrations by running them against a temporary DB copy.

    Args:
        alembic_ini: Path to the alembic.ini configuration file.
        db_path: Path to the local SQLite database file.
    """
    import shutil
    import tempfile

    from alembic import command
    from alembic.config import Config

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        suffix=".db",
        prefix="kalshi-migrate-",
        dir=str(db_path.parent),
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)

    try:
        if db_path.exists():
            shutil.copy2(db_path, tmp_path)
        else:
            tmp_path.touch()

        tmp_cfg = Config(str(alembic_ini))
        # Alembic is invoked synchronously, but our alembic `env.py` runs migrations via
        # `async_engine_from_config`, so the async driver URL is required here.
        tmp_cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{tmp_path}")
        command.upgrade(tmp_cfg, "head")
    finally:
        tmp_path.unlink(missing_ok=True)


@app.command("init")
def data_init(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Initialize the database with required tables."""
    from kalshi_research.cli.db import open_db

    async def _init() -> None:
        async with open_db(db_path):
            console.print(f"[green]✓[/green] Database initialized at {db_path}")

    run_async(_init())


@app.command("migrate")
def data_migrate(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--apply",
            help="Validate migrations on a temporary DB copy (default: dry-run).",
        ),
    ] = True,
) -> None:
    """Run Alembic schema migrations (upgrade to head)."""
    from alembic import command
    from alembic.config import Config
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine

    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        alembic_ini = _find_alembic_ini()
    except FileNotFoundError:
        console.print("[red]Error:[/red] Could not find alembic.ini")
        console.print(
            "[dim]Run from the repository root, or ensure alembic.ini is available.[/dim]"
        )
        raise typer.Exit(1) from None

    alembic_cfg = Config(str(alembic_ini))
    # Keep the async driver URL: our alembic `env.py` runs migrations via
    # `async_engine_from_config`.
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path}")

    script = ScriptDirectory.from_config(alembic_cfg)
    target_revision = script.get_current_head()

    current_revision: str | None = None
    if db_path.exists():
        engine = create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_revision = context.get_current_revision()

    mode = "dry-run" if dry_run else "apply"
    console.print(
        f"[dim]Schema migrate ({mode}):[/dim] {current_revision or 'base'} → {target_revision}"
    )

    try:
        if dry_run:
            _validate_migrations_on_temp_db(alembic_ini=alembic_ini, db_path=db_path)
        else:
            command.upgrade(alembic_cfg, "head")
    except Exception as exc:
        console.print(f"[red]Error:[/red] Migration failed: {exc}")
        raise typer.Exit(1) from None

    if dry_run:
        console.print("[green]✓[/green] Dry-run complete (validated on a temporary DB copy).")
    else:
        console.print("[green]✓[/green] Migration applied successfully.")


@app.command("sync-markets")
def data_sync_markets(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    status: Annotated[
        str | None,
        typer.Option("--status", "-s", help="Filter by status (open, closed, etc)."),
    ] = None,
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            help="Optional pagination safety limit. None = iterate until exhausted.",
        ),
    ] = None,
    mve_filter: Annotated[
        str | None,
        typer.Option(
            "--mve-filter",
            help="Filter multivariate events: 'exclude' (skip sports parlays) or 'only'.",
        ),
    ] = None,
    include_mve_events: Annotated[
        bool,
        typer.Option(
            "--include-mve-events",
            help="Also sync multivariate events via /events/multivariate.",
        ),
    ] = False,
) -> None:
    """Sync markets from Kalshi API to database."""
    from typing import Literal, cast

    from kalshi_research.cli.db import open_db
    from kalshi_research.data import DataFetcher

    # Validate mve_filter value
    mve_filter_typed: Literal["only", "exclude"] | None = None
    if mve_filter is not None:
        if mve_filter not in ("only", "exclude"):
            console.print(
                f"[red]Error:[/red] --mve-filter must be 'only' or 'exclude', got '{mve_filter}'"
            )
            raise typer.Exit(1)
        mve_filter_typed = cast("Literal['only', 'exclude']", mve_filter)

    async def _sync() -> None:
        async with open_db(db_path) as db, DataFetcher(db) as fetcher:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task1 = progress.add_task("Syncing events...", total=None)
                events = await fetcher.sync_events(
                    max_pages=max_pages,
                    include_multivariate=include_mve_events,
                )
                progress.update(task1, description=f"Synced {events} events")

                progress.add_task("Syncing markets...", total=None)
                markets = await fetcher.sync_markets(
                    status=status, max_pages=max_pages, mve_filter=mve_filter_typed
                )

        console.print(f"[green]✓[/green] Synced {events} events and {markets} markets")

    run_async(_sync())


@app.command("sync-settlements")
def data_sync_settlements(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            help="Optional pagination safety limit. None = iterate until exhausted.",
        ),
    ] = None,
) -> None:
    """Sync settled market outcomes from Kalshi API to database.

    Notes:
        Kalshi exposes `settlement_ts` (added Dec 19, 2025) for settled markets.
        We store `Settlement.settled_at` using `Market.settlement_ts` when available, falling back
        to `Market.expiration_time` for historical/legacy data.
    """
    from kalshi_research.cli.db import open_db
    from kalshi_research.data import DataFetcher

    async def _sync() -> None:
        async with open_db(db_path) as db, DataFetcher(db) as fetcher:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Syncing settlements...", total=None)
                settlements = await fetcher.sync_settlements(max_pages=max_pages)

        console.print(f"[green]✓[/green] Synced {settlements} settlements")

    run_async(_sync())


@app.command("sync-trades")
def data_sync_trades(
    ticker: Annotated[
        str | None,
        typer.Option("--ticker", help="Optional market ticker filter."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Max trades to fetch (Kalshi caps at 1000)."),
    ] = 100,
    min_ts: Annotated[
        int | None,
        typer.Option("--min-ts", help="Filter: min Unix timestamp (seconds)."),
    ] = None,
    max_ts: Annotated[
        int | None,
        typer.Option("--max-ts", help="Filter: max Unix timestamp (seconds)."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Write results to a CSV file."),
    ] = None,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output results as JSON to stdout."),
    ] = False,
) -> None:
    """Fetch public trade history from Kalshi (GET /markets/trades)."""
    import csv
    import json

    from kalshi_research.api.exceptions import KalshiAPIError
    from kalshi_research.cli.client_factory import public_client

    if output is not None and output_json:
        console.print("[red]Error:[/red] Choose one of --output or --json (not both).")
        raise typer.Exit(2)

    async def _fetch() -> list[dict[str, object]]:
        async with public_client() as client:
            try:
                trades = await client.get_trades(
                    ticker=ticker,
                    limit=limit,
                    min_ts=min_ts,
                    max_ts=max_ts,
                )
            except KalshiAPIError as e:
                exit_kalshi_api_error(e)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        return [t.model_dump(mode="json") for t in trades]

    trade_rows = run_async(_fetch())

    if output_json:
        typer.echo(json.dumps(trade_rows, indent=2, default=str))
        return

    if output is None:
        if not trade_rows:
            console.print("[yellow]No trades returned for the given filters.[/yellow]")
            return
        table = Table(title="Trades")
        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("Time", style="dim")
        table.add_column("YES", justify="right", style="green")
        table.add_column("NO", justify="right", style="red")
        table.add_column("Qty", justify="right", style="magenta")
        table.add_column("Taker", style="white")

        for row in trade_rows[:25]:
            table.add_row(
                str(row.get("ticker", "")),
                str(row.get("created_time", "")),
                str(row.get("yes_price", "")),
                str(row.get("no_price", "")),
                str(row.get("count", "")),
                str(row.get("taker_side", "")),
            )

        console.print(table)
        if len(trade_rows) > 25:
            console.print(
                f"[dim]Showing 25 of {len(trade_rows)} trades. Use --output to export.[/dim]"
            )
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "trade_id",
        "ticker",
        "created_time",
        "yes_price",
        "no_price",
        "count",
        "taker_side",
    ]
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in trade_rows:
            writer.writerow({k: row.get(k) for k in fieldnames})

    console.print(f"[green]✓[/green] Exported {len(trade_rows)} trades to {output}")


@app.command("snapshot")
def data_snapshot(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    status: Annotated[
        str | None,
        typer.Option("--status", "-s", help="Filter by status (default: open)."),
    ] = "open",
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            help="Optional pagination safety limit. None = iterate until exhausted.",
        ),
    ] = None,
) -> None:
    """Take a price snapshot of all markets."""
    from kalshi_research.cli.db import open_db
    from kalshi_research.data import DataFetcher

    async def _snapshot() -> None:
        async with open_db(db_path) as db, DataFetcher(db) as fetcher:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Taking snapshot...", total=None)
                count = await fetcher.take_snapshot(status=status, max_pages=max_pages)

        console.print(f"[green]✓[/green] Took {count} price snapshots")

    run_async(_snapshot())


@app.command("collect")
def data_collect(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    interval: Annotated[
        int,
        typer.Option("--interval", "-i", help="Interval in minutes between snapshots."),
    ] = 15,
    once: Annotated[
        bool,
        typer.Option("--once", help="Run a single full sync and exit."),
    ] = False,
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            help="Optional pagination safety limit. None = iterate until exhausted.",
        ),
    ] = None,
    include_mve_events: Annotated[
        bool,
        typer.Option(
            "--include-mve-events",
            help="Also sync multivariate events via /events/multivariate.",
        ),
    ] = False,
) -> None:
    """Run continuous data collection."""
    from kalshi_research.cli.db import open_db
    from kalshi_research.data import DataFetcher, DataScheduler

    async def _collect() -> None:
        async with open_db(db_path) as db, DataFetcher(db) as fetcher:
            if once:
                counts = await fetcher.full_sync(
                    max_pages=max_pages,
                    include_multivariate=include_mve_events,
                )
                console.print(
                    "[green]✓[/green] Full sync complete: "
                    f"{counts['events']} events, {counts['markets']} markets, "
                    f"{counts['snapshots']} snapshots"
                )
                return

            scheduler = DataScheduler()
            write_lock = asyncio.Lock()

            async def sync_task() -> None:
                async with write_lock:
                    await fetcher.sync_markets(status="open", max_pages=max_pages)

            async def snapshot_task() -> None:
                async with write_lock:
                    count = await fetcher.take_snapshot(status="open", max_pages=max_pages)
                    console.print(f"[dim]Took {count} snapshots[/dim]")

            # Schedule tasks
            await scheduler.schedule_interval(
                "market_sync",
                sync_task,
                interval_seconds=3600,  # Hourly
                run_immediately=False,
            )
            await scheduler.schedule_interval(
                "price_snapshot",
                snapshot_task,
                interval_seconds=interval * 60,
                run_immediately=False,
            )

            # Initial sync before starting scheduled tasks.
            # Prevents in-process overlap on startup.
            await fetcher.full_sync(
                max_pages=max_pages,
                include_multivariate=include_mve_events,
            )

            console.print(
                f"[green]✓[/green] Starting collection (interval: {interval}m). "
                "Press Ctrl+C to stop."
            )

            async with scheduler:
                # Run forever until interrupted
                try:
                    while True:
                        await asyncio.sleep(1)
                except asyncio.CancelledError:
                    pass

    run_async(_collect())


@app.command("export")
def data_export(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output directory for exports."),
    ] = DEFAULT_EXPORTS_DIR,
    format_type: Annotated[
        str,
        typer.Option("--format", "-f", help="Export format (parquet, csv)."),
    ] = "parquet",
) -> None:
    """Export data to Parquet or CSV for analysis."""
    from kalshi_research.data.export import export_to_csv, export_to_parquet

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(f"Exporting to {format_type}...", total=None)

        if format_type == "parquet":
            export_to_parquet(db_path, output)
        elif format_type == "csv":
            export_to_csv(db_path, output)
        else:
            console.print(f"[red]Error:[/red] Unknown format: {format_type}")
            raise typer.Exit(1)

    console.print(f"[green]✓[/green] Exported to {output}")


@app.command("stats")
def data_stats(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Show database statistics."""
    from kalshi_research.cli.db import open_db_session
    from kalshi_research.data.repositories import (
        EventRepository,
        MarketRepository,
        PriceRepository,
    )

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    async def _stats() -> None:
        async with open_db_session(db_path) as session:
            event_repo = EventRepository(session)
            market_repo = MarketRepository(session)
            price_repo = PriceRepository(session)

            events = await event_repo.get_all()
            markets = await market_repo.get_all()
            market_counts = await market_repo.count_by_status()

            # Sample snapshot counts for a few markets
            active_markets = await market_repo.get_active()
            sample_markets = list(active_markets)[:5]
            snapshot_counts = {}
            for m in sample_markets:
                snapshot_counts[m.ticker] = await price_repo.count_for_market(m.ticker)

        table = Table(title="Database Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Events", str(len(events)))
        table.add_row("Total Markets", str(len(markets)))

        for status, count in sorted(market_counts.items()):
            table.add_row(f"  - {status}", str(count))

        if snapshot_counts:
            table.add_row("Sample Snapshot Counts", "")
            for ticker, count in snapshot_counts.items():
                table.add_row(f"  - {ticker}", str(count))

        console.print(table)

    run_async(_stats())


@app.command("prune")
def data_prune(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
    snapshots_older_than_days: Annotated[
        int | None,
        typer.Option(
            "--snapshots-older-than-days",
            help="Delete price snapshots older than N days.",
        ),
    ] = None,
    news_older_than_days: Annotated[
        int | None,
        typer.Option(
            "--news-older-than-days",
            help="Delete collected news articles older than N days (by collected_at).",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--apply",
            help="Preview deletions without applying changes (default: dry-run).",
        ),
    ] = True,
) -> None:
    """Prune old rows to keep the database manageable."""
    from datetime import UTC, datetime, timedelta

    from kalshi_research.cli.db import open_db_session
    from kalshi_research.data.maintenance import (
        PruneCounts,
        apply_prune,
        compute_prune_counts,
    )

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    if snapshots_older_than_days is not None and snapshots_older_than_days < 0:
        console.print("[red]Error:[/red] --snapshots-older-than-days must be >= 0")
        raise typer.Exit(2)
    if news_older_than_days is not None and news_older_than_days < 0:
        console.print("[red]Error:[/red] --news-older-than-days must be >= 0")
        raise typer.Exit(2)

    if snapshots_older_than_days is None and news_older_than_days is None:
        console.print("[red]Error:[/red] No prune targets specified.")
        console.print(
            "[dim]Provide at least one of --snapshots-older-than-days or --news-older-than-days."
            "[/dim]"
        )
        raise typer.Exit(2)

    now = datetime.now(UTC)
    snapshots_before = (
        now - timedelta(days=snapshots_older_than_days)
        if snapshots_older_than_days is not None
        else None
    )
    news_before = (
        now - timedelta(days=news_older_than_days) if news_older_than_days is not None else None
    )

    async def _prune() -> tuple[datetime, PruneCounts]:
        async with open_db_session(db_path) as session:
            if dry_run:
                counts = await compute_prune_counts(
                    session,
                    snapshots_before=snapshots_before,
                    news_before=news_before,
                )
                return (now, counts)

            async with session.begin():
                counts = await apply_prune(
                    session,
                    snapshots_before=snapshots_before,
                    news_before=news_before,
                )
            return (now, counts)

    pruned_at, counts = run_async(_prune())

    table = Table(title="Prune Summary")
    table.add_column("Category", style="cyan")
    table.add_column("Cutoff", style="dim")
    table.add_column("Rows", justify="right", style="green")

    if snapshots_before is not None:
        table.add_row("price_snapshots", snapshots_before.isoformat(), str(counts.price_snapshots))
    if news_before is not None:
        table.add_row("news_articles", news_before.isoformat(), str(counts.news_articles))
        table.add_row(
            "news_article_markets",
            news_before.isoformat(),
            str(counts.news_article_markets),
        )
        table.add_row(
            "news_article_events",
            news_before.isoformat(),
            str(counts.news_article_events),
        )
        table.add_row("news_sentiments", news_before.isoformat(), str(counts.news_sentiments))

    console.print(table)

    mode = "dry-run" if dry_run else "applied"
    console.print(f"[green]✓[/green] Prune {mode} at {pruned_at.isoformat()} (UTC)")


@app.command("vacuum")
def data_vacuum(
    db_path: Annotated[
        Path,
        typer.Option("--db", "-d", help="Path to SQLite database file."),
    ] = DEFAULT_DB_PATH,
) -> None:
    """Run SQLite VACUUM to reclaim disk space after large deletes."""
    from sqlalchemy import create_engine, text

    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found at {db_path}")
        raise typer.Exit(1)

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("VACUUM"))
    finally:
        engine.dispose()

    console.print("[green]✓[/green] Vacuum complete")
