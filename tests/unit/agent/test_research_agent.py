"""Unit tests for ResearchAgent plan building and budget enforcement."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from kalshi_research.agent.research_agent import ResearchAgent
from kalshi_research.agent.schemas import ResearchStepStatus
from kalshi_research.api.models.market import Market
from kalshi_research.exa.policy import ExaBudget, ExaMode


@pytest.fixture
def mock_exa_client() -> AsyncMock:
    """Create a mock ExaClient."""
    return AsyncMock()


@pytest.fixture
def sample_market() -> Market:
    """Create a sample market for testing."""
    return Market(
        ticker="TEST-01JAN25",
        title="Will test pass by January 2025?",
        event_ticker="TEST",
        series_ticker="TEST",
        subtitle="Test market subtitle",
        open_time=datetime.now(UTC),
        close_time=datetime.now(UTC),
        expiration_time=datetime.now(UTC),
        status="active",
        yes_bid=45,
        yes_ask=55,
        no_bid=45,
        no_ask=55,
        last_price=50,
        previous_yes_bid=44,
        previous_yes_ask=54,
        previous_no_bid=44,
        previous_no_ask=54,
        previous_price=49,
        volume=1000,
        volume_24h=100,
        liquidity=500,
        open_interest=250,
        result="",
        can_close_early=False,
        cap_strike=None,
        floor_strike=None,
        category="Test",
        risk_limit_dollars=850,
    )


def test_plan_builder_fast_mode(mock_exa_client: AsyncMock, sample_market: Market) -> None:
    """Test plan builder creates correct steps for fast mode."""
    agent = ResearchAgent(mock_exa_client)

    plan = agent.build_plan(
        sample_market,
        mode=ExaMode.FAST,
        budget_usd=0.10,
    )

    assert plan.ticker == "TEST-01JAN25"
    assert plan.mode == "fast"
    assert len(plan.steps) >= 1  # At least one news search
    assert all(step.estimated_cost_usd > 0 for step in plan.steps)
    assert plan.total_estimated_cost_usd > 0

    # Fast mode should have fewer steps
    assert len(plan.steps) <= 3


def test_plan_builder_standard_mode(mock_exa_client: AsyncMock, sample_market: Market) -> None:
    """Test plan builder creates correct steps for standard mode."""
    agent = ResearchAgent(mock_exa_client)

    plan = agent.build_plan(
        sample_market,
        mode=ExaMode.STANDARD,
        budget_usd=0.50,
    )

    assert plan.ticker == "TEST-01JAN25"
    assert plan.mode == "standard"

    # Standard mode should have news searches + answer
    step_endpoints = [step.endpoint for step in plan.steps]
    assert "search" in step_endpoints
    assert "answer" in step_endpoints


def test_plan_builder_deep_mode(mock_exa_client: AsyncMock, sample_market: Market) -> None:
    """Test plan builder creates correct steps for deep mode."""
    agent = ResearchAgent(mock_exa_client)

    plan = agent.build_plan(
        sample_market,
        mode=ExaMode.DEEP,
        budget_usd=1.00,
    )

    assert plan.ticker == "TEST-01JAN25"
    assert plan.mode == "deep"

    # Deep mode should have all step types
    step_endpoints = [step.endpoint for step in plan.steps]
    assert "search" in step_endpoints
    assert "answer" in step_endpoints
    assert "research" in step_endpoints


def test_plan_id_deterministic(mock_exa_client: AsyncMock, sample_market: Market) -> None:
    """Test plan ID is deterministic for same inputs."""
    agent = ResearchAgent(mock_exa_client)

    plan1 = agent.build_plan(sample_market, mode=ExaMode.STANDARD, budget_usd=0.50)
    plan2 = agent.build_plan(sample_market, mode=ExaMode.STANDARD, budget_usd=0.50)

    assert plan1.plan_id == plan2.plan_id


def test_plan_id_varies_with_mode(mock_exa_client: AsyncMock, sample_market: Market) -> None:
    """Test plan ID changes when mode changes."""
    agent = ResearchAgent(mock_exa_client)

    plan_fast = agent.build_plan(sample_market, mode=ExaMode.FAST, budget_usd=0.50)
    plan_standard = agent.build_plan(sample_market, mode=ExaMode.STANDARD, budget_usd=0.50)

    assert plan_fast.plan_id != plan_standard.plan_id


def test_query_generation(mock_exa_client: AsyncMock, sample_market: Market) -> None:
    """Test query generation from market title."""
    agent = ResearchAgent(mock_exa_client)

    queries = agent._generate_queries("Will Bitcoin reach $100k by 2025?")

    assert len(queries) > 0
    assert len(queries) <= 3
    # Should strip "Will " prefix
    assert not any(q.lower().startswith("will ") for q in queries)
    # Should strip trailing "?"
    assert not any(q.endswith("?") for q in queries)


@pytest.mark.asyncio
async def test_budget_enforcement_stops_early(
    mock_exa_client: AsyncMock, sample_market: Market
) -> None:
    """Test that execution stops when budget is exhausted."""
    agent = ResearchAgent(mock_exa_client)

    # Create a plan with multiple steps
    plan = agent.build_plan(sample_market, mode=ExaMode.STANDARD, budget_usd=0.50)

    # Set budget to be exhausted after first step
    budget = ExaBudget(limit_usd=0.01)

    # Mock the _execute_step to track calls
    executed_steps = []

    async def mock_execute_step(step: object, market: object) -> MagicMock:
        from kalshi_research.agent.schemas import ResearchStepResult

        executed_steps.append(step)
        result = ResearchStepResult(
            step_id=step.step_id,  # type: ignore
            status=ResearchStepStatus.COMPLETED,
            actual_cost_usd=0.02,
            sources_found=5,
        )
        object.__setattr__(result, "factors", [])
        return result

    agent._execute_step = mock_execute_step  # type: ignore

    summary = await agent.execute_plan(plan, sample_market, budget=budget)

    # Only first step should execute before budget exhaustion
    assert len(executed_steps) < len(plan.steps)
    assert summary.budget_exhausted is True


@pytest.mark.asyncio
async def test_budget_tracks_actual_cost(mock_exa_client: AsyncMock, sample_market: Market) -> None:
    """Test that budget correctly tracks actual costs."""
    agent = ResearchAgent(mock_exa_client)

    plan = agent.build_plan(sample_market, mode=ExaMode.FAST, budget_usd=0.50)
    budget = ExaBudget(limit_usd=0.50)

    # Mock _execute_step to return specific costs
    async def mock_execute_step(step: object, market: object) -> MagicMock:
        from kalshi_research.agent.schemas import ResearchStepResult

        result = ResearchStepResult(
            step_id=step.step_id,  # type: ignore
            status=ResearchStepStatus.COMPLETED,
            actual_cost_usd=0.05,
            sources_found=5,
        )
        object.__setattr__(result, "factors", [])
        return result

    agent._execute_step = mock_execute_step  # type: ignore

    summary = await agent.execute_plan(plan, sample_market, budget=budget)

    # Budget should reflect actual costs
    assert summary.total_cost_usd == budget.spent_usd
    assert budget.spent_usd <= budget.limit_usd or summary.budget_exhausted


def test_plan_serialization_roundtrip(mock_exa_client: AsyncMock, sample_market: Market) -> None:
    """Test ResearchPlan can be serialized and deserialized."""
    agent = ResearchAgent(mock_exa_client)

    plan = agent.build_plan(sample_market, mode=ExaMode.STANDARD, budget_usd=0.50)

    # Serialize to JSON
    json_str = plan.model_dump_json()

    # Deserialize
    from kalshi_research.agent.schemas import ResearchPlan

    restored_plan = ResearchPlan.model_validate_json(json_str)

    assert restored_plan.plan_id == plan.plan_id
    assert restored_plan.ticker == plan.ticker
    assert restored_plan.mode == plan.mode
    assert len(restored_plan.steps) == len(plan.steps)


@pytest.mark.asyncio
async def test_deep_research_crash_recovery_by_id(
    mock_exa_client: AsyncMock, sample_market: Market
) -> None:
    """Test that deep research tasks can be recovered by saved research_id."""
    from kalshi_research.exa.models import ResearchStatus, ResearchTask

    agent = ResearchAgent(mock_exa_client)

    # Create a research step
    from kalshi_research.agent.schemas import ResearchStep

    step = ResearchStep(
        step_id="deep_research_1",
        endpoint="research",
        description="Test research",
        estimated_cost_usd=0.50,
        params={"instructions": "Research on test topic"},
    )

    # Simulate saved state from previous crash
    agent._state.save_research_task(
        ticker=sample_market.ticker,
        research_id="test-research-id-123",
        instructions="Research on test topic",
    )

    # Mock get_research_task to return completed task
    from kalshi_research.exa.models.research import ResearchCostDollars

    completed_task = ResearchTask(
        researchId="test-research-id-123",
        instructions="Research on test topic",
        status=ResearchStatus.COMPLETED,
        createdAt=int(datetime.now(UTC).timestamp()),
        citations=[],
        costDollars=ResearchCostDollars(total=0.25, numSearches=1, numPages=5, reasoningTokens=100),
    )
    mock_exa_client.get_research_task = AsyncMock(return_value=completed_task)

    # Execute step - should recover existing task
    result = await agent._execute_step(step, sample_market)

    # Verify recovery was attempted with saved ID
    mock_exa_client.get_research_task.assert_called_with("test-research-id-123")

    # Should NOT create a new task
    mock_exa_client.create_research_task.assert_not_called()

    # Result should be successful
    assert result.status == ResearchStepStatus.COMPLETED
    assert result.actual_cost_usd == 0.25


@pytest.mark.asyncio
async def test_deep_research_crash_recovery_by_list(
    mock_exa_client: AsyncMock, sample_market: Market
) -> None:
    """Test recovery falls back to find_recent_research_task when ID fails."""
    from kalshi_research.exa.models import ResearchStatus, ResearchTask

    agent = ResearchAgent(mock_exa_client)

    from kalshi_research.agent.schemas import ResearchStep

    step = ResearchStep(
        step_id="deep_research_1",
        endpoint="research",
        description="Test research",
        estimated_cost_usd=0.50,
        params={"instructions": "Research on test topic"},
    )

    # Simulate saved state with invalid ID
    agent._state.save_research_task(
        ticker=sample_market.ticker,
        research_id="invalid-id-404",
        instructions="Research on test topic",
    )

    # Mock get_research_task to fail
    mock_exa_client.get_research_task = AsyncMock(side_effect=Exception("Not found"))

    # Mock find_recent_research_task to return recovered task
    from kalshi_research.exa.models.research import ResearchCostDollars

    recovered_task = ResearchTask(
        researchId="recovered-task-id-789",
        instructions="Research on test topic",
        status=ResearchStatus.COMPLETED,
        createdAt=int(datetime.now(UTC).timestamp()),
        citations=[],
        costDollars=ResearchCostDollars(total=0.30, numSearches=1, numPages=5, reasoningTokens=100),
    )
    mock_exa_client.find_recent_research_task = AsyncMock(return_value=recovered_task)

    # Execute step - should recover via list
    result = await agent._execute_step(step, sample_market)

    # Verify fallback to find_recent_research_task
    mock_exa_client.find_recent_research_task.assert_called_once()
    call_kwargs = mock_exa_client.find_recent_research_task.call_args[1]
    assert call_kwargs["instructions_prefix"] == "Research on test topic"[:50]

    # Should NOT create new task
    mock_exa_client.create_research_task.assert_not_called()

    # Result should be successful
    assert result.status == ResearchStepStatus.COMPLETED
    assert result.actual_cost_usd == 0.30


@pytest.mark.asyncio
async def test_deep_research_creates_new_when_no_recovery(
    mock_exa_client: AsyncMock, sample_market: Market
) -> None:
    """Test that new research task is created when no recovery possible."""
    from kalshi_research.exa.models import ResearchStatus, ResearchTask

    agent = ResearchAgent(mock_exa_client)

    from kalshi_research.agent.schemas import ResearchStep

    step = ResearchStep(
        step_id="deep_research_1",
        endpoint="research",
        description="Test research",
        estimated_cost_usd=0.50,
        params={"instructions": "Research on test topic"},
    )

    # No saved state (fresh run)

    # Mock create_research_task to return new task
    from kalshi_research.exa.models.research import ResearchCostDollars

    new_task = ResearchTask(
        researchId="new-task-id-456",
        instructions="Research on test topic",
        status=ResearchStatus.COMPLETED,
        createdAt=int(datetime.now(UTC).timestamp()),
        citations=[],
        costDollars=ResearchCostDollars(total=0.40, numSearches=1, numPages=5, reasoningTokens=100),
    )
    mock_exa_client.create_research_task = AsyncMock(return_value=new_task)
    mock_exa_client.get_research_task = AsyncMock(return_value=new_task)

    # Execute step - should create new task
    result = await agent._execute_step(step, sample_market)

    # Verify new task was created
    mock_exa_client.create_research_task.assert_called_once_with(
        instructions="Research on test topic"
    )

    # Result should be successful
    assert result.status == ResearchStepStatus.COMPLETED
    assert result.actual_cost_usd == 0.40


@pytest.mark.asyncio
async def test_deep_research_clears_state_after_completion(
    mock_exa_client: AsyncMock, sample_market: Market
) -> None:
    """Test that state is cleared after successful completion."""
    from kalshi_research.exa.models import ResearchStatus, ResearchTask

    agent = ResearchAgent(mock_exa_client)

    from kalshi_research.agent.schemas import ResearchStep

    step = ResearchStep(
        step_id="deep_research_1",
        endpoint="research",
        description="Test research",
        estimated_cost_usd=0.50,
        params={"instructions": "Research on test topic"},
    )

    # Mock create and complete cycle
    from kalshi_research.exa.models.research import ResearchCostDollars

    completed_task = ResearchTask(
        researchId="task-to-clear-999",
        instructions="Research on test topic",
        status=ResearchStatus.COMPLETED,
        createdAt=int(datetime.now(UTC).timestamp()),
        citations=[],
        costDollars=ResearchCostDollars(total=0.35, numSearches=1, numPages=5, reasoningTokens=100),
    )
    mock_exa_client.create_research_task = AsyncMock(return_value=completed_task)
    mock_exa_client.get_research_task = AsyncMock(return_value=completed_task)

    # Execute step
    await agent._execute_step(step, sample_market)

    # Verify state file does not exist after completion
    state_file = agent._state._get_state_file(sample_market.ticker)
    assert not state_file.exists(), "State file should be cleaned up after completion"
