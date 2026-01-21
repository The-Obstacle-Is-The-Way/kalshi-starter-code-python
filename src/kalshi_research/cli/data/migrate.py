"""Database migration command."""

from pathlib import Path
from typing import Annotated

import typer

from kalshi_research.cli.data._helpers import find_alembic_ini, validate_migrations_on_temp_db
from kalshi_research.cli.utils import console
from kalshi_research.paths import DEFAULT_DB_PATH


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
        alembic_ini = find_alembic_ini()
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
            validate_migrations_on_temp_db(alembic_ini=alembic_ini, db_path=db_path)
        else:
            command.upgrade(alembic_cfg, "head")
    except Exception as exc:
        console.print(f"[red]Error:[/red] Migration failed: {exc}")
        raise typer.Exit(1) from None

    if dry_run:
        console.print("[green]✓[/green] Dry-run complete (validated on a temporary DB copy).")
    else:
        console.print("[green]✓[/green] Migration applied successfully.")
