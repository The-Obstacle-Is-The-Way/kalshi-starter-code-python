from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kalshi_research.agent.providers.llm import (
    ClaudeSynthesizer,
    MockSynthesizer,
    SynthesisInput,
    get_synthesizer,
)
from kalshi_research.agent.schemas import (
    AnalysisFactor,
    Factor,
    MarketInfo,
    MarketPriceSnapshot,
    ResearchSummary,
)


class _FakeUsage:
    def __init__(self, *, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _FakeToolUse:
    def __init__(self, *, name: str, input: dict[str, object]) -> None:
        self.type = "tool_use"
        self.name = name
        self.input = input


class _FakeResponse:
    def __init__(self, *, tool_input: dict[str, object], usage: _FakeUsage) -> None:
        self.content = [_FakeToolUse(name="submit_analysis", input=tool_input)]
        self.usage = usage


class _FakeMessages:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.last_create_kwargs: dict[str, object] | None = None

    async def create(self, **kwargs: object) -> _FakeResponse:
        self.last_create_kwargs = dict(kwargs)
        return self._response


class _FakeAnthropicClient:
    def __init__(self, messages: _FakeMessages) -> None:
        self.messages = messages


def _make_input(*, with_research: bool = True) -> SynthesisInput:
    now = datetime.now(UTC)
    market = MarketInfo(
        ticker="TEST-24DEC31",
        event_ticker="EVT",
        series_ticker=None,
        title="Will a thing happen?",
        subtitle="A subtitle",
        status="open",
        open_time=now,
        close_time=now,
        expiration_time=now,
        settlement_ts=None,
    )
    snapshot = MarketPriceSnapshot(
        yes_bid_cents=45,
        yes_ask_cents=47,
        no_bid_cents=53,
        no_ask_cents=55,
        last_price_cents=None,
        volume_24h=1234,
        open_interest=567,
        midpoint_prob=0.46,
        spread_cents=2,
        captured_at=now,
    )
    research = None
    if with_research:
        research = ResearchSummary(
            ticker=market.ticker,
            title=market.title,
            mode="fast",
            factors=[
                Factor(
                    factor_text="Relevant news suggests probability is higher.",
                    source_url="https://example.com/a",
                    confidence="high",
                )
            ],
            queries_used=["test query"],
            total_sources_found=1,
            total_cost_usd=0.01,
            budget_usd=0.05,
            budget_exhausted=False,
            steps_executed=[],
        )
    return SynthesisInput(market=market, snapshot=snapshot, research=research)


def test_get_synthesizer_returns_mock() -> None:
    synth = get_synthesizer("mock")
    assert isinstance(synth, MockSynthesizer)


def test_get_synthesizer_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError, match="Unknown synthesizer backend"):
        get_synthesizer("nope")


def test_get_synthesizer_anthropic_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        get_synthesizer("anthropic")


def test_claude_synthesizer_builds_prompt_includes_fields() -> None:
    dummy_messages = _FakeMessages(
        _FakeResponse(
            tool_input={
                "predicted_prob": 60,
                "confidence": "low",
                "reasoning": "x" * 60,
                "factors": [],
                "sources": [],
            },
            usage=_FakeUsage(input_tokens=1, output_tokens=1),
        )
    )
    synth = ClaudeSynthesizer(client=_FakeAnthropicClient(dummy_messages))
    prompt = synth._build_prompt(_make_input())
    assert "## Market: TEST-24DEC31" in prompt
    assert "Current implied probability" in prompt
    assert "Research Factors" in prompt


@pytest.mark.asyncio
async def test_claude_synthesizer_synthesizes_valid_result_and_tracks_cost() -> None:
    tool_input: dict[str, object] = {
        "predicted_prob": 65,
        "confidence": "medium",
        "reasoning": "This is a test reasoning string with enough length to pass verification.",
        "factors": [
            AnalysisFactor(
                description="Evidence suggests upward drift.",
                impact="up",
                source_url="https://example.com/a",
            )
        ],
        "sources": ["https://example.com/a", "https://example.com/a"],
    }
    usage = _FakeUsage(input_tokens=100, output_tokens=200)
    response = _FakeResponse(tool_input=tool_input, usage=usage)
    messages = _FakeMessages(response)
    synth = ClaudeSynthesizer(client=_FakeAnthropicClient(messages))

    result = await synth.synthesize(input=_make_input())

    assert result.ticker == "TEST-24DEC31"
    assert result.market_prob == pytest.approx(0.46)
    assert result.predicted_prob == 65
    assert result.model_id == synth.model
    assert result.sources == ["https://example.com/a"]

    assert synth.get_total_tokens() == 300
    assert synth.get_last_call_cost_usd() == pytest.approx(0.0033)
    assert synth.get_total_cost_usd() == pytest.approx(0.0033)


@pytest.mark.asyncio
async def test_claude_synthesizer_caps_max_tokens_from_budget() -> None:
    tool_input: dict[str, object] = {
        "predicted_prob": 55,
        "confidence": "low",
        "reasoning": "y" * 60,
        "factors": [],
        "sources": [],
    }
    usage = _FakeUsage(input_tokens=1, output_tokens=1)
    response = _FakeResponse(tool_input=tool_input, usage=usage)
    messages = _FakeMessages(response)
    synth = ClaudeSynthesizer(client=_FakeAnthropicClient(messages), max_cost_usd=0.00003)

    await synth.synthesize(input=_make_input(with_research=False))

    assert messages.last_create_kwargs is not None
    assert messages.last_create_kwargs.get("max_tokens") == 2
