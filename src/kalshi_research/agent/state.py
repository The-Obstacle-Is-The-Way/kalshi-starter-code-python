"""Research task state management for crash recovery.

Provides lightweight JSON-based persistence for tracking in-progress deep research tasks.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import structlog

logger = structlog.get_logger()


class ResearchTaskState:
    """Manages persistence of in-progress research task IDs for crash recovery."""

    def __init__(self, state_dir: Path | None = None) -> None:
        """
        Initialize state manager.

        Args:
            state_dir: Directory for state files (defaults to data/agent_state)
        """
        if state_dir is None:
            state_dir = Path("data/agent_state")

        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _get_state_file(self, ticker: str) -> Path:
        """Get state file path for a specific ticker."""
        # Use ticker as filename (sanitized)
        safe_ticker = ticker.replace("/", "_").replace("\\", "_")
        return self.state_dir / f"{safe_ticker}_research.json"

    def save_research_task(
        self,
        ticker: str,
        research_id: str,
        instructions: str,
    ) -> None:
        """
        Persist research task ID before polling starts.

        Args:
            ticker: Market ticker
            research_id: Exa research task ID
            instructions: Research instructions (for matching)
        """
        state_file = self._get_state_file(ticker)

        state = {
            "ticker": ticker,
            "research_id": research_id,
            "instructions": instructions,
            "created_at": datetime.now(UTC).isoformat(),
        }

        try:
            state_file.write_text(json.dumps(state, indent=2))
            logger.debug(
                "saved_research_task_state",
                ticker=ticker,
                research_id=research_id,
                state_file=str(state_file),
            )
        except Exception as e:
            logger.warning("failed_to_save_research_task_state", error=str(e))

    def load_research_task(self, ticker: str) -> dict[str, str] | None:
        """
        Load persisted research task state for recovery.

        Args:
            ticker: Market ticker

        Returns:
            Saved state dict or None if not found
        """
        state_file = self._get_state_file(ticker)

        if not state_file.exists():
            return None

        try:
            state: dict[str, str] = json.loads(state_file.read_text())
            logger.debug(
                "loaded_research_task_state",
                ticker=ticker,
                research_id=state.get("research_id"),
            )
            return state
        except Exception as e:
            logger.warning("failed_to_load_research_task_state", error=str(e))
            return None

    def clear_research_task(self, ticker: str) -> None:
        """
        Clear research task state after successful completion.

        Args:
            ticker: Market ticker
        """
        state_file = self._get_state_file(ticker)

        if state_file.exists():
            try:
                state_file.unlink()
                logger.debug("cleared_research_task_state", ticker=ticker)
            except Exception as e:
                logger.warning("failed_to_clear_research_task_state", error=str(e))
