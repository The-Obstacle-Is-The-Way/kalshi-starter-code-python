"""Shared helper functions for portfolio CLI commands."""

from __future__ import annotations

import os
from typing import Any

import typer

from kalshi_research.cli.utils import console, load_json_storage_file
from kalshi_research.paths import DEFAULT_THESES_PATH

PORTFOLIO_SYNC_TIP = (
    "[dim]Tip: run `kalshi portfolio sync` to populate/refresh the local cache.[/dim]"
)


def format_signed_currency(cents: int) -> str:
    """Format a cent value as a signed currency string with color.

    Args:
        cents: Amount in cents (can be positive, negative, or zero).

    Returns:
        Formatted string with color markup.
    """
    value = f"${cents / 100:.2f}"
    if cents > 0:
        return f"[green]+{value}[/green]"
    if cents < 0:
        return f"[red]{value}[/red]"
    return value


def load_theses() -> dict[str, Any]:
    """Load theses from storage.

    Returns:
        Dictionary containing theses data with "theses" list key.
    """
    return load_json_storage_file(
        path=DEFAULT_THESES_PATH, kind="Theses", required_list_key="theses"
    )


def validate_environment_override(environment: str | None) -> str | None:
    """Validate and normalize a portfolio `--env` override.

    Args:
        environment: Raw CLI environment value (`demo` or `prod`), or `None`.

    Returns:
        Normalized environment string, or `None` when no override was provided.

    Raises:
        typer.Exit: If the environment value is invalid.
    """
    if environment is None:
        return None

    from kalshi_research.api.config import Environment

    raw = environment
    normalized = raw.strip().lower()
    try:
        return Environment(normalized).value
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid environment '{raw}'. Expected 'prod' or 'demo'.")
        raise typer.Exit(1) from None


def require_auth_env(
    *, purpose: str, environment: str | None
) -> tuple[str, str | None, str | None]:
    """Require and resolve authentication environment variables.

    Args:
        purpose: Human-readable purpose for the auth (for error messages).
        environment: Optional environment override (demo or prod).

    Returns:
        Tuple of (key_id, private_key_path, private_key_b64).

    Raises:
        typer.Exit: If required credentials are not configured.
    """
    from kalshi_research.api.credentials import (
        get_kalshi_auth_env_var_names,
        resolve_kalshi_auth_env,
    )

    key_id, private_key_path, private_key_b64 = resolve_kalshi_auth_env(environment=environment)
    key_id_var, private_key_path_var, private_key_b64_var = get_kalshi_auth_env_var_names(
        environment=environment
    )

    if not key_id or (not private_key_path and not private_key_b64):
        console.print(f"[red]Error:[/red] {purpose} requires authentication.")
        console.print(
            f"[dim]Set {key_id_var} and {private_key_path_var} "
            f"(or {private_key_b64_var}) to enable authenticated commands.[/dim]"
        )
        raise typer.Exit(1)

    return key_id, private_key_path, private_key_b64


def resolve_rate_tier_override(rate_tier: str | None) -> str:
    """Resolve and validate a rate tier override.

    Args:
        rate_tier: Raw CLI rate tier value, or None.

    Returns:
        Normalized rate tier string (from CLI, env var, or default).

    Raises:
        typer.Exit: If rate tier is invalid.
    """
    from kalshi_research.api.rate_limiter import RateTier

    raw = rate_tier or os.getenv("KALSHI_RATE_TIER") or RateTier.BASIC.value
    normalized = raw.strip().lower()
    try:
        return RateTier(normalized).value
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid rate tier '{raw}'.")
        console.print("[dim]Expected one of: basic, advanced, premier, prime.[/dim]")
        raise typer.Exit(1) from None
