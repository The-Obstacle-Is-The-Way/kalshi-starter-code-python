"""LLM provider interface for synthesis.

Phase 1: Protocol-based interface (no specific implementation required).
Future: Add Instructor or PydanticAI concrete implementations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ..schemas import AnalysisResult, MarketInfo, MarketPriceSnapshot, ResearchSummary

from ..schemas import AnalysisFactor, AnalysisResult


class SynthesisInput:
    """Input bundle for synthesis model."""

    def __init__(
        self,
        market: MarketInfo,
        snapshot: MarketPriceSnapshot,
        research: ResearchSummary | None = None,
    ):
        """Initialize synthesis input.

        Args:
            market: Market metadata
            snapshot: Current price snapshot
            research: Optional research summary from Exa agent
        """
        self.market = market
        self.snapshot = snapshot
        self.research = research


class StructuredSynthesizer(Protocol):
    """Protocol for structured synthesis models.

    Implementations should use Pydantic-aware LLM frameworks (Instructor, PydanticAI, etc.)
    to ensure schema-validated outputs.
    """

    async def synthesize(self, *, input: SynthesisInput) -> AnalysisResult:
        """Synthesize probability estimate from market and research data.

        Args:
            input: SynthesisInput bundle with market, snapshot, and optional research

        Returns:
            AnalysisResult with predicted probability and reasoning

        Raises:
            ValidationError: If LLM output fails Pydantic schema validation
            RuntimeError: If synthesis fails (e.g., API error, timeout)
        """
        ...


class MockSynthesizer:
    """Mock synthesizer for testing.

    Returns a fixed AnalysisResult that passes basic validation.
    """

    async def synthesize(self, *, input: SynthesisInput) -> AnalysisResult:
        """Return mock analysis result.

        Args:
            input: SynthesisInput bundle

        Returns:
            Mock AnalysisResult with valid schema
        """
        # Simple mock: predict market price + 5% with low confidence
        market_pct = int(input.snapshot.midpoint_prob * 100)
        predicted = min(100, max(0, market_pct + 5))

        factors = []
        sources = []

        # If research provided, extract one factor
        if input.research and input.research.factors:
            first_factor = input.research.factors[0]
            factors.append(
                AnalysisFactor(
                    description=first_factor.factor_text,
                    impact="up",
                    source_url=first_factor.source_url,
                )
            )
            sources.append(first_factor.source_url)

        return AnalysisResult(
            ticker=input.market.ticker,
            market_prob=input.snapshot.midpoint_prob,
            predicted_prob=predicted,
            confidence="low",
            reasoning=(
                f"Mock analysis for {input.market.title}. "
                f"Market is at {market_pct}%, predicting {predicted}% based on "
                f"simple +5% heuristic. This is a test stub."
            ),
            factors=factors,
            sources=sources,
            generated_at=datetime.now(UTC),
            model_id="mock-v1",
        )
