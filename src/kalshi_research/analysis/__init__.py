"""Analysis tools for prediction market research."""

from kalshi_research.analysis.calibration import CalibrationAnalyzer, CalibrationResult
from kalshi_research.analysis.edge import Edge, EdgeType
from kalshi_research.analysis.liquidity import (
    DepthAnalysis,
    ExecutionWindow,
    LiquidityAnalysis,
    LiquidityError,
    LiquidityGrade,
    LiquidityWeights,
    OrderbookAnalyzer,
    SlippageEstimate,
    enforce_max_slippage,
    estimate_price_impact,
    estimate_slippage,
    liquidity_score,
    max_safe_order_size,
    orderbook_depth_score,
    suggest_execution_timing,
)
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
    "DepthAnalysis",
    "Edge",
    "EdgeType",
    "ExecutionWindow",
    "LiquidityAnalysis",
    "LiquidityError",
    "LiquidityGrade",
    "LiquidityWeights",
    "MarketMetrics",
    "MarketScanner",
    "OrderbookAnalyzer",
    "ScanResult",
    "SlippageEstimate",
    "SpreadStats",
    "VolatilityStats",
    "VolumeProfile",
    "enforce_max_slippage",
    "estimate_price_impact",
    "estimate_slippage",
    "liquidity_score",
    "max_safe_order_size",
    "orderbook_depth_score",
    "plot_calibration_curve",
    "plot_edge_histogram",
    "plot_probability_timeline",
    "plot_spread_timeline",
    "plot_volume_profile",
    "suggest_execution_timing",
]
