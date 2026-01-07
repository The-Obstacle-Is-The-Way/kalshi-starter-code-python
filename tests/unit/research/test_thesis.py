"""
Tests for research thesis framework - uses REAL objects.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from kalshi_research.research.thesis import Thesis, ThesisStatus, ThesisTracker


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
