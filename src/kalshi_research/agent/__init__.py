"""Research agent system for cost-bounded, reproducible research automation."""

from kalshi_research.agent.orchestrator import AgentKernel
from kalshi_research.agent.research_agent import ResearchAgent
from kalshi_research.agent.schemas import (
    AgentRunResult,
    AnalysisFactor,
    AnalysisResult,
    Factor,
    MarketInfo,
    MarketPriceSnapshot,
    ResearchPlan,
    ResearchStep,
    ResearchStepStatus,
    ResearchSummary,
    VerificationReport,
)
from kalshi_research.agent.verify import verify_analysis

__all__ = [
    "AgentKernel",
    "AgentRunResult",
    "AnalysisFactor",
    "AnalysisResult",
    "Factor",
    "MarketInfo",
    "MarketPriceSnapshot",
    "ResearchAgent",
    "ResearchPlan",
    "ResearchStep",
    "ResearchStepStatus",
    "ResearchSummary",
    "VerificationReport",
    "verify_analysis",
]
