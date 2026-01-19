"""LLM provider interface for synthesis.

Phase 1: Schema-validated, backend-selectable synthesizers.

- `MockSynthesizer` stays available for tests/CI and zero-dependency runs.
- `ClaudeSynthesizer` (Anthropic) provides a real, structured-output backend.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from ..schemas import AnalysisResult, MarketInfo, MarketPriceSnapshot, ResearchSummary

from ..schemas import AnalysisFactor, AnalysisResult

_AsyncAnthropic: object | None
try:
    from anthropic import AsyncAnthropic as _AsyncAnthropicImpl
except ImportError:  # pragma: no cover
    _AsyncAnthropic = None
else:  # pragma: no cover
    _AsyncAnthropic = _AsyncAnthropicImpl

ConfidenceLevel = Literal["low", "medium", "high"]


class _AnalysisToolInput(BaseModel):
    """LLM tool output schema (excludes fields we already know)."""

    model_config = ConfigDict(frozen=True)

    predicted_prob: int = Field(ge=0, le=100, description="Predicted probability (0..100)")
    confidence: ConfidenceLevel = Field(description="Confidence level")
    reasoning: str = Field(description="Concise reasoning with citations")
    factors: list[AnalysisFactor] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list, description="Unique source URLs cited")


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _estimate_tokens_conservative(text: str) -> int:
    # Conservative heuristic: overestimate tokens to avoid exceeding cost caps.
    # Empirically, many tokenizers average ~4 chars/token for English; use 3 for safety.
    chars_per_token = 3
    return max(1, (len(text) + chars_per_token - 1) // chars_per_token)


@dataclass(frozen=True)
class _AnthropicPricing:
    """Token pricing (USD per 1M tokens)."""

    input_usd_per_mtok: float
    output_usd_per_mtok: float

    def cost_usd(self, *, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * self.input_usd_per_mtok) / 1_000_000 + (
            output_tokens * self.output_usd_per_mtok
        ) / 1_000_000


def _read_positive_float_env(name: str) -> float | None:
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


def _default_pricing_for_model(_model: str) -> _AnthropicPricing:
    # Prefer explicit env overrides (works across model changes without code edits).
    input_override = _read_positive_float_env("ANTHROPIC_INPUT_USD_PER_MTOK")
    output_override = _read_positive_float_env("ANTHROPIC_OUTPUT_USD_PER_MTOK")
    if input_override is not None and output_override is not None:
        return _AnthropicPricing(
            input_usd_per_mtok=input_override, output_usd_per_mtok=output_override
        )

    # Defaults are for the Sonnet family (override via env if you use different pricing).
    return _AnthropicPricing(input_usd_per_mtok=3.0, output_usd_per_mtok=15.0)


SYSTEM_PROMPT = """You are a prediction market analyst specializing in probability estimation.

Given market information and research, estimate the probability of the YES outcome.

Key principles:
1. Be calibrated: your 70% predictions should resolve YES ~70% of the time
2. Cite evidence. If you cannot cite >=2 sources, use confidence="low"
3. Consider base rates and reference classes
4. Markets can be wrong; edge comes from research + calibration

You MUST respond using the submit_analysis tool with valid structured output."""

ANALYSIS_PROMPT_TEMPLATE = """## Market: {ticker}
**{title}**
{subtitle}

### Current Market State
- Market closes: {close_time}
- Current implied probability: {market_prob_pct}%
- Yes bid/ask: {yes_bid}¢ / {yes_ask}¢ (spread: {spread}¢)
- 24h volume: {volume_24h} contracts

### Research Factors (with citations)
{factors}

---

Requirements:
- predicted_prob: integer 0..100
- confidence: low | medium | high
- reasoning: 50..2000 chars, cite evidence explicitly
- factors: each factor must include a source_url; impact is up/down/unclear
- sources: unique list of URLs; must match the factor source_url values

Guidance:
- If you have fewer than 2 credible sources, choose confidence="low".
- For confidence="medium", include at least 2 sources.
- For confidence="high", include at least 3 sources.
"""


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

    def get_total_cost_usd(self) -> float:
        """Return the cumulative estimated USD cost for this synthesizer instance."""
        ...

    def get_total_tokens(self) -> int:
        """Return cumulative tokens (input + output) for this synthesizer instance."""
        ...


class _AnthropicMessages(Protocol):
    async def create(self, **kwargs: object) -> object: ...


class _AnthropicClient(Protocol):
    messages: _AnthropicMessages


class _AsyncAnthropicCtor(Protocol):
    def __call__(self, *, api_key: str) -> _AnthropicClient: ...


class ClaudeSynthesizer:
    """LLM synthesizer using Anthropic Claude with tool-based structured outputs."""

    def __init__(
        self,
        *,
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = 1024,
        max_cost_usd: float | None = None,
        api_key: str | None = None,
        client: _AnthropicClient | None = None,
    ) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if max_cost_usd is not None and max_cost_usd <= 0:
            raise ValueError("max_cost_usd must be positive when provided")

        self.model = model
        self._max_tokens = max_tokens
        self._max_cost_usd = max_cost_usd

        self._pricing = _default_pricing_for_model(model)

        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_cost_usd = 0.0
        self._last_cost_usd = 0.0

        if client is not None:
            self._client: _AnthropicClient = client
            return

        resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required for the 'anthropic' synthesizer backend. "
                "Set ANTHROPIC_API_KEY or use KALSHI_SYNTHESIZER_BACKEND=mock."
            )

        if _AsyncAnthropic is None:
            raise ValueError(
                "Anthropic synthesizer backend requested but dependency is not installed. "
                "Install with `uv sync --extra llm`."
            )

        ctor = cast("_AsyncAnthropicCtor", _AsyncAnthropic)
        self._client = ctor(api_key=resolved_key)

    async def synthesize(self, *, input: SynthesisInput) -> AnalysisResult:
        prompt = self._build_prompt(input)

        tool_schema: dict[str, object] = _AnalysisToolInput.model_json_schema()
        tools: list[dict[str, object]] = [
            {
                "name": "submit_analysis",
                "description": "Submit probability analysis for this market",
                "input_schema": tool_schema,
            }
        ]

        max_tokens = self._max_tokens
        if self._max_cost_usd is not None:
            # Conservative cap using estimated input + output token pricing.
            request_text = (
                SYSTEM_PROMPT
                + "\n"
                + prompt
                + "\n"
                + json.dumps(tools, sort_keys=True, separators=(",", ":"), default=str)
            )
            estimated_input_tokens = _estimate_tokens_conservative(request_text)
            input_usd_per_token = self._pricing.input_usd_per_mtok / 1_000_000
            output_usd_per_token = self._pricing.output_usd_per_mtok / 1_000_000
            estimated_input_cost = estimated_input_tokens * input_usd_per_token
            remaining_budget = max(0.0, self._max_cost_usd - estimated_input_cost)
            budget_cap = int(remaining_budget / output_usd_per_token)
            max_tokens = max(1, min(max_tokens, budget_cap))

        response = await self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=0.0,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            tools=tools,
            tool_choice={"type": "tool", "name": "submit_analysis"},
        )

        tool_input = self._extract_tool_input(response, tool_name="submit_analysis")
        parsed = _AnalysisToolInput.model_validate(tool_input)

        self._track_usage(response)

        factor_urls = _dedupe_preserve_order([factor.source_url for factor in parsed.factors])
        factor_url_set = set(factor_urls)

        sources = _dedupe_preserve_order(parsed.sources)
        if sources:
            sources = [url for url in sources if url in factor_url_set]
        if not sources:
            sources = factor_urls

        confidence: ConfidenceLevel = parsed.confidence
        if confidence == "high" and len(sources) < 3:
            confidence = "medium" if len(sources) >= 2 else "low"
        if confidence == "medium" and len(sources) < 2:
            confidence = "low"

        return AnalysisResult(
            ticker=input.market.ticker,
            market_prob=input.snapshot.midpoint_prob,
            predicted_prob=parsed.predicted_prob,
            confidence=confidence,
            reasoning=parsed.reasoning,
            factors=parsed.factors,
            sources=sources,
            generated_at=datetime.now(UTC),
            model_id=self.model,
        )

    def get_last_call_cost_usd(self) -> float:
        return self._last_cost_usd

    def get_total_cost_usd(self) -> float:
        return self._total_cost_usd

    def get_total_tokens(self) -> int:
        return self._total_input_tokens + self._total_output_tokens

    def _build_prompt(self, input: SynthesisInput) -> str:
        factors_text = self._format_research_factors(input.research)
        subtitle = input.market.subtitle or ""
        market_prob_pct = int(input.snapshot.midpoint_prob * 100)

        return ANALYSIS_PROMPT_TEMPLATE.format(
            ticker=input.market.ticker,
            title=input.market.title,
            subtitle=subtitle,
            close_time=input.market.close_time.isoformat(),
            market_prob_pct=market_prob_pct,
            yes_bid=input.snapshot.yes_bid_cents,
            yes_ask=input.snapshot.yes_ask_cents,
            spread=input.snapshot.spread_cents,
            volume_24h=input.snapshot.volume_24h,
            factors=factors_text,
        )

    def _format_research_factors(self, research: ResearchSummary | None) -> str:
        if research is None or not research.factors:
            return "No research factors provided."

        lines: list[str] = []
        for factor in research.factors[:12]:
            line = f"- {factor.factor_text} (source: {factor.source_url})"
            if factor.highlight:
                line += f"\n  Quote: {factor.highlight}"
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _extract_tool_input(response: object, *, tool_name: str) -> dict[str, object]:
        content = getattr(response, "content", None)
        if not isinstance(content, list):
            raise RuntimeError("Anthropic response content is not a list")

        for block in content:
            block_type = getattr(block, "type", None)
            name = getattr(block, "name", None)
            if block_type != "tool_use" or name != tool_name:
                continue

            tool_input = getattr(block, "input", None)
            if not isinstance(tool_input, dict):
                raise RuntimeError("Anthropic tool_use block input is not a dict")
            return tool_input

        raise RuntimeError(f"Anthropic response did not include tool_use for {tool_name!r}")

    def _track_usage(self, response: object) -> None:
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)

        if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
            # Usage is missing or unexpected; keep cost at 0 but still return a valid result.
            self._last_cost_usd = 0.0
            return

        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens

        cost = self._pricing.cost_usd(input_tokens=input_tokens, output_tokens=output_tokens)
        self._last_cost_usd = cost
        self._total_cost_usd += cost


class MockSynthesizer:
    """Mock synthesizer for testing.

    Returns a fixed AnalysisResult that passes basic validation.
    """

    def __init__(self) -> None:
        self._total_cost_usd = 0.0
        self._last_cost_usd = 0.0
        self._total_tokens = 0

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

    def get_last_call_cost_usd(self) -> float:
        return self._last_cost_usd

    def get_total_cost_usd(self) -> float:
        return self._total_cost_usd

    def get_total_tokens(self) -> int:
        return self._total_tokens


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
