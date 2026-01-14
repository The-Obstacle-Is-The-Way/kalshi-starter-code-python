"""Shared price conversion helpers for API models."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def fixed_dollars_to_cents(dollar_str: str, *, label: str) -> int:
    """
    Convert a Kalshi fixed-point dollar string (e.g., "0.5500") into integer cents.

    This rounds half-up to the nearest cent and validates the result is within [0, 100].
    """
    try:
        cents = (Decimal(dollar_str.strip()) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    except (AttributeError, InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid {label}: {dollar_str!r}") from exc

    cents_int = int(cents)
    if cents_int < 0 or cents_int > 100:
        raise ValueError(f"{label} out of range: {dollar_str!r}")
    return cents_int
