"""Schema types for LLM synthesis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from ...schemas import AnalysisFactor

if TYPE_CHECKING:
    from ...schemas import AnalysisResult, MarketInfo, MarketPriceSnapshot, ResearchSummary

ConfidenceLevel = Literal["low", "medium", "high"]


class AnalysisToolInput(BaseModel):
    """LLM tool output schema (excludes fields we already know)."""

    model_config = ConfigDict(frozen=True)

    predicted_prob: int = Field(ge=0, le=100, description="Predicted probability (0..100)")
    confidence: ConfidenceLevel = Field(description="Confidence level")
    reasoning: str = Field(description="Concise reasoning with citations")
    factors: list[AnalysisFactor] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list, description="Unique source URLs cited")


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

    def get_last_call_cost_usd(self) -> float:
        """Return the estimated USD cost of the most recent call."""
        ...
