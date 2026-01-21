"""LLM provider interface for synthesis.

Phase 1: Schema-validated, backend-selectable synthesizers.

- `MockSynthesizer` stays available for tests/CI and zero-dependency runs.
- `ClaudeSynthesizer` (Anthropic) provides a real, structured-output backend.
"""

from __future__ import annotations

from ._claude import ClaudeSynthesizer
from ._factory import get_synthesizer
from ._mock import MockSynthesizer
from ._schemas import StructuredSynthesizer, SynthesisInput

__all__ = [
    "ClaudeSynthesizer",
    "MockSynthesizer",
    "StructuredSynthesizer",
    "SynthesisInput",
    "get_synthesizer",
]
