"""Unit tests for agent schemas."""

import json
from datetime import UTC, datetime

import pytest

from kalshi_research.agent.schemas import (
    Factor,
    ResearchPlan,
    ResearchStep,
    ResearchStepResult,
    ResearchStepStatus,
    ResearchSummary,
)


def test_research_step_creation() -> None:
    """Test ResearchStep creation and immutability."""
    step = ResearchStep(
        step_id="test_1",
        endpoint="search",
        description="Test search",
        estimated_cost_usd=0.05,
        params={"query": "test"},
    )

    assert step.step_id == "test_1"
    assert step.endpoint == "search"
    assert step.estimated_cost_usd == 0.05
    assert step.params == {"query": "test"}

    # Test immutability
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        step.step_id = "modified"


def test_research_plan_serialization() -> None:
    """Test ResearchPlan JSON serialization stability."""
    now = datetime.now(UTC)
    plan = ResearchPlan(
        plan_id="test_plan_123",
        ticker="TEST-01JAN25",
        mode="standard",
        steps=[
            ResearchStep(
                step_id="step_1",
                endpoint="search",
                description="News search",
                estimated_cost_usd=0.02,
                params={"query": "test query"},
            )
        ],
        total_estimated_cost_usd=0.02,
        created_at=now,
    )

    # Serialize to JSON
    json_str = plan.model_dump_json()
    data = json.loads(json_str)

    assert data["plan_id"] == "test_plan_123"
    assert data["ticker"] == "TEST-01JAN25"
    assert data["mode"] == "standard"
    assert len(data["steps"]) == 1
    assert data["total_estimated_cost_usd"] == 0.02

    # Deserialize back
    restored = ResearchPlan.model_validate(data)
    assert restored.plan_id == plan.plan_id
    assert restored.ticker == plan.ticker


def test_factor_with_source() -> None:
    """Test Factor model requires source URL."""
    factor = Factor(
        factor_text="Test finding",
        source_url="https://example.com/article",
        confidence="high",
        highlight="Key quote from article",
    )

    assert factor.factor_text == "Test finding"
    assert factor.source_url == "https://example.com/article"
    assert factor.confidence == "high"
    assert factor.highlight == "Key quote from article"


def test_research_summary_defaults() -> None:
    """Test ResearchSummary with default values."""
    summary = ResearchSummary(
        ticker="TEST-01JAN25",
        title="Will test pass?",
        mode="fast",
        total_cost_usd=0.03,
        budget_usd=0.50,
    )

    assert summary.factors == []
    assert summary.queries_used == []
    assert summary.total_sources_found == 0
    assert summary.budget_exhausted is False
    assert summary.steps_executed == []


def test_research_summary_budget_exhausted() -> None:
    """Test ResearchSummary correctly tracks budget exhaustion."""
    summary = ResearchSummary(
        ticker="TEST-01JAN25",
        title="Test market",
        mode="deep",
        factors=[],
        total_cost_usd=1.05,
        budget_usd=1.00,
        budget_exhausted=True,
    )

    assert summary.budget_exhausted is True
    assert summary.total_cost_usd > summary.budget_usd


def test_research_summary_serialization_with_factors() -> None:
    """Test ResearchSummary serialization includes factors correctly."""
    summary = ResearchSummary(
        ticker="TEST-01JAN25",
        title="Test market",
        mode="standard",
        factors=[
            Factor(
                factor_text="Finding 1",
                source_url="https://example.com/1",
                confidence="high",
            ),
            Factor(
                factor_text="Finding 2",
                source_url="https://example.com/2",
                confidence="medium",
            ),
        ],
        queries_used=["query1", "query2"],
        total_sources_found=10,
        total_cost_usd=0.15,
        budget_usd=0.50,
    )

    json_str = summary.model_dump_json()
    data = json.loads(json_str)

    assert len(data["factors"]) == 2
    assert data["factors"][0]["factor_text"] == "Finding 1"
    assert data["factors"][1]["source_url"] == "https://example.com/2"
    assert data["queries_used"] == ["query1", "query2"]
    assert data["total_sources_found"] == 10


def test_research_step_result_status() -> None:
    """Test ResearchStepResult status tracking."""
    result = ResearchStepResult(
        step_id="test_1",
        status=ResearchStepStatus.COMPLETED,
        actual_cost_usd=0.04,
        sources_found=5,
    )

    assert result.status == ResearchStepStatus.COMPLETED
    assert result.actual_cost_usd == 0.04
    assert result.sources_found == 5
    assert result.error_message is None


def test_research_step_result_failed() -> None:
    """Test ResearchStepResult with failure."""
    result = ResearchStepResult(
        step_id="test_1",
        status=ResearchStepStatus.FAILED,
        actual_cost_usd=0.0,
        error_message="API timeout",
    )

    assert result.status == ResearchStepStatus.FAILED
    assert result.error_message == "API timeout"
