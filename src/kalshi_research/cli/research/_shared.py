"""Shared utilities for research CLI commands."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer

from kalshi_research.cli.utils import (
    atomic_write_json,
    console,
    exit_kalshi_api_error,
    load_json_storage_file,
)
from kalshi_research.paths import DEFAULT_THESES_PATH

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market
    from kalshi_research.research.thesis import Thesis as ThesisModel
    from kalshi_research.research.thesis import ThesisEvidence, ThesisTracker


def _get_thesis_file() -> Path:
    """Get path to thesis storage file."""
    return DEFAULT_THESES_PATH


def _load_theses() -> dict[str, Any]:
    """Load theses from storage."""
    thesis_file = _get_thesis_file()
    return load_json_storage_file(path=thesis_file, kind="Theses", required_list_key="theses")


def _save_theses(data: dict[str, Any]) -> None:
    """Save theses to storage."""
    thesis_file = _get_thesis_file()
    atomic_write_json(thesis_file, data)


def _resolve_thesis(tracker: "ThesisTracker", thesis_id: str) -> "ThesisModel | None":
    """Resolve a thesis by ID or prefix.

    Tries exact match first, then falls back to prefix search.
    """
    thesis = tracker.get(thesis_id)
    if thesis is not None:
        return thesis
    return next((t for t in tracker.list_all() if t.id.startswith(thesis_id)), None)


def _serialize_thesis_evidence(evidence_items: "list[ThesisEvidence]") -> list[dict[str, Any]]:
    """Serialize thesis evidence items to JSON-compatible dicts."""
    return [
        {
            "url": e.url,
            "title": e.title,
            "source_domain": e.source_domain,
            "published_date": e.published_date.isoformat() if e.published_date else None,
            "snippet": e.snippet,
            "supports": e.supports,
            "relevance_score": e.relevance_score,
            "added_at": e.added_at.isoformat(),
        }
        for e in evidence_items
    ]


async def _fetch_market(ticker: str) -> "Market":
    """Fetch a market from the Kalshi public API.

    Prints a CLI-friendly error message and exits with code 2 when the ticker is not found
    (HTTP 404), otherwise exits with code 1 on errors.

    Args:
        ticker: Market ticker to fetch.

    Returns:
        The API `Market` model.

    Raises:
        typer.Exit: If the market cannot be fetched.
    """
    from kalshi_research.api.exceptions import KalshiAPIError
    from kalshi_research.cli.client_factory import public_client

    async with public_client() as kalshi:
        try:
            return await kalshi.get_market(ticker)
        except KalshiAPIError as e:
            exit_kalshi_api_error(e)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None
