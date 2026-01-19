"""Research providers for agent system."""

from .kalshi import fetch_market_info, fetch_price_snapshot
from .llm import (
    ClaudeSynthesizer,
    MockSynthesizer,
    StructuredSynthesizer,
    SynthesisInput,
    get_synthesizer,
)

__all__ = [
    "ClaudeSynthesizer",
    "MockSynthesizer",
    "StructuredSynthesizer",
    "SynthesisInput",
    "fetch_market_info",
    "fetch_price_snapshot",
    "get_synthesizer",
]
