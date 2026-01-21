"""Shared helper functions for market CLI commands."""

from __future__ import annotations

import typer

from kalshi_research.cli.utils import console


def normalize_market_list_status(status: str | None) -> str | None:
    """Normalize and validate market status filter values.

    Handles the common footgun where response status values (like "active")
    differ from filter values (like "open").

    Args:
        status: Raw status filter value from CLI.

    Returns:
        Normalized lowercase status value, or None.

    Raises:
        typer.Exit: If status is invalid.
    """
    if status is None:
        return None

    from kalshi_research.api.models.market import MarketFilterStatus

    raw = status
    normalized = raw.strip().lower()

    # Common footgun: response status values differ from filter values.
    # Users often try "active" when they mean "open". Be helpful, but explicit.
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
        console.print(
            "[dim]Note: API responses may contain status values like 'active' or 'determined', "
            "but the /markets filter uses different values.[/dim]"
        )
        raise typer.Exit(2)

    return normalized


def optional_lower(raw: str | None) -> str | None:
    """Convert string to lowercase, handling None.

    Args:
        raw: String to convert.

    Returns:
        Lowercase string, empty string if input was whitespace-only, or None.
    """
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped.lower() if stripped else None
