"""Step execution logic for research agent.

This module handles executing individual research steps (search, answer, research).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from kalshi_research.agent.research_agent._recovery import DeepResearchRecovery
from kalshi_research.agent.schemas import (
    Factor,
    ResearchStep,
    ResearchStepResult,
    ResearchStepStatus,
)
from kalshi_research.exa.policy import extract_exa_cost_total

if TYPE_CHECKING:
    from kalshi_research.agent.state import ResearchTaskState
    from kalshi_research.api.models.market import Market
    from kalshi_research.exa.client import ExaClient

logger = structlog.get_logger()


class StepExecutor:
    """Executes individual research steps with support for search, answer, and deep research."""

    def __init__(self, exa: ExaClient, state: ResearchTaskState) -> None:
        self._exa = exa
        self._state = state
        self._recovery = DeepResearchRecovery(exa=exa, state=state)

    async def execute_step(self, step: ResearchStep, market: Market) -> ResearchStepResult:
        """Execute a single research step and return results with factors."""
        logger.info("executing_step", step_id=step.step_id, endpoint=step.endpoint)

        factors: list[Factor] = []
        actual_cost = 0.0
        sources_found = 0

        if step.endpoint == "search":
            factors, actual_cost, sources_found = await self._execute_search(step)

        elif step.endpoint == "answer":
            factors, actual_cost, sources_found = await self._execute_answer(step)

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

    async def _execute_search(self, step: ResearchStep) -> tuple[list[Factor], float, int]:
        """Execute a search step and extract factors."""
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
        factors: list[Factor] = []
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

        return factors, actual_cost, sources_found

    async def _execute_answer(self, step: ResearchStep) -> tuple[list[Factor], float, int]:
        """Execute an answer step and extract factors."""
        answer_response = await self._exa.answer(
            query=step.params["query"],
            text=step.params.get("include_text", False),
        )

        actual_cost = extract_exa_cost_total(answer_response)

        # Extract factors from answer citations
        factors: list[Factor] = []
        sources_found = 0
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

        return factors, actual_cost, sources_found

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
        task, research_id_to_wait = await self._recovery.recover_or_create_research_task(
            ticker=ticker, instructions=instructions
        )

        # Wait for completion if task is still running
        if task is None:
            task = await self._recovery.wait_for_research_task(
                research_id=research_id_to_wait,
                poll_interval_seconds=poll_interval_seconds,
                timeout_seconds=timeout_seconds,
            )

        # Finalize: extract factors or raise on failure
        return self._recovery.finalize_research_task(task=task, ticker=ticker)
