"""Claude (Anthropic) synthesizer implementation."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Protocol, cast

from ...schemas import AnalysisResult, ResearchSummary
from ._pricing import (
    AnthropicPricing,
    dedupe_preserve_order,
    default_pricing_for_model,
    estimate_tokens_conservative,
)
from ._prompts import ANALYSIS_PROMPT_TEMPLATE, SYSTEM_PROMPT
from ._schemas import AnalysisToolInput, ConfidenceLevel, SynthesisInput

_AsyncAnthropic: object | None
try:
    from anthropic import AsyncAnthropic as _AsyncAnthropicImpl
except ImportError:  # pragma: no cover
    _AsyncAnthropic = None
else:  # pragma: no cover
    _AsyncAnthropic = _AsyncAnthropicImpl


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

        self._pricing: AnthropicPricing = default_pricing_for_model(model)

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
        """Synthesize probability estimate from market and research data."""
        prompt = self._build_prompt(input)

        tool_schema: dict[str, object] = AnalysisToolInput.model_json_schema()
        tools: list[dict[str, object]] = [
            {
                "name": "submit_analysis",
                "description": "Submit probability analysis for this market",
                "input_schema": tool_schema,
            }
        ]

        max_tokens = self._compute_max_tokens(prompt, tools)

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
        parsed = AnalysisToolInput.model_validate(tool_input)

        self._track_usage(response)

        return self._build_result(input, parsed)

    def get_last_call_cost_usd(self) -> float:
        """Return the estimated USD cost of the most recent call."""
        return self._last_cost_usd

    def _compute_max_tokens(self, prompt: str, tools: list[dict[str, object]]) -> int:
        """Compute max tokens, capped by budget if specified."""
        max_tokens = self._max_tokens
        if self._max_cost_usd is None:
            return max_tokens

        # Conservative cap using estimated input + output token pricing.
        request_text = (
            SYSTEM_PROMPT
            + "\n"
            + prompt
            + "\n"
            + json.dumps(tools, sort_keys=True, separators=(",", ":"), default=str)
        )
        estimated_input_tokens = estimate_tokens_conservative(request_text)
        input_usd_per_token = self._pricing.input_usd_per_mtok / 1_000_000
        output_usd_per_token = self._pricing.output_usd_per_mtok / 1_000_000
        estimated_input_cost = estimated_input_tokens * input_usd_per_token
        remaining_budget = max(0.0, self._max_cost_usd - estimated_input_cost)
        budget_cap = int(remaining_budget / output_usd_per_token)
        return max(1, min(max_tokens, budget_cap))

    def _build_prompt(self, input: SynthesisInput) -> str:
        """Build the analysis prompt for the LLM."""
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
        """Format research factors for the prompt."""
        if research is None or not research.factors:
            return "No research factors provided."

        lines: list[str] = []
        for factor in research.factors[:12]:
            line = f"- {factor.factor_text} (source: {factor.source_url})"
            if factor.highlight:
                line += f"\n  Quote: {factor.highlight}"
            lines.append(line)
        return "\n".join(lines)

    def _build_result(self, input: SynthesisInput, parsed: AnalysisToolInput) -> AnalysisResult:
        """Build AnalysisResult from parsed tool input."""
        factor_urls = dedupe_preserve_order([factor.source_url for factor in parsed.factors])
        factor_url_set = set(factor_urls)

        sources = dedupe_preserve_order(parsed.sources)
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

    @staticmethod
    def _extract_tool_input(response: object, *, tool_name: str) -> dict[str, object]:
        """Extract tool input from Anthropic response."""
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
        """Track API usage and update last call cost."""
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)

        if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
            # Usage is missing or unexpected; keep cost at 0 but still return a valid result.
            self._last_cost_usd = 0.0
            return

        self._last_cost_usd = self._pricing.cost_usd(
            input_tokens=input_tokens, output_tokens=output_tokens
        )
