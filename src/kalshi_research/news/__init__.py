"""News monitoring and sentiment analysis pipeline."""

from __future__ import annotations

from kalshi_research.news.aggregator import SentimentAggregator, SentimentSummary
from kalshi_research.news.collector import NewsCollector
from kalshi_research.news.sentiment import (
    SentimentAnalyzer,
    SentimentResult,
    SummarySentimentAnalyzer,
)
from kalshi_research.news.tracker import NewsTracker

__all__ = [
    "NewsCollector",
    "NewsTracker",
    "SentimentAggregator",
    "SentimentAnalyzer",
    "SentimentResult",
    "SentimentSummary",
    "SummarySentimentAnalyzer",
]
