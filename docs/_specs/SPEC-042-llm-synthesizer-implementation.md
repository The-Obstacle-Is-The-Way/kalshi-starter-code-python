# SPEC-042: LLM Synthesizer Implementation

**Status:** Active
**Priority:** P1 (High - Required for agent system value)
**Created:** 2026-01-18
**Promoted From:** FUTURE-007
**Owner:** Solo
**Effort:** ~2-3 days (Phase 1)

---

## Summary

Implement a real LLM-based synthesizer to replace `MockSynthesizer` in the agent analysis workflow. Without this, `kalshi agent analyze` returns meaningless "+5% from market" predictions.

This spec addresses [DEBT-037](../_debt/DEBT-037-mock-synthesizer-production-gap.md) which is blocking the entire agent system value proposition.

**Model Choice:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) - pinned model ID for reproducibility (confirmed in Anthropic model docs).

---

## Goals

1. **Implement Claude Sonnet 4.5 synthesizer** using Anthropic's native structured outputs
2. **Ensure structured output validation** via Pydantic + Anthropic beta header
3. **Make backend configurable** via environment variable (default: `anthropic`)
4. **Add cost tracking** for LLM calls
5. **Preserve mock for testing** - Mock stays available for CI/testing

---

## Non-Goals

- Fine-tuning models
- Multi-agent debate/consensus
- Real-time streaming responses
- Multi-provider support in Phase 1 (stick with Anthropic until stable)

---

## SSOT (What's True Today)

1. **Protocol defined**: `StructuredSynthesizer` in `src/kalshi_research/agent/providers/llm.py`
2. **Mock implementation**: `MockSynthesizer` returns `market_price + 5%`
3. **CLI hardcoded**: `src/kalshi_research/cli/agent.py:262-268` always uses mock
4. **Schemas exist**: `SynthesisInput`, `AnalysisResult` in `src/kalshi_research/agent/schemas.py`
5. **Warning exists** (human mode only): Lines 263-267 print warning for `--human` output

---

## Model Selection Rationale

### Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)

- **Pinned model ID:** Use a dated model ID for reproducibility (`claude-sonnet-4-5-20250929`) and optionally allow an alias via configuration.
- **Structured output:** Use Anthropic tool use + schema validation (Pydantic) for deterministic machine-readable outputs.
- **Cost tracking:** Track token usage and compute USD cost using pricing from Anthropic vendor docs at implementation time (do not hardcode numbers in the spec).

---

## Architecture

### Synthesizer Selection

```python
# src/kalshi_research/agent/providers/llm.py

def get_synthesizer(backend: str | None = None) -> StructuredSynthesizer:
    """Factory function to create synthesizer based on config."""
    backend = backend or os.getenv("KALSHI_SYNTHESIZER_BACKEND", "anthropic")

    if backend == "mock":
        return MockSynthesizer()
    elif backend == "anthropic":
        return ClaudeSynthesizer()
    else:
        raise ValueError(f"Unknown synthesizer backend: {backend}")
```

### ClaudeSynthesizer (Phase 1 - Primary)

```python
from anthropic import AsyncAnthropic

# Frontier model - Claude Sonnet 4.5
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

# Pricing constants (USD per 1M tokens). Fill from vendor docs at implementation time.
INPUT_USD_PER_M: float = ...
OUTPUT_USD_PER_M: float = ...

class ClaudeSynthesizer:
    """LLM synthesizer using Claude Sonnet 4.5 with native structured outputs."""

    def __init__(self, model: str = CLAUDE_MODEL):
        self.client = AsyncAnthropic()
        self.model = model
        self._total_tokens = 0
        self._total_cost_usd = 0.0

    async def synthesize(self, *, input: SynthesisInput) -> AnalysisResult:
        """Synthesize probability estimate from market and research data."""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            # If required for structured outputs, set the beta header per Anthropic docs.
            # extra_headers={"anthropic-beta": "structured-outputs-YYYY-MM-DD"},
            tools=[{
                "name": "submit_analysis",
                "description": "Submit your probability analysis for this market",
                "input_schema": AnalysisResult.model_json_schema()
            }],
            tool_choice={"type": "tool", "name": "submit_analysis"},
            messages=[{
                "role": "user",
                "content": self._build_prompt(input)
            }],
            system=SYSTEM_PROMPT,
        )

        # Extract tool call result
        tool_use = next(
            block for block in response.content
            if block.type == "tool_use"
        )

        # Track costs
        self._track_usage(response)

        # Validate and return
        return AnalysisResult.model_validate(tool_use.input)

    def _build_prompt(self, input: SynthesisInput) -> str:
        """Build prompt from market info, price snapshot, and research."""
        research_factors = input.research.factors if input.research else []
        return ANALYSIS_PROMPT_TEMPLATE.format(
            ticker=input.market.ticker,
            title=input.market.title,
            subtitle=input.market.subtitle,
            close_time=input.market.close_time.isoformat(),
            current_prob=f"{input.snapshot.midpoint_prob:.1%}",
            yes_bid=input.snapshot.yes_bid_cents,
            yes_ask=input.snapshot.yes_ask_cents,
            spread=input.snapshot.spread_cents,
            volume_24h=input.snapshot.volume_24h,
            factors=self._format_research_factors(research_factors),
        )

    def _track_usage(self, response) -> None:
        """Track token usage and costs."""
        self._total_tokens += response.usage.input_tokens + response.usage.output_tokens
        # Compute cost using pricing constants sourced from vendor docs at implementation time.
        self._total_cost_usd += (
            response.usage.input_tokens * INPUT_USD_PER_M / 1_000_000 +
            response.usage.output_tokens * OUTPUT_USD_PER_M / 1_000_000
        )

    def _format_research_factors(self, factors: list[Factor]) -> str:
        """Format ResearchSummary factors for prompt."""
        if not factors:
            return "No factors identified"
        return "\n".join(
            f"- {f.factor_text} (source: {f.source_url})"
            for f in factors
        )
```

### Prompt Template

```python
SYSTEM_PROMPT = """You are a prediction market analyst specializing in probability estimation.
Given market information and research, estimate the probability of the YES outcome.

Key principles:
1. Be calibrated - your 70% predictions should resolve YES ~70% of the time
2. Use research evidence to inform estimates, but acknowledge uncertainty
3. Consider base rates and reference classes
4. Be aware that markets can be wrong - your edge comes from research
5. Express genuine uncertainty through your confidence level

You will use the submit_analysis tool to provide your structured analysis."""

ANALYSIS_PROMPT_TEMPLATE = """
## Market: {ticker}
**{title}**
{subtitle}

### Current Market State
- Market closes: {close_time}
- Current implied probability: {current_prob}
- Yes bid/ask: {yes_bid}¢ / {yes_ask}¢ (spread: {spread}¢)
- 24h volume: {volume_24h} contracts

### Research Summary
### Research Factors (structured)
{factors}

---

Analyze this market and provide:
1. Your probability estimate (0-100) for YES
2. Your confidence level (low/medium/high) based on research quality
3. Clear reasoning citing specific evidence
4. Key sources that informed your estimate

Consider:
- What does the research suggest vs market price?
- What uncertainties or information gaps remain?
- Are there base rates or reference classes to consider?
"""
```

---

## CLI Changes

```python
# src/kalshi_research/cli/agent.py

from kalshi_research.agent.providers.llm import get_synthesizer, MockSynthesizer

# In analyze command:
backend = os.getenv("KALSHI_SYNTHESIZER_BACKEND", "anthropic")
synthesizer = get_synthesizer(backend)

# Warn if mock
if isinstance(synthesizer, MockSynthesizer):
    if human or not output_json:
        console.print(
            "[yellow]Warning:[/yellow] Using MockSynthesizer. "
            "Set KALSHI_SYNTHESIZER_BACKEND=anthropic for real analysis."
        )
```

---

## Dependencies

Add to `pyproject.toml` as optional extras:

```toml
[project.optional-dependencies]
llm = [
    "anthropic>=0.40.0",  # For Claude Sonnet 4.5 + structured outputs
]
```

Installation:
```bash
uv sync --extra llm  # For Claude synthesizer
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KALSHI_SYNTHESIZER_BACKEND` | `anthropic` | `mock` or `anthropic` |
| `ANTHROPIC_API_KEY` | - | Required for `anthropic` backend |

---

## Implementation Plan

### Phase 1: Claude Sonnet 4.5 (This Spec)

1. Add `anthropic>=0.40.0` to optional dependencies
2. Implement `ClaudeSynthesizer` class with structured outputs
3. Add `get_synthesizer()` factory function
4. Add `KALSHI_SYNTHESIZER_BACKEND` env var support (default: `anthropic`)
5. Create prompt template optimized for calibrated forecasting
6. Add cost tracking (input/output tokens)
7. Update CLI to use factory function
8. Add unit tests with mocked Anthropic responses

### Phase 2: Calibration Layer (Future)

1. Track historical predictions vs outcomes
2. Apply statistical calibration adjustment
3. Store predictions in DB for backtesting

---

## Testing Strategy

### Unit Tests (No API Calls)

```python
# tests/unit/agent/test_llm_synthesizer.py

def test_claude_synthesizer_builds_prompt():
    """Prompt template includes all required fields."""
    synth = ClaudeSynthesizer()
    prompt = synth._build_prompt(mock_input)
    assert "TICKER" in prompt
    assert "Current implied probability" in prompt

@respx.mock
async def test_claude_synthesizer_returns_valid_result():
    """Mocked Anthropic returns valid AnalysisResult."""
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(200, json={
            "content": [{
                "type": "tool_use",
                "name": "submit_analysis",
                "input": {
                    "ticker": "TEST",
                    "predicted_prob": 65,
                    "confidence": "medium",
                    "reasoning": "Test reasoning",
                    # ... other fields
                }
            }],
            "usage": {"input_tokens": 100, "output_tokens": 200}
        })
    )
    synth = ClaudeSynthesizer()
    result = await synth.synthesize(input=mock_input)
    assert 0 <= result.predicted_prob <= 100

def test_get_synthesizer_factory():
    """Factory returns correct synthesizer type."""
    assert isinstance(get_synthesizer("mock"), MockSynthesizer)
```

### Integration Tests (Opt-In)

```python
# tests/integration/agent/test_llm_real.py

@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="No API key")
async def test_real_claude_synthesis():
    """Real Claude call returns valid result."""
    synth = ClaudeSynthesizer()
    result = await synth.synthesize(input=real_input)
    assert result.reasoning  # Non-empty reasoning
    assert 0 <= result.predicted_prob <= 100
```

---

## Acceptance Criteria

- [ ] `ClaudeSynthesizer` implemented using `claude-sonnet-4-5-20250929`
- [ ] Native structured outputs enabled per Anthropic vendor docs (beta header if required)
- [ ] `get_synthesizer()` factory function works
- [ ] `KALSHI_SYNTHESIZER_BACKEND` env var controls backend (default: `anthropic`)
- [ ] CLI uses factory, warns when mock is active
- [ ] Prompt template optimized for calibrated probability estimation
- [ ] Cost tracking for LLM calls (tokens used, USD spent)
- [ ] Unit tests with mocked API (no real calls in CI)
- [ ] Integration test with real API (opt-in via env var)
- [ ] Documentation updated with env var instructions

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/kalshi_research/agent/providers/llm.py` | Add `ClaudeSynthesizer`, `get_synthesizer()`, prompt templates |
| `src/kalshi_research/cli/agent.py` | Use factory function, update warning logic |
| `pyproject.toml` | Add `[llm]` optional dependencies |
| `tests/unit/agent/test_llm_synthesizer.py` | New unit tests |
| `tests/integration/agent/test_llm_real.py` | New integration tests (opt-in) |
| `.env.example` | Add `KALSHI_SYNTHESIZER_BACKEND` |

---

## References

- [DEBT-037: MockSynthesizer in Production Path](../_debt/DEBT-037-mock-synthesizer-production-gap.md)
- [SPEC-032: Agent System Orchestration](SPEC-032-agent-system-orchestration.md)
- [SPEC-033: Exa Research Agent](SPEC-033-exa-research-agent.md)
- [Claude Models Overview (model IDs)](https://platform.claude.com/docs/en/about-claude/models/overview)
- [Anthropic Docs: Structured Outputs](https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs)
- [Anthropic Docs: Pricing](https://docs.anthropic.com/en/docs/about-claude/pricing)
