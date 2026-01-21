"""Typer CLI commands for research workflows and thesis tracking.

This package provides research commands for the Kalshi CLI:
- thesis: Thesis management (create, list, show, edit, resolve, check-invalidation, suggest)
- cache: Exa cache maintenance
- context: Market context research
- topic: Topic research for thesis ideation
- similar: Find similar pages via Exa
- deep: Async deep research via Exa /research/v1
- backtest: Thesis backtesting
"""

import typer

# Re-export shared utilities for backwards compatibility with tests that patch them
from kalshi_research.cli.research._shared import (
    _fetch_market,
    _get_thesis_file,
    _load_theses,
    _resolve_thesis,
    _save_theses,
    _serialize_thesis_evidence,
)
from kalshi_research.cli.research.backtest import (
    _display_backtest_results,
    _parse_backtest_dates,
    research_backtest,
)
from kalshi_research.cli.research.cache import cache_app
from kalshi_research.cli.research.context import (
    _render_market_context,
    _research_market_context,
    _run_market_context_research,
    research_context,
)
from kalshi_research.cli.research.deep import (
    _load_research_output_schema,
    _run_deep_research,
    research_deep,
)
from kalshi_research.cli.research.similar import research_similar
from kalshi_research.cli.research.thesis import (
    _check_thesis_invalidation,
    _fetch_and_render_linked_positions,
    _find_thesis_by_id,
    _gather_thesis_research_data,
    _print_invalidation_signals,
    _render_thesis_cases_and_updates,
    _render_thesis_evidence,
    _render_thesis_fields_table,
    _render_thesis_header,
    thesis_app,
)
from kalshi_research.cli.research.topic import (
    _render_topic_research,
    _run_topic_research,
    research_topic,
)

# Create main app and register sub-apps and commands
app = typer.Typer(help="Research and thesis tracking commands.")
app.add_typer(thesis_app, name="thesis")
app.add_typer(cache_app, name="cache")

# Register top-level research commands
app.command("context")(research_context)
app.command("topic")(research_topic)
app.command("similar")(research_similar)
app.command("deep")(research_deep)
app.command("backtest")(research_backtest)

# Public API exports
__all__ = [
    "_check_thesis_invalidation",
    "_display_backtest_results",
    "_fetch_and_render_linked_positions",
    "_fetch_market",
    "_find_thesis_by_id",
    "_gather_thesis_research_data",
    # Shared utilities (for backwards compatibility with tests)
    "_get_thesis_file",
    "_load_research_output_schema",
    "_load_theses",
    # Helper functions exposed for testing
    "_parse_backtest_dates",
    "_print_invalidation_signals",
    "_render_market_context",
    "_render_thesis_cases_and_updates",
    "_render_thesis_evidence",
    "_render_thesis_fields_table",
    "_render_thesis_header",
    "_render_topic_research",
    "_research_market_context",
    "_resolve_thesis",
    "_run_deep_research",
    "_run_market_context_research",
    "_run_topic_research",
    "_save_theses",
    "_serialize_thesis_evidence",
    # Main app
    "app",
    "cache_app",
    "research_backtest",
    # Commands (for direct registration if needed)
    "research_context",
    "research_deep",
    "research_similar",
    "research_topic",
    # Sub-apps
    "thesis_app",
]
