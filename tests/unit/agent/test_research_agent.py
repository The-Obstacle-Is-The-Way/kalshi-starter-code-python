"""Unit tests for ResearchAgent plan building and budget enforcement."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from kalshi_research.agent.research_agent import ResearchAgent
from kalshi_research.agent.schemas import (
    ResearchPlan,
    ResearchStep,
    ResearchStepResult,
    ResearchStepStatus,
    ResearchSummary,
)
from kalshi_research.agent.state import ResearchTaskState
from kalshi_research.api.models.market import Market
from kalshi_research.exa.exceptions import ExaAPIError
from kalshi_research.exa.models import (
    AnswerResponse,
    Citation,
    CostDollars,
    SearchResponse,
    SearchResult,
)
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


@pytest.fixture
def agent(mock_exa_client: AsyncMock, tmp_path: Path) -> ResearchAgent:
    """Create a ResearchAgent with isolated state dir."""
    agent = ResearchAgent(mock_exa_client)
    isolated_state = ResearchTaskState(state_dir=tmp_path / "agent_state")
    agent._state = isolated_state
    # Also update the executor's state reference
    agent._executor._state = isolated_state
    agent._executor._recovery._state = isolated_state
    return agent


def test_plan_builder_fast_mode(agent: ResearchAgent, sample_market: Market) -> None:
    """Test plan builder creates correct steps for fast mode."""
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


def test_plan_builder_standard_mode(agent: ResearchAgent, sample_market: Market) -> None:
    """Test plan builder creates correct steps for standard mode."""
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


def test_plan_builder_deep_mode(agent: ResearchAgent, sample_market: Market) -> None:
    """Test plan builder creates correct steps for deep mode."""
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


def test_plan_id_deterministic(agent: ResearchAgent, sample_market: Market) -> None:
    """Test plan ID is deterministic for same inputs."""
    plan1 = agent.build_plan(sample_market, mode=ExaMode.STANDARD, budget_usd=0.50)
    plan2 = agent.build_plan(sample_market, mode=ExaMode.STANDARD, budget_usd=0.50)

    assert plan1.plan_id == plan2.plan_id


def test_plan_id_varies_with_mode(agent: ResearchAgent, sample_market: Market) -> None:
    """Test plan ID changes when mode changes."""
    plan_fast = agent.build_plan(sample_market, mode=ExaMode.FAST, budget_usd=0.50)
    plan_standard = agent.build_plan(sample_market, mode=ExaMode.STANDARD, budget_usd=0.50)

    assert plan_fast.plan_id != plan_standard.plan_id


def test_build_plan_rejects_non_positive_deep_research_params(
    agent: ResearchAgent, sample_market: Market
) -> None:
    """Test that deep research polling parameters must be positive."""
    with pytest.raises(ValueError, match="deep_research_timeout_seconds must be positive"):
        agent.build_plan(
            sample_market,
            mode=ExaMode.DEEP,
            budget_usd=1.00,
            deep_research_timeout_seconds=0,
        )

    with pytest.raises(ValueError, match="deep_research_poll_interval_seconds must be positive"):
        agent.build_plan(
            sample_market,
            mode=ExaMode.DEEP,
            budget_usd=1.00,
            deep_research_poll_interval_seconds=0,
        )


def test_query_generation(agent: ResearchAgent, sample_market: Market) -> None:
    """Test query generation from market title."""
    queries = agent._generate_queries("Will Bitcoin reach $100k by 2025?")

    assert len(queries) > 0
    assert len(queries) <= 3
    # Should strip "Will " prefix
    assert not any(q.lower().startswith("will ") for q in queries)
    # Should strip trailing "?"
    assert not any(q.endswith("?") for q in queries)


def test_query_generation_no_will_prefix(agent: ResearchAgent) -> None:
    """Test query generation when title does not start with 'Will '."""
    queries = agent._generate_queries("Bitcoin price forecast 2025")
    assert queries[0] == "Bitcoin price forecast 2025"


@pytest.mark.asyncio
async def test_budget_enforcement_stops_early(
    agent: ResearchAgent, sample_market: Market, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that execution stops when budget is exhausted."""
    plan = ResearchPlan(
        plan_id="test-plan",
        ticker=sample_market.ticker,
        mode="standard",
        steps=[
            ResearchStep(
                step_id="step-1",
                endpoint="search",
                description="Step 1",
                estimated_cost_usd=0.01,
                params={"query": "test"},
            ),
            ResearchStep(
                step_id="step-2",
                endpoint="search",
                description="Step 2",
                estimated_cost_usd=0.01,
                params={"query": "test"},
            ),
        ],
        total_estimated_cost_usd=0.02,
    )

    # Set budget to be exhausted after first step
    budget = ExaBudget(limit_usd=0.015)

    # Mock the _execute_step to track calls
    executed_steps: list[ResearchStep] = []

    async def mock_execute_step(step: ResearchStep, market: Market) -> ResearchStepResult:
        executed_steps.append(step)
        _ = market
        return ResearchStepResult(
            step_id=step.step_id,
            status=ResearchStepStatus.COMPLETED,
            actual_cost_usd=0.01,
            sources_found=5,
            factors=[],
        )

    monkeypatch.setattr(agent._executor, "execute_step", mock_execute_step)

    summary = await agent.execute_plan(plan, sample_market, budget=budget)

    # Only first step should execute before budget exhaustion
    assert executed_steps == [plan.steps[0]]
    assert summary.budget_exhausted is True


@pytest.mark.asyncio
async def test_budget_tracks_actual_cost(
    agent: ResearchAgent, sample_market: Market, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that budget correctly tracks actual costs."""
    plan = agent.build_plan(sample_market, mode=ExaMode.FAST, budget_usd=0.50)
    budget = ExaBudget(limit_usd=0.50)

    # Mock _execute_step to return specific costs
    async def mock_execute_step(step: ResearchStep, market: Market) -> ResearchStepResult:
        _ = market
        return ResearchStepResult(
            step_id=step.step_id,
            status=ResearchStepStatus.COMPLETED,
            actual_cost_usd=0.05,
            sources_found=5,
            factors=[],
        )

    monkeypatch.setattr(agent._executor, "execute_step", mock_execute_step)

    summary = await agent.execute_plan(plan, sample_market, budget=budget)

    # Budget should reflect actual costs
    assert summary.total_cost_usd == budget.spent_usd
    assert budget.spent_usd <= budget.limit_usd or summary.budget_exhausted


def test_plan_serialization_roundtrip(agent: ResearchAgent, sample_market: Market) -> None:
    """Test ResearchPlan can be serialized and deserialized."""
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
async def test_execute_plan_records_failed_step_on_exa_error(
    agent: ResearchAgent, sample_market: Market, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that execute_plan records failure and continues on Exa errors."""
    plan = ResearchPlan(
        plan_id="test-plan",
        ticker=sample_market.ticker,
        mode="standard",
        steps=[
            ResearchStep(
                step_id="step-1",
                endpoint="search",
                description="Step 1",
                estimated_cost_usd=0.01,
                params={"query": "test"},
            )
        ],
        total_estimated_cost_usd=0.01,
    )

    budget = ExaBudget(limit_usd=1.0)

    async def mock_execute_step(step: ResearchStep, market: Market) -> ResearchStepResult:
        _ = step
        _ = market
        raise ExaAPIError("boom", status_code=500)

    monkeypatch.setattr(agent._executor, "execute_step", mock_execute_step)

    summary = await agent.execute_plan(plan, sample_market, budget=budget)

    assert summary.total_cost_usd == 0.0
    assert summary.steps_executed == [
        {
            "step_id": "step-1",
            "status": ResearchStepStatus.FAILED.value,
            "actual_cost_usd": 0.0,
            "error": "boom",
        }
    ]


@pytest.mark.asyncio
async def test_execute_plan_reraises_unexpected_exception(
    agent: ResearchAgent, sample_market: Market, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that execute_plan re-raises unexpected exceptions."""
    plan = ResearchPlan(
        plan_id="test-plan",
        ticker=sample_market.ticker,
        mode="standard",
        steps=[
            ResearchStep(
                step_id="step-1",
                endpoint="search",
                description="Step 1",
                estimated_cost_usd=0.01,
                params={"query": "test"},
            )
        ],
        total_estimated_cost_usd=0.01,
    )

    budget = ExaBudget(limit_usd=1.0)

    async def mock_execute_step(step: ResearchStep, market: Market) -> ResearchStepResult:
        _ = step
        _ = market
        raise RuntimeError("kaboom")

    monkeypatch.setattr(agent._executor, "execute_step", mock_execute_step)

    with pytest.raises(RuntimeError, match="kaboom"):
        await agent.execute_plan(plan, sample_market, budget=budget)


@pytest.mark.asyncio
async def test_research_convenience_method_calls_execute_plan(
    agent: ResearchAgent, sample_market: Market, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that research() builds a plan and delegates to execute_plan()."""

    async def fake_execute_plan(
        plan: ResearchPlan, market: Market, *, budget: ExaBudget
    ) -> ResearchSummary:
        assert plan.ticker == sample_market.ticker
        assert market is sample_market
        assert budget.limit_usd == 0.10
        return ResearchSummary(
            ticker=sample_market.ticker,
            title=sample_market.title,
            mode="fast",
            factors=[],
            queries_used=[],
            total_sources_found=0,
            total_cost_usd=0.0,
            budget_usd=budget.limit_usd,
            budget_exhausted=False,
            steps_executed=[],
        )

    monkeypatch.setattr(agent, "execute_plan", fake_execute_plan)

    summary = await agent.research(sample_market, mode=ExaMode.FAST, budget_usd=0.10)
    assert summary.mode == "fast"


@pytest.mark.asyncio
async def test_deep_research_crash_recovery_by_id(
    agent: ResearchAgent, sample_market: Market, mock_exa_client: AsyncMock
) -> None:
    """Test that deep research tasks can be recovered by saved research_id."""
    # Create a research step
    from kalshi_research.agent.schemas import ResearchStep
    from kalshi_research.exa.models import ResearchStatus, ResearchTask

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
    agent: ResearchAgent, sample_market: Market, mock_exa_client: AsyncMock
) -> None:
    """Test recovery falls back to find_recent_research_task when ID fails."""
    from kalshi_research.agent.schemas import ResearchStep
    from kalshi_research.exa.models import ResearchStatus, ResearchTask

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
    mock_exa_client.get_research_task = AsyncMock(
        side_effect=ExaAPIError("Not found", status_code=404)
    )

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
    agent: ResearchAgent, sample_market: Market, mock_exa_client: AsyncMock
) -> None:
    """Test that new research task is created when no recovery possible."""
    from kalshi_research.agent.schemas import ResearchStep
    from kalshi_research.exa.models import ResearchStatus, ResearchTask

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
    agent: ResearchAgent, sample_market: Market, mock_exa_client: AsyncMock
) -> None:
    """Test that state is cleared after successful completion."""
    from kalshi_research.agent.schemas import ResearchStep
    from kalshi_research.exa.models import ResearchStatus, ResearchTask

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


@pytest.mark.asyncio
async def test_deep_research_waits_for_running_recovered_task(
    agent: ResearchAgent, sample_market: Market, mock_exa_client: AsyncMock
) -> None:
    """Test that running recovered tasks are awaited via wait_for_research()."""
    from kalshi_research.exa.models import ResearchCostDollars, ResearchStatus, ResearchTask

    step = ResearchStep(
        step_id="deep_research_1",
        endpoint="research",
        description="Test research",
        estimated_cost_usd=0.50,
        params={
            "instructions": "Research on test topic",
            "poll_interval_seconds": 1.0,
            "timeout_seconds": 10.0,
        },
    )

    agent._state.save_research_task(
        ticker=sample_market.ticker,
        research_id="running-id-1",
        instructions="Research on test topic",
    )

    running_task = ResearchTask(
        researchId="running-id-1",
        instructions="Research on test topic",
        status=ResearchStatus.RUNNING,
        createdAt=int(datetime.now(UTC).timestamp()),
        citations=None,
        costDollars=None,
    )
    completed_task = ResearchTask(
        researchId="running-id-1",
        instructions="Research on test topic",
        status=ResearchStatus.COMPLETED,
        createdAt=int(datetime.now(UTC).timestamp()),
        citations=[
            ResearchTask.Citation(
                id="c1",
                url="https://example.com/1",
                title="Example Citation",
            )
        ],
        costDollars=ResearchCostDollars(total=0.25, numSearches=1, numPages=2, reasoningTokens=10),
    )

    mock_exa_client.get_research_task = AsyncMock(return_value=running_task)
    mock_exa_client.wait_for_research = AsyncMock(return_value=completed_task)

    result = await agent._execute_step(step, sample_market)

    mock_exa_client.wait_for_research.assert_called_once_with(
        "running-id-1", poll_interval=1.0, timeout=10.0
    )
    assert result.actual_cost_usd == 0.25
    assert result.sources_found == 1
    assert result.factors[0].source_url == "https://example.com/1"
    assert not agent._state._get_state_file(sample_market.ticker).exists()


@pytest.mark.asyncio
async def test_deep_research_timeout_keeps_state_file(
    agent: ResearchAgent, sample_market: Market, mock_exa_client: AsyncMock
) -> None:
    """Test that timeouts do not clear crash-recovery state."""
    from kalshi_research.exa.models import ResearchStatus, ResearchTask

    step = ResearchStep(
        step_id="deep_research_1",
        endpoint="research",
        description="Test research",
        estimated_cost_usd=0.50,
        params={
            "instructions": "Research on test topic",
            "poll_interval_seconds": 1.0,
            "timeout_seconds": 10.0,
        },
    )

    created = ResearchTask(
        researchId="timeout-id-1",
        instructions="Research on test topic",
        status=ResearchStatus.RUNNING,
        createdAt=int(datetime.now(UTC).timestamp()),
        citations=None,
        costDollars=None,
    )
    mock_exa_client.create_research_task = AsyncMock(return_value=created)
    mock_exa_client.wait_for_research = AsyncMock(side_effect=TimeoutError)

    with pytest.raises(TimeoutError):
        await agent._execute_step(step, sample_market)

    assert agent._state._get_state_file(sample_market.ticker).exists()


@pytest.mark.asyncio
async def test_deep_research_failure_clears_state_file(
    agent: ResearchAgent, sample_market: Market, mock_exa_client: AsyncMock
) -> None:
    """Test that terminal failure clears crash-recovery state."""
    from kalshi_research.exa.models import ResearchStatus, ResearchTask

    step = ResearchStep(
        step_id="deep_research_1",
        endpoint="research",
        description="Test research",
        estimated_cost_usd=0.50,
        params={
            "instructions": "Research on test topic",
            "poll_interval_seconds": 1.0,
            "timeout_seconds": 10.0,
        },
    )

    created = ResearchTask(
        researchId="failed-id-1",
        instructions="Research on test topic",
        status=ResearchStatus.RUNNING,
        createdAt=int(datetime.now(UTC).timestamp()),
        citations=None,
        costDollars=None,
    )
    failed = ResearchTask(
        researchId="failed-id-1",
        instructions="Research on test topic",
        status=ResearchStatus.FAILED,
        createdAt=int(datetime.now(UTC).timestamp()),
        citations=None,
        costDollars=None,
    )
    mock_exa_client.create_research_task = AsyncMock(return_value=created)
    mock_exa_client.wait_for_research = AsyncMock(return_value=failed)

    with pytest.raises(ExaAPIError, match="status=failed"):
        await agent._execute_step(step, sample_market)

    assert not agent._state._get_state_file(sample_market.ticker).exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("poll_interval_seconds", "timeout_seconds", "match"),
    [
        (0, 10, "poll_interval_seconds must be positive"),
        (10, 0, "timeout_seconds must be positive"),
    ],
)
async def test_deep_research_rejects_non_positive_polling_params(
    agent: ResearchAgent,
    sample_market: Market,
    poll_interval_seconds: float,
    timeout_seconds: float,
    match: str,
) -> None:
    """Test that deep research validates polling parameters before calling Exa."""
    step = ResearchStep(
        step_id="deep_research_1",
        endpoint="research",
        description="Test research",
        estimated_cost_usd=0.50,
        params={
            "instructions": "Research on test topic",
            "poll_interval_seconds": poll_interval_seconds,
            "timeout_seconds": timeout_seconds,
        },
    )

    with pytest.raises(ValueError, match=match):
        await agent._execute_step(step, sample_market)


@pytest.mark.asyncio
async def test_execute_step_search_extracts_factors(
    agent: ResearchAgent, sample_market: Market, mock_exa_client: AsyncMock
) -> None:
    """Test that search step extracts factors and parses start date."""
    step = ResearchStep(
        step_id="search_1",
        endpoint="search",
        description="Search",
        estimated_cost_usd=0.01,
        params={
            "query": "test query",
            "num_results": 2,
            "start_published_date": "2026-01-01T00:00:00Z",
            "category": "news",
            "include_text": False,
            "include_highlights": True,
        },
    )

    response = SearchResponse(
        request_id="req-1",
        results=[
            SearchResult(
                id="r1",
                url="https://example.com/a",
                title="Result A",
                published_date=datetime.now(UTC),
                highlights=["Highlighted A"],
            ),
            SearchResult(
                id="r2",
                url="https://example.com/b",
                title="Result B",
                published_date=None,
                highlights=None,
            ),
        ],
        cost_dollars=CostDollars(total=0.02),
    )
    mock_exa_client.search = AsyncMock(return_value=response)

    result = await agent._execute_step(step, sample_market)

    assert result.actual_cost_usd == 0.02
    assert result.sources_found == 2
    assert result.factors[0].factor_text == "Highlighted A"
    assert result.factors[1].factor_text == "Result B"
    assert result.factors[0].confidence == "medium"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("answer_text", "expected_factor_text"),
    [
        ("Here is the answer text.", "Here is the answer text."),
        ("", "Citation title"),
    ],
)
async def test_execute_step_answer_extracts_factors(
    agent: ResearchAgent,
    sample_market: Market,
    mock_exa_client: AsyncMock,
    answer_text: str,
    expected_factor_text: str,
) -> None:
    """Test that answer step extracts factors from citations."""
    step = ResearchStep(
        step_id="answer_1",
        endpoint="answer",
        description="Answer",
        estimated_cost_usd=0.01,
        params={"query": "test", "include_text": False},
    )

    response = AnswerResponse(
        answer=answer_text,
        citations=[
            Citation(
                id="c1",
                url="https://example.com/c",
                title="Citation title",
                published_date=datetime.now(UTC),
            )
        ],
        cost_dollars=CostDollars(total=0.03),
    )
    mock_exa_client.answer = AsyncMock(return_value=response)

    result = await agent._execute_step(step, sample_market)

    assert result.actual_cost_usd == 0.03
    assert result.sources_found == 1
    assert result.factors[0].source_url == "https://example.com/c"
    assert result.factors[0].factor_text == expected_factor_text[:200]


@pytest.mark.asyncio
async def test_execute_step_unknown_endpoint_raises(
    agent: ResearchAgent, sample_market: Market
) -> None:
    """Test that unknown endpoints raise a ValueError."""
    step = ResearchStep(
        step_id="bad_1",
        endpoint="nope",
        description="Bad",
        estimated_cost_usd=0.0,
        params={},
    )

    with pytest.raises(ValueError, match="Unknown research step endpoint"):
        await agent._execute_step(step, sample_market)
