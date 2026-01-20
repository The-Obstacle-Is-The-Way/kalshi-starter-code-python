"""Deterministic research agent with cost-bounded execution.

This agent orchestrates Exa API calls in a predictable, budget-aware manner.
No LLM planning in Phase 1 - plans are deterministic functions of mode + market metadata.
"""

from __future__ import annotations

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
from kalshi_research.exa.exceptions import ExaAPIError, ExaError
from kalshi_research.exa.models import ResearchStatus
from kalshi_research.exa.policy import ExaBudget, ExaMode, ExaPolicy, extract_exa_cost_total

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market
    from kalshi_research.exa.client import ExaClient
    from kalshi_research.exa.models import ResearchTask

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
        if deep_research_timeout_seconds <= 0:
            raise ValueError("deep_research_timeout_seconds must be positive")
        if deep_research_poll_interval_seconds <= 0:
            raise ValueError("deep_research_poll_interval_seconds must be positive")

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
                        "timeout_seconds": deep_research_timeout_seconds,
                        "poll_interval_seconds": deep_research_poll_interval_seconds,
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
        poll_interval_seconds = float(step.params.get("poll_interval_seconds", 5.0))
        timeout_seconds = float(step.params.get("timeout_seconds", 300.0))
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be positive")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        # Attempt recovery or create new task
        task, research_id_to_wait = await self._recover_or_create_research_task(
            ticker=ticker, instructions=instructions
        )

        # Wait for completion if task is still running
        if task is None:
            task = await self._wait_for_research_task(
                research_id=research_id_to_wait,
                poll_interval_seconds=poll_interval_seconds,
                timeout_seconds=timeout_seconds,
            )

        # Finalize: extract factors or raise on failure
        return self._finalize_research_task(task=task, ticker=ticker)

    async def _recover_or_create_research_task(
        self, *, ticker: str, instructions: str
    ) -> tuple[ResearchTask | None, str | None]:
        """
        Attempt to recover an existing research task or create a new one.

        Returns:
            Tuple of (completed_task, research_id_to_wait_for).
            If completed_task is not None, no waiting needed.
            If research_id_to_wait_for is not None, caller must wait for completion.
        """
        task: ResearchTask | None = None
        research_id_to_wait_for: str | None = None

        # Check for existing orphaned task first (crash recovery)
        saved_state = self._state.load_research_task(ticker)
        if saved_state:
            task, research_id_to_wait_for = await self._try_recover_from_saved_state(
                saved_state=saved_state, ticker=ticker, instructions=instructions
            )

        # If no recoverable task found, create new one
        if task is None and research_id_to_wait_for is None:
            task, research_id_to_wait_for = await self._create_new_research_task(
                ticker=ticker, instructions=instructions
            )

        return task, research_id_to_wait_for

    async def _try_recover_from_saved_state(
        self, *, saved_state: dict[str, str], ticker: str, instructions: str
    ) -> tuple[ResearchTask | None, str | None]:
        """Attempt to recover a research task from saved crash-recovery state."""
        task: ResearchTask | None = None
        research_id_to_wait_for: str | None = None

        saved_research_id = saved_state.get("research_id")
        logger.info(
            "attempting_research_task_recovery",
            ticker=ticker,
            saved_research_id=saved_research_id,
        )

        # Try recovery by ID first
        if isinstance(saved_research_id, str) and saved_research_id:
            task, research_id_to_wait_for = await self._try_recover_by_id(saved_research_id)

        else:
            logger.warning("saved_state_missing_research_id", ticker=ticker)

        # Fall back to list-based recovery if ID recovery failed
        if task is None and research_id_to_wait_for is None:
            task, research_id_to_wait_for = await self._try_recover_by_list(
                ticker=ticker, instructions=instructions
            )

        return task, research_id_to_wait_for

    async def _try_recover_by_id(self, research_id: str) -> tuple[ResearchTask | None, str | None]:
        """Try to recover a research task by its saved ID."""
        task: ResearchTask | None = None
        research_id_to_wait_for: str | None = None

        try:
            recovered = await self._exa.get_research_task(research_id)
            logger.info(
                "recovered_research_task_by_id",
                research_id=recovered.research_id,
                status=recovered.status.value,
            )
            if self._is_terminal_status(recovered):
                task = recovered
            else:
                research_id_to_wait_for = recovered.research_id
        except ExaError as exc:
            logger.warning(
                "saved_id_recovery_failed_trying_list",
                saved_research_id=research_id,
                error=str(exc),
            )

        return task, research_id_to_wait_for

    async def _try_recover_by_list(
        self, *, ticker: str, instructions: str
    ) -> tuple[ResearchTask | None, str | None]:
        """Try to recover a research task via find_recent_research_task."""
        task: ResearchTask | None = None
        research_id_to_wait_for: str | None = None

        try:
            recovered = await self._exa.find_recent_research_task(
                instructions_prefix=instructions[:50],
            )
        except ExaError as exc:
            logger.warning("list_recovery_failed", ticker=ticker, error=str(exc))
            return task, research_id_to_wait_for

        if recovered:
            # Update state with the recovered ID so future crashes can recover by ID.
            self._state.save_research_task(
                ticker=ticker,
                research_id=recovered.research_id,
                instructions=instructions,
            )
            logger.info(
                "recovered_research_task_by_list",
                research_id=recovered.research_id,
                status=recovered.status.value,
            )
            if self._is_terminal_status(recovered):
                task = recovered
            else:
                research_id_to_wait_for = recovered.research_id

        return task, research_id_to_wait_for

    async def _create_new_research_task(
        self, *, ticker: str, instructions: str
    ) -> tuple[ResearchTask | None, str | None]:
        """Create a new research task and save state for crash recovery."""
        task: ResearchTask | None = None
        research_id_to_wait_for: str | None = None

        created = await self._exa.create_research_task(instructions=instructions)
        logger.info("research_task_created", research_id=created.research_id)

        # Persist task ID BEFORE polling starts (crash recovery point)
        self._state.save_research_task(
            ticker=ticker,
            research_id=created.research_id,
            instructions=instructions,
        )
        if self._is_terminal_status(created):
            task = created
        else:
            research_id_to_wait_for = created.research_id

        return task, research_id_to_wait_for

    def _is_terminal_status(self, task: ResearchTask) -> bool:
        """Check if a research task has reached a terminal status."""
        return task.status in (
            ResearchStatus.COMPLETED,
            ResearchStatus.CANCELED,
            ResearchStatus.FAILED,
        )

    async def _wait_for_research_task(
        self, *, research_id: str | None, poll_interval_seconds: float, timeout_seconds: float
    ) -> ResearchTask:
        """Wait for a research task to complete."""
        if research_id is None:
            raise RuntimeError("Internal error: missing research_id for wait_for_research")

        try:
            return await self._exa.wait_for_research(
                research_id,
                poll_interval=poll_interval_seconds,
                timeout=timeout_seconds,
            )
        except TimeoutError:
            logger.warning("research_task_timeout", research_id=research_id)
            # Keep state file for later recovery (task may complete server-side).
            raise

    def _finalize_research_task(
        self, *, task: ResearchTask, ticker: str
    ) -> tuple[list[Factor], float, int]:
        """
        Finalize a completed research task: extract factors or raise on failure.

        Returns:
            Tuple of (factors, actual_cost, sources_found)
        """
        if task.status != ResearchStatus.COMPLETED:
            # Terminal but not successful.
            self._state.clear_research_task(ticker)
            raise ExaAPIError(
                f"Research task ended with status={task.status.value}",
                status_code=None,
            )

        actual_cost = extract_exa_cost_total(task)
        sources_found = len(task.citations) if task.citations else 0

        factors: list[Factor] = []
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
        else:
            raise ValueError(f"Unknown research step endpoint: {step.endpoint!r}")

        return ResearchStepResult(
            step_id=step.step_id,
            status=ResearchStepStatus.COMPLETED,
            actual_cost_usd=actual_cost,
            sources_found=sources_found,
            factors=factors,
        )

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
