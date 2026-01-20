"""Typer CLI commands for thesis management.

This subpackage provides thesis-related CLI commands:
- create: Create a new research thesis
- list: List all theses
- show: Show thesis details
- edit: Edit a thesis
- resolve: Resolve a thesis with an outcome
- check-invalidation: Check for invalidation signals
- suggest: Generate thesis suggestions from research
"""

import typer

from kalshi_research.cli.research.thesis._commands import (
    _check_thesis_invalidation,
    _gather_thesis_research_data,
    research_thesis_check_invalidation,
    research_thesis_create,
    research_thesis_edit,
    research_thesis_list,
    research_thesis_resolve,
    research_thesis_show,
)
from kalshi_research.cli.research.thesis._helpers import (
    _fetch_and_render_linked_positions,
    _find_thesis_by_id,
    _print_invalidation_signals,
    _render_thesis_cases_and_updates,
    _render_thesis_evidence,
    _render_thesis_fields_table,
    _render_thesis_header,
)
from kalshi_research.cli.research.thesis._suggest import research_thesis_suggest

# Create thesis app and register commands
thesis_app = typer.Typer(help="Thesis management commands.")
thesis_app.command("create")(research_thesis_create)
thesis_app.command("list")(research_thesis_list)
thesis_app.command("show")(research_thesis_show)
thesis_app.command("edit")(research_thesis_edit)
thesis_app.command("resolve")(research_thesis_resolve)
thesis_app.command("check-invalidation")(research_thesis_check_invalidation)
thesis_app.command("suggest")(research_thesis_suggest)

# Re-export for backwards compatibility
__all__ = [
    # Async helpers
    "_check_thesis_invalidation",
    "_fetch_and_render_linked_positions",
    "_find_thesis_by_id",
    "_gather_thesis_research_data",
    # Render helpers
    "_print_invalidation_signals",
    "_render_thesis_cases_and_updates",
    "_render_thesis_evidence",
    "_render_thesis_fields_table",
    "_render_thesis_header",
    "thesis_app",
]
