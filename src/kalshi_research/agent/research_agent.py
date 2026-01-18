"""Deterministic research agent with cost-bounded execution.

This agent orchestrates Exa API calls in a predictable, budget-aware manner.
No LLM planning in Phase 1 - plans are deterministic functions of mode + market metadata.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog

from kalshi_research.agent.schemas import (
    Factor,
    ResearchPlan,
    ResearchStep,
    ResearchStepResult,
    ResearchStepStatus,
    ResearchSummary,
)
from kalshi_research.agent.state import ResearchTaskState
from kalshi_research.exa.models import ResearchStatus
from kalshi_research.exa.policy import ExaBudget, ExaMode, ExaPolicy, extract_exa_cost_total

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

    def build_plan(
        self,
        market: Market,
        *,
        mode: ExaMode = ExaMode.STANDARD,
        budget_usd: float,
        recency_days: int = 30,
    ) -> ResearchPlan:
        """
        Build a deterministic research plan for a given market and mode.

        Args:
            market: Market metadata
            mode: Research mode (fast/standard/deep)
            budget_usd: Budget limit
            recency_days: Recency window for news searches

        Returns:
            A serializable ResearchPlan with ordered steps and cost estimates.
        """
        policy = ExaPolicy.from_mode(mode=mode, budget_usd=budget_usd)

        # Generate search queries from market title
        queries = self._generate_queries(market.title)

        steps: list[ResearchStep] = []
        step_counter = 0

        # Step 1: News search (all modes)
        for query in queries[: 2 if mode == ExaMode.FAST else 3]:
            step_counter += 1
            num_results = 5 if mode == ExaMode.FAST else 10
            steps.append(
                ResearchStep(
                    step_id=f"news_search_{step_counter}",
                    endpoint="search",
                    description=f"News search for: {query}",
                    estimated_cost_usd=policy.estimate_search_cost_usd(
                        num_results=num_results,
                        include_text=policy.include_full_text,
                        include_highlights=True,
                        search_type=policy.exa_search_type,
                    ),
                    params={
                        "query": query,
                        "num_results": num_results,
                        "start_published_date": (
                            datetime.now(UTC) - timedelta(days=recency_days)
                        ).isoformat(),
                        "category": "news",
                        "use_autoprompt": True,
                        "include_text": policy.include_full_text,
                        "include_highlights": True,
                    },
                )
            )

        # Step 2: Answer call (standard/deep modes only)
        if mode != ExaMode.FAST and policy.include_answer:
            step_counter += 1
            steps.append(
                ResearchStep(
                    step_id=f"answer_{step_counter}",
                    endpoint="answer",
                    description=f"Topic summary for: {queries[0]}",
                    estimated_cost_usd=policy.estimate_answer_cost_usd(
                        include_text=policy.include_full_text
                    ),
                    params={
                        "query": queries[0],
                        "include_text": policy.include_full_text,
                        "num_results": 5,
                    },
                )
            )

        # Step 3: Background research (deep mode only)
        if mode == ExaMode.DEEP:
            step_counter += 1
            research_query = f"Research on {market.title.rstrip('?').strip()}"
            steps.append(
                ResearchStep(
                    step_id=f"deep_research_{step_counter}",
                    endpoint="research",
                    description=f"Deep research task: {research_query}",
                    estimated_cost_usd=0.50,  # Conservative estimate for /research/v1
                    params={
                        "instructions": research_query,
                        "use_autoprompt": True,
                    },
                )
            )

        total_estimated = sum(step.estimated_cost_usd for step in steps)

        # Generate deterministic plan ID
        plan_input = f"{market.ticker}|{mode.value}|{recency_days}|{len(steps)}"
        plan_id = hashlib.sha256(plan_input.encode()).hexdigest()[:12]

        return ResearchPlan(
            plan_id=plan_id,
            ticker=market.ticker,
            mode=mode.value,
            steps=steps,
            total_estimated_cost_usd=total_estimated,
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
                result = await self._execute_step(step, market)
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

                # Extract factors from step result (stored in result metadata)
                if hasattr(result, "factors"):
                    factors.extend(result.factors)

                # Track queries
                query = step.params.get("query")
                if query and isinstance(query, str):
                    queries_used.append(query)

            except Exception as e:
                logger.error("step_execution_failed", step_id=step.step_id, error=str(e))
                step_results.append(
                    {
                        "step_id": step.step_id,
                        "status": ResearchStepStatus.FAILED.value,
                        "actual_cost_usd": 0.0,
                        "error": str(e),
                    }
                )

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
    ) -> ResearchSummary:
        """
        Run a complete research workflow for a market.

        Args:
            market: Market to research
            mode: Research mode (fast/standard/deep)
            budget_usd: Budget limit (uses mode default if None)
            recency_days: Recency window for news searches

        Returns:
            ResearchSummary with all results and metadata.
        """
        policy = ExaPolicy.from_mode(mode=mode, budget_usd=budget_usd)
        budget = ExaBudget(limit_usd=policy.budget_usd)

        plan = self.build_plan(
            market, mode=mode, budget_usd=policy.budget_usd, recency_days=recency_days
        )

        return await self.execute_plan(plan, market, budget=budget)

    async def _execute_research_task(
        self, step: ResearchStep, market: Market
    ) -> tuple[list[Factor], float, int]:
        """
        Execute deep research task with crash recovery.

        Returns:
            Tuple of (factors, actual_cost, sources_found)
        """
        instructions = step.params["instructions"]
        ticker = market.ticker

        # Check for existing orphaned task first (crash recovery)
        task = None
        saved_state = self._state.load_research_task(ticker)

        if saved_state:
            logger.info(
                "attempting_research_task_recovery",
                ticker=ticker,
                saved_research_id=saved_state.get("research_id"),
            )

            # Try to recover using saved ID first
            try:
                task = await self._exa.get_research_task(saved_state["research_id"])
                logger.info(
                    "recovered_research_task_by_id",
                    research_id=task.research_id,
                    status=task.status.value,
                )
            except Exception:
                # Saved ID failed, try finding by instructions
                logger.warning(
                    "saved_id_recovery_failed_trying_list",
                    saved_research_id=saved_state.get("research_id"),
                )
                task = await self._exa.find_recent_research_task(
                    instructions_prefix=instructions[:50],
                )
                if task:
                    logger.info(
                        "recovered_research_task_by_list",
                        research_id=task.research_id,
                        status=task.status.value,
                    )

        # If no recoverable task found, create new one
        if task is None:
            task = await self._exa.create_research_task(instructions=instructions)
            logger.info("research_task_created", research_id=task.research_id)

            # Persist task ID BEFORE polling starts (crash recovery point)
            self._state.save_research_task(
                ticker=ticker,
                research_id=task.research_id,
                instructions=instructions,
            )

        # Poll for completion (with timeout)
        max_polls = 60
        poll_count = 0
        while task.status != ResearchStatus.COMPLETED and poll_count < max_polls:
            await asyncio.sleep(5)  # Wait 5 seconds between polls
            task = await self._exa.get_research_task(task.research_id)
            poll_count += 1

        factors: list[Factor] = []
        actual_cost = 0.0
        sources_found = 0

        if task.status == ResearchStatus.COMPLETED:
            actual_cost = extract_exa_cost_total(task)
            sources_found = len(task.citations) if task.citations else 0

            # Extract factors from research citations
            if task.citations:
                for research_citation in task.citations[:10]:
                    factors.append(
                        Factor(
                            factor_text=research_citation.title or "Research finding",
                            source_url=research_citation.url,
                            confidence="high",
                        )
                    )

            # Clear state after successful completion
            self._state.clear_research_task(ticker)
        else:
            logger.warning(
                "research_task_timeout",
                research_id=task.research_id,
                status=task.status.value,
            )

        return factors, actual_cost, sources_found

    async def _execute_step(self, step: ResearchStep, market: Market) -> ResearchStepResult:
        """Execute a single research step and return results with factors."""

        logger.info("executing_step", step_id=step.step_id, endpoint=step.endpoint)

        factors: list[Factor] = []
        actual_cost = 0.0
        sources_found = 0

        if step.endpoint == "search":
            # Execute search using ExaClient API
            start_date_str = step.params.get("start_published_date")
            start_date = None
            if start_date_str:
                start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))

            search_response = await self._exa.search(
                query=step.params["query"],
                num_results=step.params.get("num_results", 10),
                start_published_date=start_date,
                category=step.params.get("category"),
                search_type=step.params.get("type", "auto"),
                text=step.params.get("include_text", False),
                highlights=step.params.get("include_highlights", False),
            )

            actual_cost = extract_exa_cost_total(search_response)
            sources_found = len(search_response.results)

            # Extract factors from search results
            for search_result in search_response.results[:10]:  # Limit factor extraction
                factor_text = search_result.title
                if search_result.highlights and len(search_result.highlights) > 0:
                    factor_text = search_result.highlights[0]

                factors.append(
                    Factor(
                        factor_text=factor_text,
                        source_url=search_result.url,
                        confidence="medium",
                        highlight=search_result.highlights[0] if search_result.highlights else None,
                        published_date=search_result.published_date,
                    )
                )

        elif step.endpoint == "answer":
            # Execute answer call using ExaClient API
            answer_response = await self._exa.answer(
                query=step.params["query"],
                text=step.params.get("include_text", False),
            )

            actual_cost = extract_exa_cost_total(answer_response)

            # Extract factors from answer citations
            if answer_response.citations:
                sources_found = len(answer_response.citations)
                for citation in answer_response.citations[:5]:
                    factors.append(
                        Factor(
                            factor_text=answer_response.answer[:200]
                            if answer_response.answer
                            else citation.title,
                            source_url=citation.url,
                            confidence="high",
                            highlight=citation.title,
                            published_date=citation.published_date,
                        )
                    )

        elif step.endpoint == "research":
            # Execute deep research task (async) with crash recovery
            factors, actual_cost, sources_found = await self._execute_research_task(step, market)

        # Create result with factors attached
        result = ResearchStepResult(
            step_id=step.step_id,
            status=ResearchStepStatus.COMPLETED,
            actual_cost_usd=actual_cost,
            sources_found=sources_found,
        )

        # Attach factors to result (we'll use object attributes since Pydantic model is frozen)
        # Store factors in a way the caller can access
        object.__setattr__(result, "factors", factors)

        return result

    def _generate_queries(self, title: str) -> list[str]:
        """Generate search queries from market title."""
        clean_title = title.strip()
        if clean_title.lower().startswith("will "):
            clean_title = clean_title[5:]
        clean_title = clean_title.rstrip("?").strip()

        queries = [
            clean_title,
            f"{clean_title} news",
            f"{clean_title} analysis forecast",
        ]

        # Deduplicate and limit
        return list(dict.fromkeys(q for q in queries if q))[:3]
