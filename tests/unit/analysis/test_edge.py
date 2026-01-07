"""
Tests for edge detection - uses REAL objects.
"""

from __future__ import annotations

import pytest

from kalshi_research.analysis.edge import Edge, EdgeDetector, EdgeType


class TestEdge:
    """Test Edge dataclass."""

    def test_edge_str_with_estimate(self) -> None:
        """Edge string representation with estimate."""
        edge = Edge(
            ticker="TEST-MKT",
            edge_type=EdgeType.THESIS,
            confidence=0.8,
            market_price=0.35,
            your_estimate=0.55,
            expected_value=20.0,
            description="Buy YES",
        )

        string = str(edge)
        assert "THESIS" in string
        assert "TEST-MKT" in string
        assert "35%" in string
        assert "55%" in string
        assert "+20.0c" in string

    def test_edge_str_without_estimate(self) -> None:
        """Edge string representation without estimate."""
        edge = Edge(
            ticker="TEST-MKT",
            edge_type=EdgeType.SPREAD,
            confidence=0.5,
            market_price=0.50,
            your_estimate=None,
            expected_value=None,
            description="Wide spread",
        )

        string = str(edge)
        assert "N/A" in string


class TestThesisEdge:
    """Test thesis edge detection."""

    def test_detects_bullish_edge(self) -> None:
        """Detects when you're more bullish than market."""
        detector = EdgeDetector()

        edge = detector.detect_thesis_edge(
            ticker="TEST",
            market_prob=0.35,
            your_prob=0.55,
        )

        assert edge is not None
        assert edge.edge_type == EdgeType.THESIS
        assert edge.your_estimate == 0.55
        assert edge.market_price == 0.35
        assert edge.metadata["side"] == "YES"
        assert edge.expected_value is not None
        assert edge.expected_value > 0  # Positive EV

    def test_detects_bearish_edge(self) -> None:
        """Detects when you're more bearish than market."""
        detector = EdgeDetector()

        edge = detector.detect_thesis_edge(
            ticker="TEST",
            market_prob=0.70,
            your_prob=0.45,
        )

        assert edge is not None
        assert edge.metadata["side"] == "NO"

    def test_no_edge_when_small_diff(self) -> None:
        """No edge when difference is too small."""
        detector = EdgeDetector()

        edge = detector.detect_thesis_edge(
            ticker="TEST",
            market_prob=0.50,
            your_prob=0.52,  # Only 2% difference
            min_edge=0.05,
        )

        assert edge is None

    def test_confidence_scales_with_edge_size(self) -> None:
        """Confidence scales with edge magnitude."""
        detector = EdgeDetector()

        small_edge = detector.detect_thesis_edge("TEST", 0.50, 0.55)
        large_edge = detector.detect_thesis_edge("TEST", 0.50, 0.70)

        assert small_edge is not None
        assert large_edge is not None
        assert large_edge.confidence > small_edge.confidence

    def test_expected_value_calculation_yes(self) -> None:
        """EV calculation for YES position."""
        detector = EdgeDetector()

        edge = detector.detect_thesis_edge(
            ticker="TEST",
            market_prob=0.40,  # Cost = 40c
            your_prob=0.60,  # You think 60% chance
        )

        assert edge is not None
        # EV = (0.60 * 60c) - (0.40 * 40c) = 36c - 16c = 20c
        assert edge.expected_value == pytest.approx(20.0)


class TestSpreadEdge:
    """Test spread edge detection."""

    def test_detects_wide_spread(self) -> None:
        """Detects unusually wide spreads."""
        detector = EdgeDetector(min_spread_cents=5)

        edge = detector.detect_spread_edge(
            ticker="TEST",
            bid=45,
            ask=55,
            typical_spread=2,
        )

        assert edge is not None
        assert edge.edge_type == EdgeType.SPREAD
        assert edge.metadata["spread"] == 10

    def test_no_edge_for_tight_spread(self) -> None:
        """No edge for normal spreads."""
        detector = EdgeDetector(min_spread_cents=5)

        edge = detector.detect_spread_edge(
            ticker="TEST",
            bid=49,
            ask=51,
            typical_spread=2,
        )

        assert edge is None  # Spread is only 2

    def test_market_price_from_midpoint(self) -> None:
        """Market price calculated from bid-ask midpoint."""
        detector = EdgeDetector(min_spread_cents=5)

        edge = detector.detect_spread_edge("TEST", bid=40, ask=50)

        assert edge is not None
        assert edge.market_price == pytest.approx(0.45)  # (40+50)/200


class TestVolumeEdge:
    """Test volume edge detection."""

    def test_detects_volume_spike(self) -> None:
        """Detects volume spikes."""
        detector = EdgeDetector(min_volume_spike=3.0)

        edge = detector.detect_volume_edge(
            ticker="TEST",
            current_volume=15000,
            avg_volume=3000.0,
            market_prob=0.50,
        )

        assert edge is not None
        assert edge.edge_type == EdgeType.VOLUME
        assert edge.metadata["ratio"] == 5.0

    def test_no_edge_for_normal_volume(self) -> None:
        """No edge for normal volume."""
        detector = EdgeDetector(min_volume_spike=3.0)

        edge = detector.detect_volume_edge(
            ticker="TEST",
            current_volume=5000,
            avg_volume=3000.0,
            market_prob=0.50,
        )

        assert edge is None  # 1.67x is below threshold

    def test_handles_zero_avg_volume(self) -> None:
        """Handles zero average volume gracefully."""
        detector = EdgeDetector()

        edge = detector.detect_volume_edge(
            ticker="TEST",
            current_volume=1000,
            avg_volume=0.0,
            market_prob=0.50,
        )

        assert edge is None


class TestVolatilityEdge:
    """Test volatility edge detection."""

    def test_detects_large_move_up(self) -> None:
        """Detects large upward moves."""
        detector = EdgeDetector(min_price_move=0.10)

        edge = detector.detect_volatility_edge(
            ticker="TEST",
            price_change=0.15,
            market_prob=0.65,
        )

        assert edge is not None
        assert edge.edge_type == EdgeType.VOLATILITY
        assert edge.metadata["direction"] == "up"

    def test_detects_large_move_down(self) -> None:
        """Detects large downward moves."""
        detector = EdgeDetector(min_price_move=0.10)

        edge = detector.detect_volatility_edge(
            ticker="TEST",
            price_change=-0.20,
            market_prob=0.30,
        )

        assert edge is not None
        assert edge.metadata["direction"] == "down"

    def test_no_edge_for_small_move(self) -> None:
        """No edge for small price changes."""
        detector = EdgeDetector(min_price_move=0.10)

        edge = detector.detect_volatility_edge(
            ticker="TEST",
            price_change=0.05,
            market_prob=0.50,
        )

        assert edge is None
