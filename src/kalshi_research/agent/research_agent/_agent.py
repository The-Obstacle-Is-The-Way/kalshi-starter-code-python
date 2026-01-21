"""Main ResearchAgent class providing the public API.

This module contains the ResearchAgent class that orchestrates research workflows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from kalshi_research.agent.research_agent._executor import StepExecutor
from kalshi_research.agent.research_agent._plan_builder import (
    _generate_queries,
    build_research_plan,
)
from kalshi_research.agent.schemas import (
    Factor,
    ResearchPlan,
    ResearchStep,
    ResearchStepResult,
    ResearchStepStatus,
    ResearchSummary,
)
from kalshi_research.agent.state import ResearchTaskState
from kalshi_research.exa.exceptions import ExaError
from kalshi_research.exa.policy import ExaBudget, ExaMode, ExaPolicy

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market
    from kalshi_research.exa.client import ExaClient

logger = structlog.get_logger()


class ResearchAgent:
    """
    Cost-bounded research agent that executes deterministic Exa workflows.

    Usage:
        agent = ResearchAgent(exa_client)
        summary = await agent.research(market, mode="standard", budget_usd=0.50)
    """

    def __init__(self, exa: ExaClient) -> None:
        self._exa = exa
        self._state = ResearchTaskState()
        self._executor = StepExecutor(exa=exa, state=self._state)

    def build_plan(
        self,
        market: Market,
        *,
        mode: ExaMode = ExaMode.STANDARD,
        budget_usd: float,
        recency_days: int = 30,
        deep_research_timeout_seconds: float = 300.0,
        deep_research_poll_interval_seconds: float = 5.0,
    ) -> ResearchPlan:
        """
        Build a deterministic research plan for a given market and mode.

        Args:
            market: Market metadata
            mode: Research mode (fast/standard/deep)
            budget_usd: Budget limit
            recency_days: Recency window for news searches
            deep_research_timeout_seconds: Max seconds to wait for deep research
                completion (deep mode)
            deep_research_poll_interval_seconds: Seconds between deep research polls (deep mode)

        Returns:
            A serializable ResearchPlan with ordered steps and cost estimates.
        """
        return build_research_plan(
            market,
            mode=mode,
            budget_usd=budget_usd,
            recency_days=recency_days,
            deep_research_timeout_seconds=deep_research_timeout_seconds,
            deep_research_poll_interval_seconds=deep_research_poll_interval_seconds,
        )

    async def execute_plan(
        self,
        plan: ResearchPlan,
        market: Market,
        *,
        budget: ExaBudget,
    ) -> ResearchSummary:
        """
        Execute a research plan with budget enforcement.

        Args:
            plan: Research plan to execute
            market: Market metadata
            budget: Mutable budget tracker

        Returns:
            ResearchSummary with factors, costs, and execution metadata.
        """
        logger.info(
            "executing_research_plan",
            plan_id=plan.plan_id,
            ticker=plan.ticker,
            mode=plan.mode,
            steps=len(plan.steps),
            budget_limit=budget.limit_usd,
        )

        factors: list[Factor] = []
        queries_used: list[str] = []
        total_sources = 0
        step_results: list[dict[str, object]] = []
        budget_exhausted = False

        for step in plan.steps:
            # Check budget before executing step
            if not budget.can_spend(step.estimated_cost_usd):
                logger.warning(
                    "budget_exhausted_skipping_step",
                    step_id=step.step_id,
                    remaining=budget.remaining_usd,
                    estimated=step.estimated_cost_usd,
                )
                budget_exhausted = True
                step_results.append(
                    {
                        "step_id": step.step_id,
                        "status": ResearchStepStatus.SKIPPED.value,
                        "actual_cost_usd": 0.0,
                        "reason": "budget_exhausted",
                    }
                )
                continue

            # Execute step
            try:
                result = await self._executor.execute_step(step, market)
                budget.record_spend(result.actual_cost_usd)

                step_results.append(
                    {
                        "step_id": result.step_id,
                        "status": result.status.value,
                        "actual_cost_usd": result.actual_cost_usd,
                        "sources_found": result.sources_found,
                    }
                )

                total_sources += result.sources_found

                factors.extend(result.factors)

                # Track queries
                query = step.params.get("query")
                if query and isinstance(query, str):
                    queries_used.append(query)

            except (ExaError, TimeoutError) as exc:
                logger.error("step_execution_failed", step_id=step.step_id, error=str(exc))
                step_results.append(
                    {
                        "step_id": step.step_id,
                        "status": ResearchStepStatus.FAILED.value,
                        "actual_cost_usd": 0.0,
                        "error": str(exc),
                    }
                )
            except Exception:
                logger.exception(
                    "step_execution_crashed",
                    step_id=step.step_id,
                    endpoint=step.endpoint,
                )
                raise

        return ResearchSummary(
            ticker=market.ticker,
            title=market.title,
            mode=plan.mode,
            factors=factors,
            queries_used=queries_used,
            total_sources_found=total_sources,
            total_cost_usd=budget.spent_usd,
            budget_usd=budget.limit_usd,
            budget_exhausted=budget_exhausted,
            steps_executed=step_results,
        )

    async def research(
        self,
        market: Market,
        *,
        mode: ExaMode = ExaMode.STANDARD,
        budget_usd: float | None = None,
        recency_days: int = 30,
        deep_research_timeout_seconds: float = 300.0,
        deep_research_poll_interval_seconds: float = 5.0,
    ) -> ResearchSummary:
        """
        Run a complete research workflow for a market.

        Args:
            market: Market to research
            mode: Research mode (fast/standard/deep)
            budget_usd: Budget limit (uses mode default if None)
            recency_days: Recency window for news searches
            deep_research_timeout_seconds: Max seconds to wait for deep research
                completion (deep mode)
            deep_research_poll_interval_seconds: Seconds between deep research polls (deep mode)

        Returns:
            ResearchSummary with all results and metadata.
        """
        policy = ExaPolicy.from_mode(mode=mode, budget_usd=budget_usd)
        budget = ExaBudget(limit_usd=policy.budget_usd)

        plan = self.build_plan(
            market,
            mode=mode,
            budget_usd=policy.budget_usd,
            recency_days=recency_days,
            deep_research_timeout_seconds=deep_research_timeout_seconds,
            deep_research_poll_interval_seconds=deep_research_poll_interval_seconds,
        )

        return await self.execute_plan(plan, market, budget=budget)

    def _generate_queries(self, title: str) -> list[str]:
        """Generate search queries from market title."""
        return _generate_queries(title)

    async def _execute_step(self, step: ResearchStep, market: Market) -> ResearchStepResult:
        """Execute a single research step (delegated to executor)."""
        return await self._executor.execute_step(step, market)
