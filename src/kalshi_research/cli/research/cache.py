"""Typer CLI commands for Exa cache management."""

from pathlib import Path
from typing import Annotated

import typer

from kalshi_research.cli.utils import console

cache_app = typer.Typer(help="Exa cache maintenance commands.")


@cache_app.command("clear")
def research_cache_clear(
    clear_all: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Clear all cache entries (default: clear expired only).",
        ),
    ] = False,
    cache_dir: Annotated[
        Path | None,
        typer.Option(
            "--cache-dir",
            help="Optional override for Exa cache directory (default: data/exa_cache/).",
        ),
    ] = None,
) -> None:
    """Clear Exa response cache entries on disk."""
    from kalshi_research.exa.cache import ExaCache

    cache = ExaCache(cache_dir) if cache_dir else ExaCache()
    removed = cache.clear() if clear_all else cache.clear_expired()

    mode = "all" if clear_all else "expired"
    console.print(f"[green]✓[/green] Cleared {removed} Exa cache entries ({mode})")
