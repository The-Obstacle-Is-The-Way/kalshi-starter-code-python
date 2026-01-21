"""Factory function for synthesizer backends."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ._claude import ClaudeSynthesizer
from ._mock import MockSynthesizer

if TYPE_CHECKING:
    from ._schemas import StructuredSynthesizer


def get_synthesizer(
    backend: str | None = None,
    *,
    max_cost_usd: float | None = None,
) -> StructuredSynthesizer:
    """Construct a synthesizer from config.

    Args:
        backend: Explicit backend override ("anthropic" or "mock"). When None, reads
            KALSHI_SYNTHESIZER_BACKEND (default: "anthropic").
        max_cost_usd: Optional per-call budget for the backend.

    Returns:
        A synthesizer instance.
    """
    backend_raw = backend
    if backend_raw is None:
        backend_raw = os.getenv("KALSHI_SYNTHESIZER_BACKEND") or "anthropic"
    backend_value = backend_raw.strip().lower()

    if backend_value == "mock":
        return MockSynthesizer()
    if backend_value == "anthropic":
        return ClaudeSynthesizer(max_cost_usd=max_cost_usd)

    raise ValueError(f"Unknown synthesizer backend: {backend_value!r}")
