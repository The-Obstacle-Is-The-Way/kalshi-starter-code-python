"""Research providers for agent system."""

from .kalshi import fetch_market_info, fetch_price_snapshot
from .llm import (
    ClaudeSynthesizer,
    MockSynthesizer,
    StructuredSynthesizer,
    SynthesisInput,
    get_synthesizer,
)

# Note: llm.py was split into llm/ package (DEBT-043-D7, 2026-01-21)

__all__ = [
    "ClaudeSynthesizer",
    "MockSynthesizer",
    "StructuredSynthesizer",
    "SynthesisInput",
    "fetch_market_info",
    "fetch_price_snapshot",
    "get_synthesizer",
]
