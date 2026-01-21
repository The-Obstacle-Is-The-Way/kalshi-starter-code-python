"""Mock synthesizer for testing."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ...schemas import AnalysisFactor, AnalysisResult

if TYPE_CHECKING:
    from ._schemas import SynthesisInput


class MockSynthesizer:
    """Mock synthesizer for testing.

    Returns a fixed AnalysisResult that passes basic validation.
    """

    def __init__(self) -> None:
        self._last_cost_usd = 0.0

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

        factors: list[AnalysisFactor] = []
        sources: list[str] = []

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

    def get_last_call_cost_usd(self) -> float:
        """Return the estimated USD cost of the most recent call."""
        return self._last_cost_usd
