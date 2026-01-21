"""Data models and types for liquidity analysis.

This module contains:
- LiquidityGrade enum for market classification
- LiquidityError exception for execution constraints
- Data classes for depth, slippage, weights, and analysis results
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LiquidityGrade(str, Enum):
    """Liquidity grade classification."""

    ILLIQUID = "illiquid"
    THIN = "thin"
    MODERATE = "moderate"
    LIQUID = "liquid"


class LiquidityError(RuntimeError):
    """Raised when a proposed execution exceeds liquidity constraints."""


@dataclass(frozen=True)
class DepthAnalysis:
    """Orderbook depth analysis results."""

    total_contracts: int
    weighted_score: float
    yes_side_depth: int
    no_side_depth: int
    imbalance_ratio: float


@dataclass(frozen=True)
class SlippageEstimate:
    """Slippage estimation results for a hypothetical execution."""

    best_price: int
    avg_fill_price: float
    worst_price: int
    slippage_cents: float
    slippage_pct: float
    fillable_quantity: int
    remaining_unfilled: int
    levels_crossed: int


@dataclass(frozen=True)
class LiquidityWeights:
    """Weights for composite liquidity score."""

    spread: float = 0.30
    depth: float = 0.30
    volume: float = 0.20
    open_interest: float = 0.20

    def __post_init__(self) -> None:
        total = self.spread + self.depth + self.volume + self.open_interest
        if abs(total - 1.0) >= 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


@dataclass(frozen=True)
class LiquidityAnalysis:
    """Composite liquidity analysis for a market."""

    score: int
    grade: LiquidityGrade
    components: dict[str, float]
    depth: DepthAnalysis
    max_safe_size_yes: int
    max_safe_size_no: int
    warnings: list[str]


@dataclass(frozen=True)
class ExecutionWindow:
    """Recommended execution timing (heuristic)."""

    optimal_hours_utc: list[int]
    avoid_hours_utc: list[int]
    reasoning: str
