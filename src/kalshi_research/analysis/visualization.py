"""Visualization tools for market analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    from matplotlib.figure import Figure

    from kalshi_research.analysis.calibration import CalibrationResult
    from kalshi_research.analysis.edge import Edge
    from kalshi_research.data.models import PriceSnapshot


def plot_calibration_curve(
    result: CalibrationResult,
    title: str = "Calibration Curve",
    save_path: Path | str | None = None,
) -> Figure:
    """
    Plot calibration curve showing predicted vs actual probabilities.

    Args:
        result: CalibrationResult from CalibrationAnalyzer
        title: Chart title
        save_path: Optional path to save figure

    Returns:
        Matplotlib Figure
    """
    fig, ax = plt.subplots(figsize=(8, 6))

    # Perfect calibration line
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Perfect calibration")

    # Filter valid bins
    valid = ~np.isnan(result.predicted_probs) & ~np.isnan(result.actual_freqs)
    predicted = result.predicted_probs[valid]
    actual = result.actual_freqs[valid]
    counts = result.bin_counts[valid]

    # Plot calibration curve with point sizes based on sample count
    sizes = np.sqrt(counts) * 5  # Scale for visibility
    scatter = ax.scatter(predicted, actual, s=sizes, c="blue", alpha=0.7, label="Observed")

    # Annotations
    ax.set_xlabel("Predicted Probability")
    ax.set_ylabel("Actual Frequency")
    ax.set_title(f"{title}\n(Brier Score: {result.brier_score:.4f}, n={result.n_samples})")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Add size legend
    def _size_to_samples(size: Any) -> Any:
        return (size / 5.0) ** 2

    handles, labels = scatter.legend_elements(
        prop="sizes",
        num=4,
        alpha=0.6,
        func=_size_to_samples,
    )
    ax.legend(handles, labels, title="Samples", loc="upper left")

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_probability_timeline(
    snapshots: Sequence[PriceSnapshot],
    title: str | None = None,
    save_path: Path | str | None = None,
) -> Figure:
    """
    Plot probability over time for a market.

    Args:
        snapshots: Price snapshots for a single market
        title: Chart title (defaults to ticker)
        save_path: Optional path to save figure

    Returns:
        Matplotlib Figure
    """
    if not snapshots:
        raise ValueError("No snapshots provided")

    # Sort by timestamp
    sorted_snaps = sorted(snapshots, key=lambda s: s.snapshot_time)
    ticker = sorted_snaps[0].ticker

    timestamps = [s.snapshot_time for s in sorted_snaps]
    # Convert midpoint to probability (0-1 scale)
    prices = [(s.yes_bid + s.yes_ask) / 200.0 for s in sorted_snaps]

    fig, ax = plt.subplots(figsize=(12, 6))

    timestamps_any: Any = timestamps
    ax.plot(timestamps_any, prices, "b-", linewidth=1.5)
    ax.fill_between(timestamps_any, prices, alpha=0.2)

    # Format x-axis
    date_formatter: Callable[[str], Any] = mdates.DateFormatter
    ax.xaxis.set_major_formatter(date_formatter("%m/%d"))
    auto_locator: Callable[[], Any] = mdates.AutoDateLocator
    ax.xaxis.set_major_locator(auto_locator())

    ax.set_xlabel("Date")
    ax.set_ylabel("Probability")
    ax.set_title(title or f"Probability Timeline: {ticker}")
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)

    plt.xticks(rotation=45)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_edge_histogram(
    edges: Sequence[Edge],
    title: str = "Edge Distribution",
    save_path: Path | str | None = None,
) -> Figure:
    """
    Plot histogram of detected edges.

    Args:
        edges: List of detected edges
        title: Chart title
        save_path: Optional path to save figure

    Returns:
        Matplotlib Figure
    """
    if not edges:
        raise ValueError("No edges provided")

    # Extract edge sizes (your estimate - market price)
    edge_sizes = [e.your_estimate - e.market_price for e in edges if e.your_estimate is not None]

    if not edge_sizes:
        raise ValueError("No edges with estimates")

    fig, ax = plt.subplots(figsize=(10, 6))

    # Histogram
    bins = np.linspace(-0.5, 0.5, 21)
    _n, bins_out, patches = ax.hist(edge_sizes, bins=bins.tolist(), edgecolor="black", alpha=0.7)

    # Color positive/negative differently
    for i, patch in enumerate(cast("list[Any]", patches)):
        if bins_out[i] >= 0:
            patch.set_facecolor("green")
        else:
            patch.set_facecolor("red")

    ax.axvline(0, color="black", linestyle="--", alpha=0.5)
    ax.set_xlabel("Edge Size (Your Estimate - Market)")
    ax.set_ylabel("Count")
    ax.set_title(f"{title}\n(n={len(edge_sizes)}, mean={np.mean(edge_sizes):.1%})")
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_spread_timeline(
    snapshots: Sequence[PriceSnapshot],
    title: str | None = None,
    save_path: Path | str | None = None,
) -> Figure:
    """
    Plot bid-ask spread over time.

    Args:
        snapshots: Price snapshots with bid/ask data
        title: Chart title
        save_path: Optional path to save figure

    Returns:
        Matplotlib Figure
    """
    if not snapshots:
        raise ValueError("No snapshots provided")

    sorted_snaps = sorted(snapshots, key=lambda s: s.snapshot_time)
    ticker = sorted_snaps[0].ticker

    timestamps = [s.snapshot_time for s in sorted_snaps]
    spreads = [s.yes_ask - s.yes_bid for s in sorted_snaps]

    fig, ax = plt.subplots(figsize=(12, 6))

    timestamps_any: Any = timestamps
    ax.plot(timestamps_any, spreads, "purple", linewidth=1)
    ax.fill_between(timestamps_any, spreads, alpha=0.2, color="purple")

    date_formatter: Callable[[str], Any] = mdates.DateFormatter
    ax.xaxis.set_major_formatter(date_formatter("%m/%d"))
    auto_locator: Callable[[], Any] = mdates.AutoDateLocator
    ax.xaxis.set_major_locator(auto_locator())

    ax.set_xlabel("Date")
    ax.set_ylabel("Spread (cents)")
    ax.set_title(title or f"Bid-Ask Spread: {ticker}")
    ax.grid(True, alpha=0.3)

    plt.xticks(rotation=45)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig
