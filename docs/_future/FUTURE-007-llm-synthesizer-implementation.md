# FUTURE-007: LLM Synthesizer Implementation (Phase 2)

**Status:** Backlog
**Priority:** P1 (High - Required for agent system value)
**Created:** 2026-01-18
**Depends On:** Agent analysis workflow (`kalshi agent analyze`) and structured schemas (`kalshi_research.agent.schemas`)

---

## Summary

Implement a real LLM-based synthesizer to replace `MockSynthesizer` in the agent analysis workflow. Without this, `kalshi agent analyze` returns meaningless "+5% from market" predictions.

## Current State

The `StructuredSynthesizer` protocol is defined in `src/kalshi_research/agent/providers/llm.py`:

```python
class StructuredSynthesizer(Protocol):
    async def synthesize(self, *, input: SynthesisInput) -> AnalysisResult:
        """Synthesize probability estimate from market and research data."""
        ...
```

`MockSynthesizer` implements this with trivial logic. The CLI still uses the mock synthesizer
unconditionally (Phase 1), but:

- `kalshi agent analyze --human` prints an explicit warning that results are placeholders.
- JSON output is emitted via `typer.echo(...)` to keep stdout valid JSON (no Rich wrapping).
- Integration coverage exists for the CLI entrypoints with mocked APIs:
  `tests/integration/cli/test_agent_commands.py`

## Goals

1. **Implement at least one real LLM backend** (OpenAI, Anthropic, or local)
2. **Ensure structured output validation** via Pydantic
3. **Make backend configurable** via environment variable
4. **Add cost tracking** for LLM calls (Phase 2 budget enforcement)
5. **Warn users when mock is active**

## Non-Goals

- Fine-tuning models
- Multi-agent debate/consensus
- Real-time streaming responses

## Design Options

### Option A: Instructor + OpenAI (Recommended)

```python
import instructor
from openai import AsyncOpenAI

class InstructorSynthesizer:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = instructor.from_openai(AsyncOpenAI())
        self.model = model

    async def synthesize(self, *, input: SynthesisInput) -> AnalysisResult:
        return await self.client.chat.completions.create(
            model=self.model,
            response_model=AnalysisResult,
            messages=[{
                "role": "user",
                "content": self._build_prompt(input)
            }],
        )

    def _build_prompt(self, input: SynthesisInput) -> str:
        # Format market info, price, and research factors into prompt
        ...
```

**Pros:** Battle-tested, handles retries and validation
**Cons:** OpenAI dependency, cost per call

### Option B: Anthropic with tool_use

```python
from anthropic import AsyncAnthropic

class ClaudeSynthesizer:
    async def synthesize(self, *, input: SynthesisInput) -> AnalysisResult:
        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            tools=[{
                "name": "submit_analysis",
                "description": "Submit probability analysis",
                "input_schema": AnalysisResult.model_json_schema()
            }],
            messages=[...]
        )
        # Extract tool call and validate
        ...
```

**Pros:** Same provider as Claude Code, consistent
**Cons:** More manual parsing

### Option C: Local LLM (Ollama)

```python
import ollama

class OllamaSynthesizer:
    async def synthesize(self, *, input: SynthesisInput) -> AnalysisResult:
        response = await ollama.chat(
            model="llama3.1",
            messages=[...],
            format="json"
        )
        return AnalysisResult.model_validate_json(response["message"]["content"])
```

**Pros:** Free, local, private
**Cons:** Less reliable structured output

## Implementation Plan

### Phase 1: OpenAI/Instructor

1. Add `instructor` to dependencies
2. Implement `InstructorSynthesizer`
3. Add `KALSHI_SYNTHESIZER_BACKEND` env var (mock/openai)
4. Add prompt template with market context + research factors
5. Add cost tracking (input/output tokens)
6. Update CLI to select synthesizer based on env

### Phase 2: Multi-Backend Support

1. Add Claude synthesizer
2. Add Ollama synthesizer
3. Factory function to instantiate based on config

## CLI Changes

```python
# Before
synthesizer = MockSynthesizer()

# After
backend = os.getenv("KALSHI_SYNTHESIZER_BACKEND", "mock")
if backend == "mock":
    console.print("[yellow]Warning: Using MockSynthesizer. Set KALSHI_SYNTHESIZER_BACKEND=openai for real analysis.[/yellow]")
    synthesizer = MockSynthesizer()
elif backend == "openai":
    synthesizer = InstructorSynthesizer()
elif backend == "anthropic":
    synthesizer = ClaudeSynthesizer()
else:
    raise ValueError(f"Unknown synthesizer backend: {backend}")
```

## Acceptance Criteria

- [ ] At least one real LLM synthesizer implemented
- [ ] CLI warns when using mock
- [ ] Environment variable controls backend selection
- [ ] Cost tracking for LLM calls
- [ ] Integration test with real LLM (opt-in via env var)
- [ ] Prompt template produces reasonable predictions

## Dependencies

- `instructor>=1.0.0` (for Option A)
- `openai>=1.0.0` (for Option A)
- `anthropic>=0.20.0` (for Option B)
- `ollama>=0.1.0` (for Option C)

## Files to Create/Modify

- `src/kalshi_research/agent/providers/llm.py` - Add new synthesizers
- `src/kalshi_research/cli/agent.py` - Backend selection
- `pyproject.toml` - Optional dependencies
- `tests/unit/agent/test_llm_synthesizer.py` - New tests

## Notes

This is blocked on deciding which LLM provider to prioritize. Instructor + OpenAI is the most mature option for structured output.
