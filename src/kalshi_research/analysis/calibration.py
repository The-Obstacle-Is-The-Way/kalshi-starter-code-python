"""Calibration analysis for prediction markets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


@dataclass
class CalibrationResult:
    """Results from calibration analysis."""

    brier_score: float
    brier_skill_score: float  # vs climatology baseline
    n_samples: int

    # Calibration curve data
    bins: NDArray[np.floating[Any]]  # Probability bins
    predicted_probs: NDArray[np.floating[Any]]  # Mean predicted prob per bin
    actual_freqs: NDArray[np.floating[Any]]  # Actual YES frequency per bin
    bin_counts: NDArray[np.signedinteger[Any]]  # Samples per bin

    # Brier decomposition
    reliability: float  # Calibration error component
    resolution: float  # Discrimination ability
    uncertainty: float  # Base rate uncertainty

    def __str__(self) -> str:
        return (
            f"Calibration Results (n={self.n_samples}):\n"
            f"  Brier Score: {self.brier_score:.4f}\n"
            f"  Skill Score: {self.brier_skill_score:.4f}\n"
            f"  Reliability: {self.reliability:.4f}\n"
            f"  Resolution:  {self.resolution:.4f}"
        )


class CalibrationAnalyzer:
    """
    Analyze prediction market calibration.

    A perfectly calibrated forecaster assigns probabilities that match
    actual frequencies. If a market prices an event at 70%, and we look
    at all markets priced at 70%, exactly 70% should resolve YES.
    """

    def __init__(self, n_bins: int = 10) -> None:
        """
        Initialize the analyzer.

        Args:
            n_bins: Number of bins for calibration curve (default: 10)
        """
        self.n_bins = n_bins

    def compute_brier_score(
        self,
        forecasts: NDArray[np.floating[Any]] | list[float],
        outcomes: NDArray[np.floating[Any]] | list[int],
    ) -> float:
        """
        Compute Brier score for forecasts.

        Brier Score = (1/N) * Σ(forecast - outcome)²

        Args:
            forecasts: Predicted probabilities (0-1)
            outcomes: Actual outcomes (0 or 1)

        Returns:
            Brier score (lower is better, 0 = perfect)
        """
        f = np.asarray(forecasts, dtype=np.float64)
        o = np.asarray(outcomes, dtype=np.float64)
        return float(np.mean((f - o) ** 2))

    def compute_calibration(
        self,
        forecasts: NDArray[np.floating[Any]] | list[float],
        outcomes: NDArray[np.floating[Any]] | list[int],
    ) -> CalibrationResult:
        """
        Full calibration analysis with Brier decomposition.

        The Brier score can be decomposed into:
        - Reliability: How well probabilities match actual frequencies
        - Resolution: How much probabilities vary from base rate
        - Uncertainty: Inherent unpredictability (base_rate * (1 - base_rate))

        Brier = Reliability - Resolution + Uncertainty

        Args:
            forecasts: Predicted probabilities (0-1)
            outcomes: Actual outcomes (0 or 1)

        Returns:
            CalibrationResult with all metrics
        """
        f = np.asarray(forecasts, dtype=np.float64)
        o = np.asarray(outcomes, dtype=np.float64)
        n = len(f)
        base_rate = float(np.mean(o))

        # Brier score
        brier = self.compute_brier_score(f, o)

        # Climatology baseline (always predict base rate)
        climatology_brier = base_rate * (1 - base_rate)
        skill_score = 1 - (brier / climatology_brier) if climatology_brier > 0 else 0.0

        # Bin forecasts for calibration curve
        bin_edges = np.linspace(0, 1, self.n_bins + 1)
        bin_indices = np.digitize(f, bin_edges[1:-1])

        predicted_probs = np.full(self.n_bins, np.nan)
        actual_freqs = np.full(self.n_bins, np.nan)
        bin_counts = np.zeros(self.n_bins, dtype=np.int64)

        for i in range(self.n_bins):
            mask = bin_indices == i
            count = int(np.sum(mask))
            bin_counts[i] = count

            if count > 0:
                predicted_probs[i] = float(np.mean(f[mask]))
                actual_freqs[i] = float(np.mean(o[mask]))

        # Brier decomposition
        reliability = 0.0
        resolution = 0.0
        for i in range(self.n_bins):
            if bin_counts[i] > 0:
                reliability += bin_counts[i] * (actual_freqs[i] - predicted_probs[i]) ** 2
                resolution += bin_counts[i] * (actual_freqs[i] - base_rate) ** 2
        reliability /= n
        resolution /= n

        uncertainty = base_rate * (1 - base_rate)

        return CalibrationResult(
            brier_score=brier,
            brier_skill_score=float(skill_score),
            n_samples=n,
            bins=bin_edges,
            predicted_probs=predicted_probs,
            actual_freqs=actual_freqs,
            bin_counts=bin_counts,
            reliability=reliability,
            resolution=resolution,
            uncertainty=uncertainty,
        )
