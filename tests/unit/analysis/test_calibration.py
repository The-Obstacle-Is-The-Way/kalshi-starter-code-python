"""
Tests for calibration analysis - uses REAL numpy arrays.
"""

from __future__ import annotations

import numpy as np
import pytest

from kalshi_research.analysis.calibration import CalibrationAnalyzer, CalibrationResult


class TestBrierScore:
    """Test Brier score calculation."""

    def test_perfect_predictions(self) -> None:
        """Perfect predictions give Brier score of 0."""
        analyzer = CalibrationAnalyzer()

        # Perfect predictions
        forecasts = [1.0, 0.0, 1.0, 0.0]
        outcomes = [1, 0, 1, 0]

        score = analyzer.compute_brier_score(forecasts, outcomes)
        assert score == 0.0

    def test_worst_predictions(self) -> None:
        """Worst predictions give Brier score of 1."""
        analyzer = CalibrationAnalyzer()

        # Completely wrong
        forecasts = [0.0, 1.0, 0.0, 1.0]
        outcomes = [1, 0, 1, 0]

        score = analyzer.compute_brier_score(forecasts, outcomes)
        assert score == 1.0

    def test_uncertain_predictions(self) -> None:
        """50/50 predictions give Brier score of 0.25."""
        analyzer = CalibrationAnalyzer()

        forecasts = [0.5, 0.5, 0.5, 0.5]
        outcomes = [1, 0, 1, 0]

        score = analyzer.compute_brier_score(forecasts, outcomes)
        assert score == pytest.approx(0.25)

    def test_accepts_numpy_arrays(self) -> None:
        """Works with numpy arrays."""
        analyzer = CalibrationAnalyzer()

        forecasts = np.array([0.7, 0.3])
        outcomes = np.array([1, 0])

        score = analyzer.compute_brier_score(forecasts, outcomes)
        # (0.7-1)^2 + (0.3-0)^2 / 2 = 0.09 + 0.09 / 2 = 0.09
        assert score == pytest.approx(0.09)


class TestCalibrationAnalysis:
    """Test full calibration analysis."""

    def test_calibration_result_structure(self) -> None:
        """CalibrationResult has all expected fields."""
        analyzer = CalibrationAnalyzer(n_bins=5)

        forecasts = [0.1, 0.3, 0.5, 0.7, 0.9]
        outcomes = [0, 0, 1, 1, 1]

        result = analyzer.compute_calibration(forecasts, outcomes)

        assert isinstance(result, CalibrationResult)
        assert result.n_samples == 5
        assert 0 <= result.brier_score <= 1
        assert len(result.bins) == 6  # n_bins + 1 edges
        assert len(result.predicted_probs) == 5
        assert len(result.actual_freqs) == 5
        assert len(result.bin_counts) == 5

    def test_brier_decomposition(self) -> None:
        """Brier = Reliability - Resolution + Uncertainty."""
        analyzer = CalibrationAnalyzer(n_bins=10)

        # Many samples for stable estimates
        np.random.seed(42)
        forecasts = np.random.uniform(0.2, 0.8, 100)
        outcomes = (np.random.random(100) < forecasts).astype(int)

        result = analyzer.compute_calibration(forecasts, outcomes)

        # Verify decomposition (approximately)
        # Brier ≈ Reliability - Resolution + Uncertainty
        decomposed = result.reliability - result.resolution + result.uncertainty
        assert result.brier_score == pytest.approx(decomposed, rel=0.1)

    def test_skill_score_range(self) -> None:
        """Skill score should be -inf to 1."""
        analyzer = CalibrationAnalyzer()

        # Good forecaster
        forecasts = [0.8, 0.2, 0.9, 0.1]
        outcomes = [1, 0, 1, 0]

        result = analyzer.compute_calibration(forecasts, outcomes)
        assert result.brier_skill_score <= 1.0

    def test_perfectly_calibrated(self) -> None:
        """Reliability should be low for calibrated forecasts."""
        analyzer = CalibrationAnalyzer(n_bins=5)

        # Perfectly calibrated: each forecast matches outcome frequency
        forecasts = [0.2] * 5 + [0.8] * 5
        # 1/5 YES at 20%, 4/5 YES at 80%
        outcomes = [1, 0, 0, 0, 0, 1, 1, 1, 1, 0]

        result = analyzer.compute_calibration(forecasts, outcomes)

        # Perfect calibration has reliability = 0
        assert result.reliability == pytest.approx(0.0, abs=0.05)

    def test_str_representation(self) -> None:
        """String representation is readable."""
        analyzer = CalibrationAnalyzer()
        forecasts = [0.5, 0.5]
        outcomes = [1, 0]

        result = analyzer.compute_calibration(forecasts, outcomes)
        string = str(result)

        assert "Calibration Results" in string
        assert "Brier Score" in string
        assert "Skill Score" in string


class TestCalibrationEdgeCases:
    """Test edge cases and error handling."""

    def test_single_sample(self) -> None:
        """Works with single sample."""
        analyzer = CalibrationAnalyzer()
        forecasts = [0.7]
        outcomes = [1]

        result = analyzer.compute_calibration(forecasts, outcomes)
        assert result.n_samples == 1
        # (0.7 - 1)^2 = 0.09
        assert result.brier_score == pytest.approx(0.09)

    def test_all_same_outcome(self) -> None:
        """Works when all outcomes are the same."""
        analyzer = CalibrationAnalyzer()
        forecasts = [0.3, 0.5, 0.7]
        outcomes = [1, 1, 1]  # All YES

        result = analyzer.compute_calibration(forecasts, outcomes)
        assert result.n_samples == 3
        # Base rate = 1.0, so uncertainty = 0
        assert result.uncertainty == 0.0

    def test_empty_bins(self) -> None:
        """Handles bins with no samples (NaN in those bins)."""
        analyzer = CalibrationAnalyzer(n_bins=10)

        # All forecasts in one range
        forecasts = [0.45, 0.46, 0.47, 0.48]
        outcomes = [0, 1, 0, 1]

        result = analyzer.compute_calibration(forecasts, outcomes)

        # Most bins should be NaN
        nan_count = np.sum(np.isnan(result.predicted_probs))
        assert nan_count > 5  # Most bins empty
