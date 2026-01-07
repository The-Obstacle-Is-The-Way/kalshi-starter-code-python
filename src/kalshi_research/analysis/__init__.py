"""Analysis tools for prediction market research."""

from kalshi_research.analysis.calibration import CalibrationAnalyzer, CalibrationResult
from kalshi_research.analysis.edge import Edge, EdgeDetector, EdgeType
from kalshi_research.analysis.metrics import (
    MarketMetrics,
    SpreadStats,
    VolatilityStats,
    VolumeProfile,
)
from kalshi_research.analysis.scanner import MarketScanner, ScanResult
from kalshi_research.analysis.visualization import (
    plot_calibration_curve,
    plot_edge_histogram,
    plot_probability_timeline,
    plot_spread_timeline,
    plot_volume_profile,
)

__all__ = [
    "CalibrationAnalyzer",
    "CalibrationResult",
    "Edge",
    "EdgeDetector",
    "EdgeType",
    "MarketMetrics",
    "MarketScanner",
    "ScanResult",
    "SpreadStats",
    "VolatilityStats",
    "VolumeProfile",
    "plot_calibration_curve",
    "plot_edge_histogram",
    "plot_probability_timeline",
    "plot_spread_timeline",
    "plot_volume_profile",
]
