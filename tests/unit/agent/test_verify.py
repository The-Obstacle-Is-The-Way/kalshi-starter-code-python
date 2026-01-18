"""Unit tests for agent verification module."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kalshi_research.agent.schemas import AnalysisFactor, AnalysisResult
from kalshi_research.agent.verify import verify_analysis


def test_verify_analysis_valid():
    """Test verification passes for valid analysis."""
    analysis = AnalysisResult(
        ticker="TEST-24DEC31",
        market_prob=0.55,
        predicted_prob=60,
        confidence="medium",
        reasoning="A" * 100,  # Valid length
        factors=[
            AnalysisFactor(description="Factor 1", impact="up", source_url="https://example.com/1"),
            AnalysisFactor(
                description="Factor 2", impact="down", source_url="https://example.com/2"
            ),
        ],
        sources=["https://example.com/1", "https://example.com/2"],
        generated_at=datetime.now(UTC),
        model_id="test-v1",
    )

    report = verify_analysis(analysis)

    assert report.passed is True
    assert len(report.issues) == 0
    assert report.suggested_escalation is False
    assert len(report.checked_sources) == 2


def test_verify_analysis_insufficient_citations():
    """Test verification fails when citations are insufficient for confidence level."""
    analysis = AnalysisResult(
        ticker="TEST-24DEC31",
        market_prob=0.55,
        predicted_prob=60,
        confidence="high",  # Requires >= 3 citations
        reasoning="A" * 100,
        factors=[
            AnalysisFactor(description="Factor 1", impact="up", source_url="https://example.com/1")
        ],
        sources=["https://example.com/1"],  # Only 1 citation
        generated_at=datetime.now(UTC),
    )

    report = verify_analysis(analysis)

    assert report.passed is False
    assert any("Insufficient citations" in issue for issue in report.issues)
    assert report.suggested_escalation is True


def test_verify_analysis_duplicate_sources():
    """Test verification fails when duplicate URLs found in sources."""
    analysis = AnalysisResult(
        ticker="TEST-24DEC31",
        market_prob=0.55,
        predicted_prob=60,
        confidence="medium",
        reasoning="A" * 100,
        factors=[
            AnalysisFactor(description="Factor 1", impact="up", source_url="https://example.com/1"),
            AnalysisFactor(
                description="Factor 2", impact="down", source_url="https://example.com/2"
            ),
        ],
        sources=["https://example.com/1", "https://example.com/1"],  # Duplicate
        generated_at=datetime.now(UTC),
    )

    report = verify_analysis(analysis)

    assert report.passed is False
    assert any("Duplicate URLs" in issue for issue in report.issues)


def test_verify_analysis_source_not_in_factors():
    """Test verification fails when source URL not found in any factor."""
    analysis = AnalysisResult(
        ticker="TEST-24DEC31",
        market_prob=0.55,
        predicted_prob=60,
        confidence="medium",
        reasoning="A" * 100,
        factors=[
            AnalysisFactor(description="Factor 1", impact="up", source_url="https://example.com/1"),
            AnalysisFactor(
                description="Factor 2", impact="down", source_url="https://example.com/2"
            ),
        ],
        sources=["https://example.com/1", "https://example.com/3"],  # #3 not in factors
        generated_at=datetime.now(UTC),
    )

    report = verify_analysis(analysis)

    assert report.passed is False
    assert any("not found in any factor" in issue for issue in report.issues)


def test_verify_analysis_reasoning_too_short():
    """Test verification fails when reasoning is too short."""
    analysis = AnalysisResult(
        ticker="TEST-24DEC31",
        market_prob=0.55,
        predicted_prob=60,
        confidence="low",
        reasoning="Too short",  # Less than 50 chars
        factors=[],
        sources=[],
        generated_at=datetime.now(UTC),
    )

    report = verify_analysis(analysis)

    assert report.passed is False
    assert any("Reasoning too short" in issue for issue in report.issues)


def test_verify_analysis_reasoning_too_long():
    """Test verification fails when reasoning is too long."""
    analysis = AnalysisResult(
        ticker="TEST-24DEC31",
        market_prob=0.55,
        predicted_prob=60,
        confidence="low",
        reasoning="A" * 2500,  # More than 2000 chars
        factors=[],
        sources=[],
        generated_at=datetime.now(UTC),
    )

    report = verify_analysis(analysis)

    assert report.passed is False
    assert any("Reasoning too long" in issue for issue in report.issues)


def test_verify_analysis_invalid_confidence():
    """Test verification fails for invalid confidence level."""
    # This should be caught by Pydantic, but test the verifier logic
    analysis = AnalysisResult(
        ticker="TEST-24DEC31",
        market_prob=0.55,
        predicted_prob=60,
        confidence="invalid",  # Not in {low, medium, high}
        reasoning="A" * 100,
        factors=[],
        sources=[],
        generated_at=datetime.now(UTC),
    )

    report = verify_analysis(analysis)

    assert report.passed is False
    assert any("Invalid confidence level" in issue for issue in report.issues)


def test_verify_analysis_predicted_equals_market_high_confidence():
    """Test verification flags when predicted equals market with high confidence."""
    analysis = AnalysisResult(
        ticker="TEST-24DEC31",
        market_prob=0.60,
        predicted_prob=60,  # Identical to market
        confidence="high",
        reasoning="A" * 100,
        factors=[
            AnalysisFactor(description="Factor 1", impact="up", source_url="https://example.com/1"),
            AnalysisFactor(
                description="Factor 2", impact="down", source_url="https://example.com/2"
            ),
            AnalysisFactor(
                description="Factor 3", impact="unclear", source_url="https://example.com/3"
            ),
        ],
        sources=["https://example.com/1", "https://example.com/2", "https://example.com/3"],
        generated_at=datetime.now(UTC),
    )

    report = verify_analysis(analysis)

    assert report.passed is False
    assert any("identical to market" in issue for issue in report.issues)


def test_verify_analysis_invalid_impact():
    """Test verification fails for invalid impact values."""
    analysis = AnalysisResult(
        ticker="TEST-24DEC31",
        market_prob=0.55,
        predicted_prob=60,
        confidence="medium",
        reasoning="A" * 100,
        factors=[
            AnalysisFactor(
                description="Factor 1", impact="invalid", source_url="https://example.com/1"
            ),
            AnalysisFactor(
                description="Factor 2", impact="down", source_url="https://example.com/2"
            ),
        ],
        sources=["https://example.com/1", "https://example.com/2"],
        generated_at=datetime.now(UTC),
    )

    report = verify_analysis(analysis)

    assert report.passed is False
    assert any("invalid impact value" in issue for issue in report.issues)


def test_verify_analysis_prob_out_of_range():
    """Test that Pydantic catches out-of-range probabilities."""
    # predicted_prob out of range should be caught by Pydantic schema
    with pytest.raises(ValueError):
        AnalysisResult(
            ticker="TEST-24DEC31",
            market_prob=0.55,
            predicted_prob=150,  # Out of range
            confidence="low",
            reasoning="A" * 100,
            factors=[],
            sources=[],
            generated_at=datetime.now(UTC),
        )


def test_verify_analysis_multiple_issues():
    """Test verification collects multiple issues."""
    analysis = AnalysisResult(
        ticker="TEST-24DEC31",
        market_prob=0.55,
        predicted_prob=60,
        confidence="high",  # Requires 3 citations
        reasoning="Too short",  # Less than 50 chars
        factors=[
            AnalysisFactor(description="Factor 1", impact="up", source_url="https://example.com/1")
        ],
        sources=["https://example.com/1", "https://example.com/1"],  # Duplicate + insufficient
        generated_at=datetime.now(UTC),
    )

    report = verify_analysis(analysis)

    assert report.passed is False
    assert len(report.issues) >= 3  # Should have multiple issues
    assert report.suggested_escalation is True
