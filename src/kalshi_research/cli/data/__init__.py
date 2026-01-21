"""Typer CLI commands for database setup and data synchronization.

This package provides data management commands for the Kalshi CLI:
- init: Initialize the database
- migrate: Run Alembic schema migrations
- sync-markets: Sync markets from Kalshi API
- sync-settlements: Sync settlements from Kalshi API
- sync-trades: Fetch public trade history
- snapshot: Take a price snapshot
- collect: Run continuous data collection
- export: Export data to Parquet or CSV
- stats: Show database statistics
- prune: Prune old rows
- vacuum: Run SQLite VACUUM
"""

import typer

from kalshi_research.cli.data._helpers import find_alembic_ini, validate_migrations_on_temp_db
from kalshi_research.cli.data.collect import data_collect
from kalshi_research.cli.data.export_cmd import data_export
from kalshi_research.cli.data.init_cmd import data_init
from kalshi_research.cli.data.maintenance import data_prune, data_vacuum
from kalshi_research.cli.data.migrate import data_migrate
from kalshi_research.cli.data.snapshot import data_snapshot
from kalshi_research.cli.data.stats import data_stats
from kalshi_research.cli.data.sync import (
    data_sync_markets,
    data_sync_settlements,
    data_sync_trades,
)

# Create main app and register commands
app = typer.Typer(help="Data management commands.")

app.command("init")(data_init)
app.command("migrate")(data_migrate)
app.command("sync-markets")(data_sync_markets)
app.command("sync-settlements")(data_sync_settlements)
app.command("sync-trades")(data_sync_trades)
app.command("snapshot")(data_snapshot)
app.command("collect")(data_collect)
app.command("export")(data_export)
app.command("stats")(data_stats)
app.command("prune")(data_prune)
app.command("vacuum")(data_vacuum)

# Public API exports for backwards compatibility
__all__ = [
    "app",
    "data_collect",
    "data_export",
    "data_init",
    "data_migrate",
    "data_prune",
    "data_snapshot",
    "data_stats",
    "data_sync_markets",
    "data_sync_settlements",
    "data_sync_trades",
    "data_vacuum",
    "find_alembic_ini",
    "validate_migrations_on_temp_db",
]
