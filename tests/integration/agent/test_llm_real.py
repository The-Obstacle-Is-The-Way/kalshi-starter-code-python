from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest

from kalshi_research.agent.providers.llm import ClaudeSynthesizer, SynthesisInput
from kalshi_research.agent.schemas import MarketInfo, MarketPriceSnapshot


def _anthropic_available() -> bool:
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_claude_synthesis_returns_valid_result() -> None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    if not _anthropic_available():
        pytest.skip("anthropic dependency not installed (run: uv sync --extra llm)")

    now = datetime.now(UTC)
    market = MarketInfo(
        ticker="TEST-24DEC31",
        event_ticker="EVT",
        series_ticker=None,
        title="Will a thing happen?",
        subtitle="Integration test market (not real)",
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
        volume_24h=100,
        open_interest=10,
        midpoint_prob=0.46,
        spread_cents=2,
        captured_at=now,
    )

    synth = ClaudeSynthesizer()
    result = await synth.synthesize(input=SynthesisInput(market=market, snapshot=snapshot))

    assert result.reasoning
    assert 0 <= result.predicted_prob <= 100
    assert result.confidence in {"low", "medium", "high"}
