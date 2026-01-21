"""Trim log command for alerts monitor log file management."""

import sys
from pathlib import Path
from typing import Annotated

import typer

from kalshi_research.cli.utils import console
from kalshi_research.paths import DEFAULT_ALERT_LOG


def alerts_trim_log(
    log_path: Annotated[
        Path,
        typer.Option("--log", help="Path to the alerts monitor log file."),
    ] = DEFAULT_ALERT_LOG,
    max_mb: Annotated[
        int,
        typer.Option("--max-mb", help="Trim the log when it exceeds this many MB."),
    ] = 50,
    keep_mb: Annotated[
        int,
        typer.Option("--keep-mb", help="When trimming, keep the last N MB."),
    ] = 5,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--apply",
            help="Preview changes without modifying the log (default: dry-run).",
        ),
    ] = True,
) -> None:
    """Trim the alerts monitor log to keep disk usage bounded."""
    import errno
    import os

    if max_mb <= 0:
        console.print("[red]Error:[/red] --max-mb must be > 0")
        raise typer.Exit(2)
    if keep_mb < 0:
        console.print("[red]Error:[/red] --keep-mb must be >= 0")
        raise typer.Exit(2)
    if keep_mb > max_mb:
        console.print("[red]Error:[/red] --keep-mb must be <= --max-mb")
        raise typer.Exit(2)

    if not log_path.exists():
        console.print(f"[yellow]No log file found at {log_path}[/yellow]")
        return

    size_bytes = log_path.stat().st_size
    max_bytes = max_mb * 1024 * 1024
    keep_bytes = keep_mb * 1024 * 1024

    if size_bytes <= max_bytes:
        console.print(f"[green]✓[/green] Log size OK ({size_bytes} bytes)")
        return

    if dry_run:
        console.print(
            f"[yellow]Dry-run:[/yellow] Would trim {log_path} "
            f"from {size_bytes} bytes to ~{keep_bytes} bytes"
        )
        return

    with log_path.open("r+b") as f:
        if sys.platform != "win32":
            import fcntl

            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                if exc.errno in (errno.EACCES, errno.EAGAIN):
                    console.print(
                        "[red]Error:[/red] Log file is locked. Stop the alert monitor daemon "
                        "before trimming."
                    )
                    raise typer.Exit(2) from None
                raise

        if keep_bytes <= 0:
            f.truncate(0)
        else:
            f.seek(0, os.SEEK_END)
            end_pos = f.tell()
            start_pos = max(0, end_pos - keep_bytes)
            f.seek(start_pos)
            tail = f.read()
            f.seek(0)
            f.truncate(0)
            f.write(tail)

    new_size = log_path.stat().st_size
    console.print(f"[green]✓[/green] Trimmed log to {new_size} bytes: {log_path}")
