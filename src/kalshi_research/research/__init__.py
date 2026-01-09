"""Research framework for prediction market thesis tracking."""

from kalshi_research.research.backtest import BacktestResult, BacktestTrade, ThesisBacktester
from kalshi_research.research.context import MarketContextResearcher, MarketResearch, ResearchSource
from kalshi_research.research.thesis import Thesis, ThesisStatus, ThesisTracker
from kalshi_research.research.topic import TopicResearch, TopicResearcher

# Notebook utilities are available but not exported by default
# Users can import explicitly: from kalshi_research.research import notebook_utils

__all__ = [
    "BacktestResult",
    "BacktestTrade",
    "MarketContextResearcher",
    "MarketResearch",
    "ResearchSource",
    "Thesis",
    "ThesisBacktester",
    "ThesisStatus",
    "ThesisTracker",
    "TopicResearch",
    "TopicResearcher",
]
