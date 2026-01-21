"""Anthropic pricing utilities."""

from __future__ import annotations

import os
from dataclasses import dataclass


def dedupe_preserve_order(items: list[str]) -> list[str]:
    """De-duplicate strings while preserving order."""
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def estimate_tokens_conservative(text: str) -> int:
    """Conservative heuristic: overestimate tokens to avoid exceeding cost caps.

    Empirically, many tokenizers average ~4 chars/token for English; use 3 for safety.
    """
    chars_per_token = 3
    return max(1, (len(text) + chars_per_token - 1) // chars_per_token)


@dataclass(frozen=True)
class AnthropicPricing:
    """Token pricing (USD per 1M tokens)."""

    input_usd_per_mtok: float
    output_usd_per_mtok: float

    def cost_usd(self, *, input_tokens: int, output_tokens: int) -> float:
        """Calculate total cost for the given token counts."""
        return (input_tokens * self.input_usd_per_mtok) / 1_000_000 + (
            output_tokens * self.output_usd_per_mtok
        ) / 1_000_000


def _read_positive_float_env(name: str) -> float | None:
    """Read a positive float from an environment variable."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return None
    try:
        value = float(raw)
    except ValueError as e:
        raise ValueError(f"{name} must be a float") from e
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def default_pricing_for_model(_model: str) -> AnthropicPricing:
    """Get pricing for a model, preferring environment overrides."""
    # Prefer explicit env overrides (works across model changes without code edits).
    input_override = _read_positive_float_env("ANTHROPIC_INPUT_USD_PER_MTOK")
    output_override = _read_positive_float_env("ANTHROPIC_OUTPUT_USD_PER_MTOK")
    if input_override is not None and output_override is not None:
        return AnthropicPricing(
            input_usd_per_mtok=input_override, output_usd_per_mtok=output_override
        )

    # Defaults are for the Sonnet family (override via env if you use different pricing).
    return AnthropicPricing(input_usd_per_mtok=3.0, output_usd_per_mtok=15.0)
