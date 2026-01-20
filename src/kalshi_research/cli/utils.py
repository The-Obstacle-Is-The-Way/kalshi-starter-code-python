"""Shared utilities for CLI commands (console output, JSON storage, async helpers)."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import TYPE_CHECKING, Any, TypeVar, cast

import typer
from rich.console import Console

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from pathlib import Path

console = Console()

T = TypeVar("T")


def run_async(coro: Coroutine[object, object, T]) -> T:
    """Run a coroutine from a sync CLI command.

    Centralizes asyncio.run() usage across CLI modules to ensure consistent
    handling of KeyboardInterrupt (Ctrl+C).

    Raises:
        typer.Exit: With code 130 on KeyboardInterrupt (standard SIGINT exit code).
    """
    try:
        return asyncio.run(coro)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        raise typer.Exit(130) from None


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON atomically (temp file + fsync + rename)."""
    import os

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp.{uuid.uuid4().hex}")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    tmp_path.replace(path)


def load_json_storage_file(*, path: Path, kind: str, required_list_key: str) -> dict[str, Any]:
    """Load and validate a JSON storage file used by CLI commands.

    Returns a default object if the file does not exist, and exits with an error
    message if the file exists but is invalid JSON or has an unexpected schema.
    """
    if not path.exists():
        return {required_list_key: []}

    try:
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError:
        console.print(f"[red]Error:[/red] {kind} file is not valid JSON: {path}")
        console.print("[dim]Fix the file or restore from backup.[/dim]")
        console.print("[dim]This command will not modify it.[/dim]")
        raise typer.Exit(1) from None

    if not isinstance(raw, dict):
        console.print(f"[red]Error:[/red] {kind} file must contain a JSON object: {path}")
        raise typer.Exit(1) from None

    if required_list_key not in raw or not isinstance(raw[required_list_key], list):
        console.print(
            f"[red]Error:[/red] {kind} file has an unexpected schema: {path} "
            f"(expected key '{required_list_key}: [...]')"
        )
        raise typer.Exit(1) from None

    return cast("dict[str, Any]", raw)


def print_budget_exhausted(obj: object) -> None:
    """Print a standardized budget-exhausted warning if applicable.

    Checks for `budget_exhausted` and `budget` attributes on the object.
    """
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
