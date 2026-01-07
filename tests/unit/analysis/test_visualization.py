"""Unit tests for visualization functions."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.figure import Figure

from kalshi_research.analysis.calibration import CalibrationResult
from kalshi_research.analysis.edge import Edge
from kalshi_research.analysis.metrics import VolumeProfile
from kalshi_research.analysis.visualization import (
    plot_calibration_curve,
    plot_edge_histogram,
    plot_probability_timeline,
    plot_spread_timeline,
    plot_volume_profile,
)
from kalshi_research.data.models import PriceSnapshot


@pytest.fixture
def sample_snapshots() -> list[PriceSnapshot]:
    """Create sample price snapshots for testing."""
    base_time = datetime(2025, 1, 1, tzinfo=UTC)
    snapshots = []

    for i in range(20):
        snap = PriceSnapshot(
            id=i + 1,
            ticker="TEST-25JAN-T50",
            snapshot_time=base_time + timedelta(hours=i),
            yes_bid=45 + i,
            yes_ask=47 + i,
            no_bid=53 - i,
            no_ask=55 - i,
            last_price=46 + i,
            volume=100 + i * 10,
            volume_24h=50 + i * 5,
            open_interest=100,
            liquidity=10000,
        )
        snapshots.append(snap)

    return snapshots


@pytest.fixture
def sample_calibration_result() -> CalibrationResult:
    """Create sample calibration result for testing."""
    return CalibrationResult(
        brier_score=0.05,
        brier_skill_score=0.10,
        n_samples=90,
        bins=np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0]),
        predicted_probs=np.array([0.1, 0.3, 0.5, 0.7, 0.9]),
        actual_freqs=np.array([0.12, 0.28, 0.52, 0.68, 0.88]),
        bin_counts=np.array([10, 20, 30, 20, 10]),
        reliability=0.02,
        resolution=0.03,
        uncertainty=0.25,
    )


@pytest.fixture
def sample_edges() -> list[Edge]:
    """Create sample edges for testing."""
    from kalshi_research.analysis.edge import EdgeType

    return [
        Edge(
            ticker="TEST-1",
            edge_type=EdgeType.THESIS,
            confidence=0.8,
            market_price=0.45,
            your_estimate=0.60,
            expected_value=15.0,
            description="Market underpriced",
        ),
        Edge(
            ticker="TEST-2",
            edge_type=EdgeType.SPREAD,
            confidence=0.6,
            market_price=0.70,
            your_estimate=0.55,
            expected_value=-15.0,
            description="Wide spread opportunity",
        ),
        Edge(
            ticker="TEST-3",
            edge_type=EdgeType.VOLUME,
            confidence=0.7,
            market_price=0.50,
            your_estimate=0.65,
            expected_value=15.0,
            description="Volume spike detected",
        ),
    ]


@pytest.fixture
def sample_volume_profile() -> VolumeProfile:
    """Create sample volume profile for testing."""
    return VolumeProfile(
        ticker="TEST-25JAN-T50",
        hourly_volume={i: float(i * 100 + 500) for i in range(24)},
        daily_volume={
            "Mon": 10000.0,
            "Tue": 12000.0,
            "Wed": 11000.0,
            "Thu": 13000.0,
            "Fri": 15000.0,
            "Sat": 5000.0,
            "Sun": 4000.0,
        },
        total_volume=100000,
        period_days=7,
    )


class TestPlotCalibrationCurve:
    """Tests for plot_calibration_curve function."""

    def test_plot_calibration_curve_basic(
        self, sample_calibration_result: CalibrationResult
    ) -> None:
        """Test basic calibration curve plotting."""
        fig = plot_calibration_curve(sample_calibration_result)

        assert isinstance(fig, Figure)
        assert len(fig.axes) == 1

        # Close figure to free memory
        plt.close(fig)

    def test_plot_calibration_curve_with_title(
        self, sample_calibration_result: CalibrationResult
    ) -> None:
        """Test calibration curve with custom title."""
        fig = plot_calibration_curve(sample_calibration_result, title="Custom Title")

        assert isinstance(fig, Figure)
        ax = fig.axes[0]
        assert "Custom Title" in ax.get_title()

        plt.close(fig)

    def test_plot_calibration_curve_save(
        self, sample_calibration_result: CalibrationResult, tmp_path: Path
    ) -> None:
        """Test saving calibration curve to file."""
        output_path = tmp_path / "calibration.png"

        fig = plot_calibration_curve(sample_calibration_result, save_path=output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        plt.close(fig)


class TestPlotProbabilityTimeline:
    """Tests for plot_probability_timeline function."""

    def test_plot_probability_timeline_basic(self, sample_snapshots: list[PriceSnapshot]) -> None:
        """Test basic probability timeline plotting."""
        fig = plot_probability_timeline(sample_snapshots)

        assert isinstance(fig, Figure)
        assert len(fig.axes) == 1

        plt.close(fig)

    def test_plot_probability_timeline_empty(self) -> None:
        """Test probability timeline with empty data."""
        with pytest.raises(ValueError, match="No snapshots provided"):
            plot_probability_timeline([])

    def test_plot_probability_timeline_custom_title(
        self, sample_snapshots: list[PriceSnapshot]
    ) -> None:
        """Test probability timeline with custom title."""
        fig = plot_probability_timeline(sample_snapshots, title="Custom Timeline")

        ax = fig.axes[0]
        assert "Custom Timeline" in ax.get_title()

        plt.close(fig)

    def test_plot_probability_timeline_save(
        self, sample_snapshots: list[PriceSnapshot], tmp_path: Path
    ) -> None:
        """Test saving probability timeline to file."""
        output_path = tmp_path / "timeline.png"

        fig = plot_probability_timeline(sample_snapshots, save_path=output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        plt.close(fig)


class TestPlotEdgeHistogram:
    """Tests for plot_edge_histogram function."""

    def test_plot_edge_histogram_basic(self, sample_edges: list[Edge]) -> None:
        """Test basic edge histogram plotting."""
        fig = plot_edge_histogram(sample_edges)

        assert isinstance(fig, Figure)
        assert len(fig.axes) == 1

        plt.close(fig)

    def test_plot_edge_histogram_empty(self) -> None:
        """Test edge histogram with empty data."""
        with pytest.raises(ValueError, match="No edges provided"):
            plot_edge_histogram([])

    def test_plot_edge_histogram_no_estimates(self) -> None:
        """Test edge histogram with edges missing estimates."""
        from kalshi_research.analysis.edge import EdgeType

        edges = [
            Edge(
                ticker="TEST",
                edge_type=EdgeType.THESIS,
                confidence=0.5,
                market_price=0.5,
                your_estimate=None,
                expected_value=None,
                description="No estimate",
            )
        ]

        with pytest.raises(ValueError, match="No edges with estimates"):
            plot_edge_histogram(edges)

    def test_plot_edge_histogram_save(self, sample_edges: list[Edge], tmp_path: Path) -> None:
        """Test saving edge histogram to file."""
        output_path = tmp_path / "edges.png"

        fig = plot_edge_histogram(sample_edges, save_path=output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        plt.close(fig)


class TestPlotSpreadTimeline:
    """Tests for plot_spread_timeline function."""

    def test_plot_spread_timeline_basic(self, sample_snapshots: list[PriceSnapshot]) -> None:
        """Test basic spread timeline plotting."""
        fig = plot_spread_timeline(sample_snapshots)

        assert isinstance(fig, Figure)
        assert len(fig.axes) == 1

        plt.close(fig)

    def test_plot_spread_timeline_empty(self) -> None:
        """Test spread timeline with empty data."""
        with pytest.raises(ValueError, match="No snapshots provided"):
            plot_spread_timeline([])

    def test_plot_spread_timeline_save(
        self, sample_snapshots: list[PriceSnapshot], tmp_path: Path
    ) -> None:
        """Test saving spread timeline to file."""
        output_path = tmp_path / "spread.png"

        fig = plot_spread_timeline(sample_snapshots, save_path=output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        plt.close(fig)


class TestPlotVolumeProfile:
    """Tests for plot_volume_profile function."""

    def test_plot_volume_profile_basic(self, sample_volume_profile: VolumeProfile) -> None:
        """Test basic volume profile plotting."""
        fig = plot_volume_profile(sample_volume_profile)

        assert isinstance(fig, Figure)
        assert len(fig.axes) == 2  # Two subplots

        plt.close(fig)

    def test_plot_volume_profile_custom_title(self, sample_volume_profile: VolumeProfile) -> None:
        """Test volume profile with custom title."""
        fig = plot_volume_profile(sample_volume_profile, title="Custom Volume")

        # Check suptitle (figure title)
        assert "Custom Volume" in fig._suptitle.get_text()

        plt.close(fig)

    def test_plot_volume_profile_save(
        self, sample_volume_profile: VolumeProfile, tmp_path: Path
    ) -> None:
        """Test saving volume profile to file."""
        output_path = tmp_path / "volume.png"

        fig = plot_volume_profile(sample_volume_profile, save_path=output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        plt.close(fig)
