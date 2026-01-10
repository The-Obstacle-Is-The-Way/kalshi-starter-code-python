"""
Tests for research thesis framework - uses REAL objects.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from kalshi_research.api.models.market import Market, MarketStatus
from kalshi_research.research.thesis import (
    TemporalValidator,
    Thesis,
    ThesisEvidence,
    ThesisStatus,
    ThesisTracker,
)


class TestThesis:
    """Test Thesis dataclass."""

    def test_thesis_creation(self) -> None:
        """Can create a thesis with all fields."""
        thesis = Thesis(
            id="test-1",
            title="BTC above 100k",
            market_tickers=["KXBTC-25JAN-T100000"],
            your_probability=0.60,
            market_probability=0.45,
            confidence=0.75,
            bull_case="Institutional adoption increasing",
            bear_case="Regulatory concerns",
            key_assumptions=["No major exchange hacks"],
            invalidation_criteria=["BTC drops below 80k"],
        )

        assert thesis.id == "test-1"
        assert thesis.status == ThesisStatus.DRAFT
        assert thesis.your_probability == 0.60

    def test_edge_size_calculation(self) -> None:
        """Edge size is your prob minus market prob."""
        thesis = Thesis(
            id="test",
            title="Test",
            market_tickers=["TEST"],
            your_probability=0.70,
            market_probability=0.50,
            confidence=0.8,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
        )

        assert thesis.edge_size == pytest.approx(0.20)

    def test_was_correct_yes_outcome(self) -> None:
        """Correctly identifies correct YES predictions."""
        thesis = Thesis(
            id="test",
            title="Test",
            market_tickers=["TEST"],
            your_probability=0.70,  # Bullish
            market_probability=0.50,
            confidence=0.8,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
        )
        thesis.actual_outcome = "yes"

        assert thesis.was_correct is True

    def test_was_correct_no_outcome(self) -> None:
        """Correctly identifies correct NO predictions."""
        thesis = Thesis(
            id="test",
            title="Test",
            market_tickers=["TEST"],
            your_probability=0.30,  # Bearish
            market_probability=0.50,
            confidence=0.8,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
        )
        thesis.actual_outcome = "no"

        assert thesis.was_correct is True

    def test_was_correct_wrong_prediction(self) -> None:
        """Correctly identifies wrong predictions."""
        thesis = Thesis(
            id="test",
            title="Test",
            market_tickers=["TEST"],
            your_probability=0.80,  # Very bullish
            market_probability=0.50,
            confidence=0.8,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
        )
        thesis.actual_outcome = "no"  # But resolved NO

        assert thesis.was_correct is False

    def test_was_correct_unresolved(self) -> None:
        """Returns None for unresolved thesis."""
        thesis = Thesis(
            id="test",
            title="Test",
            market_tickers=["TEST"],
            your_probability=0.70,
            market_probability=0.50,
            confidence=0.8,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
        )

        assert thesis.was_correct is None

    def test_brier_score_calculation(self) -> None:
        """Brier score calculated correctly."""
        thesis = Thesis(
            id="test",
            title="Test",
            market_tickers=["TEST"],
            your_probability=0.70,
            market_probability=0.50,
            confidence=0.8,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
        )
        thesis.actual_outcome = "yes"

        # Brier = (0.70 - 1.0)^2 = 0.09
        assert thesis.brier_score == pytest.approx(0.09)

    def test_resolve_thesis(self) -> None:
        """Resolve sets status and outcome."""
        thesis = Thesis(
            id="test",
            title="Test",
            market_tickers=["TEST"],
            your_probability=0.70,
            market_probability=0.50,
            confidence=0.8,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
        )

        thesis.resolve("yes")

        assert thesis.status == ThesisStatus.RESOLVED
        assert thesis.actual_outcome == "yes"
        assert thesis.resolved_at is not None

    def test_add_update(self) -> None:
        """Can add timestamped updates."""
        thesis = Thesis(
            id="test",
            title="Test",
            market_tickers=["TEST"],
            your_probability=0.70,
            market_probability=0.50,
            confidence=0.8,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
        )

        thesis.add_update("Price moved to 55%")

        assert len(thesis.updates) == 1
        assert "Price moved to 55%" in thesis.updates[0]["note"]
        assert "timestamp" in thesis.updates[0]

    def test_serialization_roundtrip(self) -> None:
        """Can serialize and deserialize thesis."""
        original = Thesis(
            id="test",
            title="Test",
            market_tickers=["TEST1", "TEST2"],
            your_probability=0.70,
            market_probability=0.50,
            confidence=0.8,
            bull_case="Bull",
            bear_case="Bear",
            key_assumptions=["A1", "A2"],
            invalidation_criteria=["I1"],
        )
        original.add_update("Update 1")

        data = original.to_dict()
        restored = Thesis.from_dict(data)

        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.market_tickers == original.market_tickers
        assert restored.your_probability == original.your_probability
        assert len(restored.updates) == 1
        assert restored.evidence == []

    def test_serialization_roundtrip_with_evidence(self) -> None:
        original = Thesis(
            id="test",
            title="Test",
            market_tickers=["TEST1"],
            your_probability=0.70,
            market_probability=0.50,
            confidence=0.8,
            bull_case="Bull",
            bear_case="Bear",
            key_assumptions=[],
            invalidation_criteria=[],
        )
        original.evidence.append(
            ThesisEvidence(
                url="https://example.com",
                title="Example",
                source_domain="example.com",
                published_date=None,
                snippet="Snippet",
                supports="bull",
                relevance_score=0.9,
            )
        )
        original.research_summary = "Summary"

        data = original.to_dict()
        restored = Thesis.from_dict(data)

        assert restored.research_summary == "Summary"
        assert len(restored.evidence) == 1
        assert restored.evidence[0].supports == "bull"

    def test_from_dict_is_backward_compatible_with_missing_fields(self) -> None:
        thesis = Thesis.from_dict(
            {
                "id": "test",
                "title": "Test",
                "market_tickers": ["TEST"],
                "your_probability": 0.7,
                "market_probability": 0.5,
                "confidence": 0.8,
                "bull_case": "Bull",
                "bear_case": "Bear",
                "status": "draft",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        )

        assert thesis.key_assumptions == []
        assert thesis.invalidation_criteria == []
        assert thesis.evidence == []
        assert thesis.research_summary is None

    def test_str_representation(self) -> None:
        """String representation is readable."""
        thesis = Thesis(
            id="test",
            title="Test Market Thesis",
            market_tickers=["TEST"],
            your_probability=0.70,
            market_probability=0.50,
            confidence=0.8,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
        )

        string = str(thesis)
        assert "DRAFT" in string
        assert "Test Market Thesis" in string
        assert "70%" in string
        assert "50%" in string


class TestThesisTracker:
    """Test ThesisTracker persistence."""

    @pytest.fixture
    def temp_path(self) -> Path:
        """Create a temporary file path."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        # Delete the file so tracker starts fresh
        path.unlink()
        return path

    def test_add_and_get(self, temp_path: Path) -> None:
        """Can add and retrieve thesis."""
        tracker = ThesisTracker(temp_path)

        thesis = Thesis(
            id="test-1",
            title="Test",
            market_tickers=["TEST"],
            your_probability=0.70,
            market_probability=0.50,
            confidence=0.8,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
        )
        tracker.add(thesis)

        retrieved = tracker.get("test-1")
        assert retrieved is not None
        assert retrieved.title == "Test"

    def test_load_invalid_json_raises(self, temp_path: Path) -> None:
        """Invalid JSON should fail loudly (no silent empty fallback)."""
        temp_path.write_text("{not json", encoding="utf-8")

        with pytest.raises(ValueError, match="not valid JSON"):
            ThesisTracker(temp_path)

    def test_load_unexpected_schema_raises(self, temp_path: Path) -> None:
        """Unexpected schema should fail loudly to avoid data loss on next save."""
        temp_path.write_text('{"conditions": []}', encoding="utf-8")

        with pytest.raises(ValueError, match="unexpected schema"):
            ThesisTracker(temp_path)

    def test_persistence(self, temp_path: Path) -> None:
        """Theses persist to disk."""
        # Create and save
        tracker1 = ThesisTracker(temp_path)
        thesis = Thesis(
            id="persist-test",
            title="Persistent",
            market_tickers=["TEST"],
            your_probability=0.70,
            market_probability=0.50,
            confidence=0.8,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
        )
        tracker1.add(thesis)

        # Load in new tracker
        tracker2 = ThesisTracker(temp_path)
        retrieved = tracker2.get("persist-test")

        assert retrieved is not None
        assert retrieved.title == "Persistent"

    def test_list_by_status(self, temp_path: Path) -> None:
        """Can list theses by status."""
        tracker = ThesisTracker(temp_path)

        # Add theses with different statuses
        for i, status in enumerate([ThesisStatus.DRAFT, ThesisStatus.ACTIVE, ThesisStatus.ACTIVE]):
            thesis = Thesis(
                id=f"test-{i}",
                title=f"Test {i}",
                market_tickers=["TEST"],
                your_probability=0.70,
                market_probability=0.50,
                confidence=0.8,
                bull_case="",
                bear_case="",
                key_assumptions=[],
                invalidation_criteria=[],
                status=status,
            )
            tracker.add(thesis)

        active = tracker.list_active()
        assert len(active) == 2

    def test_performance_summary_empty(self, temp_path: Path) -> None:
        """Performance summary handles empty tracker."""
        tracker = ThesisTracker(temp_path)
        summary = tracker.performance_summary()

        assert summary["total_resolved"] == 0
        assert summary["accuracy"] is None

    def test_performance_summary_with_data(self, temp_path: Path) -> None:
        """Performance summary calculates metrics."""
        tracker = ThesisTracker(temp_path)

        # Add resolved theses
        for i, (prob, outcome) in enumerate([(0.70, "yes"), (0.30, "no"), (0.80, "no")]):
            thesis = Thesis(
                id=f"test-{i}",
                title=f"Test {i}",
                market_tickers=["TEST"],
                your_probability=prob,
                market_probability=0.50,
                confidence=0.8,
                bull_case="",
                bear_case="",
                key_assumptions=[],
                invalidation_criteria=[],
            )
            thesis.resolve(outcome)
            tracker.add(thesis)

        summary = tracker.performance_summary()

        assert summary["total_resolved"] == 3
        assert summary["correct_predictions"] == 2  # First two correct
        assert summary["accuracy"] == pytest.approx(2 / 3)

    def test_remove_thesis(self, temp_path: Path) -> None:
        """Can remove thesis."""
        tracker = ThesisTracker(temp_path)
        thesis = Thesis(
            id="to-remove",
            title="Remove Me",
            market_tickers=["TEST"],
            your_probability=0.70,
            market_probability=0.50,
            confidence=0.8,
            bull_case="",
            bear_case="",
            key_assumptions=[],
            invalidation_criteria=[],
        )
        tracker.add(thesis)
        tracker.remove("to-remove")

        assert tracker.get("to-remove") is None


class TestTemporalValidator:
    """Test temporal validation for research workflow."""

    def _make_market(self, open_time: datetime) -> Market:
        """Helper to create a market with specific open time."""
        return Market(
            ticker="KXTEST-01JAN01",
            event_ticker="KXTEST",
            title="Test market",
            status=MarketStatus.ACTIVE,
            open_time=open_time,
            close_time=datetime(2027, 1, 1, tzinfo=UTC),
            expiration_time=datetime(2027, 1, 1, tzinfo=UTC),
            volume=1000,
            volume_24h=100,
            open_interest=500,
        )

    def test_event_after_market_opens_is_valid(self) -> None:
        """Event occurring after market opens is valid."""
        market = self._make_market(open_time=datetime(2026, 1, 5, 20, 0, 0, tzinfo=UTC))
        event_date = datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)

        validator = TemporalValidator()
        result = validator.validate(market=market, event_date=event_date)

        assert result.valid is True
        assert result.warning is None

    def test_event_before_market_opens_is_invalid(self) -> None:
        """Event occurring before market opens triggers warning."""
        market = self._make_market(open_time=datetime(2026, 1, 5, 20, 0, 0, tzinfo=UTC))
        event_date = datetime(2025, 12, 31, 12, 0, 0, tzinfo=UTC)

        validator = TemporalValidator()
        result = validator.validate(market=market, event_date=event_date)

        assert result.valid is False
        assert result.warning is not None
        assert "predates market open" in result.warning
        assert "2025-12-31" in result.warning
        assert "2026-01-05" in result.warning

    def test_event_same_time_as_market_opens_is_valid(self) -> None:
        """Event at exact market open time is considered valid."""
        open_time = datetime(2026, 1, 5, 20, 0, 0, tzinfo=UTC)
        market = self._make_market(open_time=open_time)
        event_date = open_time

        validator = TemporalValidator()
        result = validator.validate(market=market, event_date=event_date)

        assert result.valid is True
        assert result.warning is None

    def test_naive_event_date_is_invalid(self) -> None:
        """Naive datetimes fail safely instead of raising during comparisons."""
        market = self._make_market(open_time=datetime(2026, 1, 5, 20, 0, 0, tzinfo=UTC))
        event_date = datetime(2026, 1, 10, 12, 0, 0)  # naive

        validator = TemporalValidator()
        result = validator.validate(market=market, event_date=event_date)

        assert result.valid is False
        assert result.warning is not None
        assert "Cannot compare naive and aware datetimes" in result.warning

    def test_stranger_things_scenario(self) -> None:
        """Test the actual Stranger Things market scenario from TODO-005."""
        # Market opened Jan 5, 2026
        market = self._make_market(open_time=datetime(2026, 1, 5, 20, 0, 0, tzinfo=UTC))
        # S5 finale was Dec 31, 2025
        s5_finale_date = datetime(2025, 12, 31, 23, 59, 0, tzinfo=UTC)

        validator = TemporalValidator()
        result = validator.validate(market=market, event_date=s5_finale_date)

        # This should flag as invalid - S5 doesn't count!
        assert result.valid is False
        assert result.warning is not None
        assert "predates market open" in result.warning
