"""Deep research task recovery logic for crash recovery.

This module handles crash recovery for long-running deep research tasks,
including state persistence and task status polling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from kalshi_research.agent.schemas import Factor
from kalshi_research.exa.exceptions import ExaAPIError, ExaError
from kalshi_research.exa.models import ResearchStatus
from kalshi_research.exa.policy import extract_exa_cost_total

if TYPE_CHECKING:
    from kalshi_research.agent.state import ResearchTaskState
    from kalshi_research.exa.client import ExaClient
    from kalshi_research.exa.models import ResearchTask

logger = structlog.get_logger()


class DeepResearchRecovery:
    """Handles crash recovery and completion waiting for deep research tasks."""

    def __init__(self, exa: ExaClient, state: ResearchTaskState) -> None:
        self._exa = exa
        self._state = state

    async def recover_or_create_research_task(
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

    async def wait_for_research_task(
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

    def finalize_research_task(
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
