"""Content option normalization helpers for Exa API requests."""

from __future__ import annotations

from kalshi_research.exa.models import (
    ContextOptions,
    HighlightsOptions,
    SummaryOptions,
    TextContentsOptions,
)


class ContentNormalizationMixin:
    """Mixin providing content option normalization helpers."""

    def _normalize_text_option(
        self, text: bool | TextContentsOptions | None
    ) -> bool | TextContentsOptions | None:
        if isinstance(text, TextContentsOptions):
            return text
        if text:
            return True
        return None

    def _normalize_highlights_option(
        self, highlights: bool | HighlightsOptions | None
    ) -> HighlightsOptions | None:
        if isinstance(highlights, HighlightsOptions):
            return highlights
        if highlights:
            return HighlightsOptions()
        return None

    def _normalize_summary_option(
        self, summary: bool | SummaryOptions | None
    ) -> SummaryOptions | None:
        if isinstance(summary, SummaryOptions):
            return summary
        if summary:
            return SummaryOptions()
        return None

    def _normalize_context_option(
        self, context: bool | ContextOptions | None
    ) -> bool | ContextOptions | None:
        if isinstance(context, ContextOptions):
            return context
        if context:
            return True
        return None
