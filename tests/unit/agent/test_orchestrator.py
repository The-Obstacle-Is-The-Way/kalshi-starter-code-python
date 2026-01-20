"""Unit tests for agent orchestrator."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from kalshi_research.agent.orchestrator import AgentKernel
from kalshi_research.agent.providers.llm import MockSynthesizer, SynthesisInput
from kalshi_research.agent.schemas import (
    AnalysisResult,
    Factor,
    ResearchSummary,
)
from kalshi_research.exa.policy import ExaMode


@pytest.fixture
def mock_kalshi_client() -> MagicMock:
    """Create mock Kalshi client."""
    client = MagicMock()

    # Mock get_market response
    mock_market = MagicMock()
    mock_market.ticker = "TEST-24DEC31"
    mock_market.event_ticker = "TEST"
    mock_market.series_ticker = None
    mock_market.title = "Test Market"
    mock_market.subtitle = "Test Subtitle"
    mock_market.status = "active"
    mock_market.open_time = datetime.now(UTC)
    mock_market.close_time = datetime.now(UTC)
    mock_market.expiration_time = datetime.now(UTC)
    mock_market.settlement_ts = None
    mock_market.last_price_cents = 55
    mock_market.volume_24h = 1000
    mock_market.open_interest = 500

    client.get_market = AsyncMock(return_value=mock_market)

    # Mock get_orderbook response
    mock_orderbook = MagicMock()
    mock_orderbook.yes = [(50, 60)]
    mock_orderbook.no = [(40, 50)]
    mock_orderbook.best_yes_bid = 50
    mock_orderbook.best_no_bid = 40

    client.get_orderbook = AsyncMock(return_value=mock_orderbook)

    return client


@pytest.fixture
def mock_research_agent() -> MagicMock:
    """Create mock research agent."""
    agent = MagicMock()

    # Mock research method
    async def mock_research(market: object, mode: ExaMode, budget_usd: float) -> ResearchSummary:
        return ResearchSummary(
            ticker="TEST-24DEC31",
            title="Test Market",
            mode=mode,
            factors=[
                Factor(
                    factor_text="Test factor",
                    source_url="https://example.com/1",
                    confidence="high",
                )
            ],
            queries_used=["test query"],
            total_sources_found=1,
            total_cost_usd=0.10,
            budget_usd=budget_usd,
            budget_exhausted=False,
            researched_at=datetime.now(UTC),
            steps_executed=[],
        )

    agent.research = AsyncMock(side_effect=mock_research)

    return agent


@pytest.mark.asyncio
async def test_orchestrator_basic_workflow(
    mock_kalshi_client: MagicMock, mock_research_agent: MagicMock
) -> None:
    """Test basic orchestrator workflow."""
    synthesizer = MockSynthesizer()

    kernel = AgentKernel(
        kalshi_client=mock_kalshi_client,
        research_agent=mock_research_agent,
        synthesizer=synthesizer,
        max_exa_usd=0.25,
        max_llm_usd=0.25,
    )

    result = await kernel.analyze(ticker="TEST-24DEC31", research_mode="standard")

    # Verify result structure
    assert result.analysis is not None
    assert result.verification is not None
    assert result.research is not None
    assert result.escalated is False
    assert result.total_cost_usd > 0.0

    # Verify Kalshi client was called
    # get_market is called 3 times: fetch_market_info, fetch_price_snapshot, research_agent
    assert mock_kalshi_client.get_market.call_count == 3
    mock_kalshi_client.get_orderbook.assert_called_once_with(ticker="TEST-24DEC31")

    # Verify research agent was called
    mock_research_agent.research.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_without_research_agent(mock_kalshi_client: MagicMock) -> None:
    """Test orchestrator without research agent (skips research step)."""
    synthesizer = MockSynthesizer()

    kernel = AgentKernel(
        kalshi_client=mock_kalshi_client,
        research_agent=None,  # No research
        synthesizer=synthesizer,
        max_exa_usd=0.25,
        max_llm_usd=0.25,
    )

    result = await kernel.analyze(ticker="TEST-24DEC31", research_mode="fast")

    # Verify result structure
    assert result.analysis is not None
    assert result.verification is not None
    assert result.research is None  # No research performed
    assert result.escalated is False
    assert result.total_cost_usd == 0.0  # No Exa cost


@pytest.mark.asyncio
async def test_orchestrator_verification_fails(
    mock_kalshi_client: MagicMock, mock_research_agent: MagicMock
) -> None:
    """Test orchestrator when verification fails."""

    # Create synthesizer that returns invalid analysis
    class BadSynthesizer:
        async def synthesize(self, *, input: SynthesisInput) -> AnalysisResult:
            return AnalysisResult(
                ticker=input.market.ticker,
                market_prob=input.snapshot.midpoint_prob,
                predicted_prob=50,
                confidence="high",  # Requires 3 citations
                reasoning="A" * 100,
                factors=[],
                sources=[],  # Insufficient citations
                generated_at=datetime.now(UTC),
                model_id="bad-v1",
            )

        def get_last_call_cost_usd(self) -> float:
            return 0.0

    synthesizer = BadSynthesizer()

    kernel = AgentKernel(
        kalshi_client=mock_kalshi_client,
        research_agent=mock_research_agent,
        synthesizer=synthesizer,
        max_exa_usd=0.25,
        max_llm_usd=0.25,
    )

    result = await kernel.analyze(ticker="TEST-24DEC31", research_mode="standard")

    # Verification should fail
    assert result.verification.passed is False
    assert len(result.verification.issues) > 0
    assert result.verification.suggested_escalation is True

    # Escalation is not implemented; the suggestion is informational only.
    assert result.escalated is False


@pytest.mark.asyncio
async def test_orchestrator_research_mode_propagation(
    mock_kalshi_client: MagicMock, mock_research_agent: MagicMock
) -> None:
    """Test that research mode is correctly propagated to research agent."""
    synthesizer = MockSynthesizer()

    kernel = AgentKernel(
        kalshi_client=mock_kalshi_client,
        research_agent=mock_research_agent,
        synthesizer=synthesizer,
        max_exa_usd=0.50,
        max_llm_usd=0.25,
    )

    await kernel.analyze(ticker="TEST-24DEC31", research_mode="deep")

    # Verify research agent was called with correct mode and budget
    call_args = mock_research_agent.research.call_args
    assert call_args is not None
    assert call_args.kwargs["mode"] == ExaMode.DEEP
    assert call_args.kwargs["budget_usd"] == 0.50


@pytest.mark.asyncio
async def test_orchestrator_cost_tracking(
    mock_kalshi_client: MagicMock, mock_research_agent: MagicMock
) -> None:
    """Test that total cost is correctly tracked."""
    synthesizer = MockSynthesizer()

    kernel = AgentKernel(
        kalshi_client=mock_kalshi_client,
        research_agent=mock_research_agent,
        synthesizer=synthesizer,
        max_exa_usd=0.25,
        max_llm_usd=0.25,
    )

    result = await kernel.analyze(ticker="TEST-24DEC31", research_mode="standard")

    # Total cost should include research cost (0.10 from mock)
    assert result.total_cost_usd == 0.10  # Mock research returns 0.10
    assert result.research is not None
    assert result.research.total_cost_usd == 0.10


@pytest.mark.asyncio
async def test_orchestrator_escalation_disabled_by_default(
    mock_kalshi_client: MagicMock, mock_research_agent: MagicMock
) -> None:
    """Test that escalation suggestions do not change behavior."""

    # Create synthesizer that returns invalid analysis (triggers escalation suggestion)
    class BadSynthesizer:
        async def synthesize(self, *, input: SynthesisInput) -> AnalysisResult:
            return AnalysisResult(
                ticker=input.market.ticker,
                market_prob=input.snapshot.midpoint_prob,
                predicted_prob=50,
                confidence="high",  # Requires 3 citations
                reasoning="A" * 100,
                factors=[],
                sources=[],  # Insufficient citations
                generated_at=datetime.now(UTC),
                model_id="bad-v1",
            )

        def get_last_call_cost_usd(self) -> float:
            return 0.0

    synthesizer = BadSynthesizer()

    kernel = AgentKernel(
        kalshi_client=mock_kalshi_client,
        research_agent=mock_research_agent,
        synthesizer=synthesizer,
        max_exa_usd=0.25,
        max_llm_usd=0.25,
    )

    result = await kernel.analyze(ticker="TEST-24DEC31", research_mode="standard")

    # Escalation can be suggested but is not executed in this repo today.
    assert result.verification.suggested_escalation is True
    assert result.escalated is False


@pytest.mark.asyncio
async def test_orchestrator_schema_validation(
    mock_kalshi_client: MagicMock, mock_research_agent: MagicMock
) -> None:
    """Test that all schemas are correctly validated."""
    synthesizer = MockSynthesizer()

    kernel = AgentKernel(
        kalshi_client=mock_kalshi_client,
        research_agent=mock_research_agent,
        synthesizer=synthesizer,
        max_exa_usd=0.25,
        max_llm_usd=0.25,
    )

    result = await kernel.analyze(ticker="TEST-24DEC31", research_mode="standard")

    # Verify all schemas are valid (Pydantic validation)
    assert isinstance(result.analysis, AnalysisResult)
    assert isinstance(result.research, ResearchSummary)
    assert 0 <= result.analysis.market_prob <= 1.0
    assert 0 <= result.analysis.predicted_prob <= 100
    assert result.analysis.confidence in {"low", "medium", "high"}
