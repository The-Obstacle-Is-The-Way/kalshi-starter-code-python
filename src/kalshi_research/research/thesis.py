"""Research thesis framework for tracking predictions."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import structlog

from kalshi_research.paths import DEFAULT_THESES_PATH
from kalshi_research.research._thesis_models import Thesis, ThesisEvidence, ThesisStatus

logger = structlog.get_logger()

# Re-export for backwards compatibility
__all__ = ["Thesis", "ThesisEvidence", "ThesisManager", "ThesisStatus", "ThesisTracker"]


class ThesisTracker:
    """
    Track and persist research theses.

    Provides methods for:
    - Creating and storing theses
    - Loading theses from disk
    - Analyzing thesis performance
    """

    def __init__(self, storage_path: str | Path = DEFAULT_THESES_PATH) -> None:
        """
        Initialize the tracker.

        Args:
            storage_path: Path to JSON file for persistence
        """
        self.storage_path = Path(storage_path)
        self.theses: dict[str, Thesis] = {}
        self._load()

    def _load(self) -> None:
        """Load theses from storage."""
        if self.storage_path.exists():
            try:
                with self.storage_path.open(encoding="utf-8") as f:
                    raw = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Theses file is not valid JSON: {self.storage_path}. "
                    "Fix the file or restore from backup."
                ) from e

            if not isinstance(raw, dict):
                raise ValueError(f"Theses file must contain a JSON object: {self.storage_path}")

            # Handle CLI format {"theses": [...]}
            if "theses" in raw:
                theses_raw = raw["theses"]
                if not isinstance(theses_raw, list):
                    raise ValueError(
                        f"Theses file has an unexpected schema: {self.storage_path} "
                        "(expected key 'theses: [...]')"
                    )

                loaded_from_list: dict[str, Thesis] = {}
                for i, item in enumerate(theses_raw):
                    if not isinstance(item, dict):
                        raise ValueError(
                            f"Theses file has an invalid entry at index {i}: {self.storage_path}"
                        )
                    try:
                        thesis = Thesis.from_dict(item)
                    except (KeyError, TypeError, ValueError) as e:
                        raise ValueError(
                            f"Theses file contains an invalid thesis at index {i}: "
                            f"{self.storage_path}"
                        ) from e
                    loaded_from_list[thesis.id] = thesis
                self.theses = loaded_from_list
                return

            # No "theses" key found - reject unknown schema
            raise ValueError(
                f"Theses file has an unexpected schema: {self.storage_path}. "
                f'Expected format: {{"theses": [...]}}'
            )

    def _save(self) -> None:
        """Save theses to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        # Save in CLI-compatible format
        data = {"theses": [t.to_dict() for t in self.theses.values()]}
        tmp_path = self.storage_path.with_suffix(
            f"{self.storage_path.suffix}.tmp.{uuid.uuid4().hex}"
        )
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        tmp_path.replace(self.storage_path)

    def add(self, thesis: Thesis) -> None:
        """Add a thesis."""
        self.theses[thesis.id] = thesis
        self._save()

    def get(self, thesis_id: str) -> Thesis | None:
        """Get a thesis by ID."""
        return self.theses.get(thesis_id)

    def remove(self, thesis_id: str) -> None:
        """Remove a thesis."""
        if thesis_id in self.theses:
            del self.theses[thesis_id]
            self._save()

    def update(self, thesis: Thesis) -> None:
        """Update a thesis."""
        self.theses[thesis.id] = thesis
        self._save()

    def list_active(self) -> list[Thesis]:
        """Get all active theses."""
        return [t for t in self.theses.values() if t.status == ThesisStatus.ACTIVE]

    def list_resolved(self) -> list[Thesis]:
        """Get all resolved theses."""
        return [t for t in self.theses.values() if t.status == ThesisStatus.RESOLVED]

    def list_by_status(self, status: ThesisStatus) -> list[Thesis]:
        """Get theses by status."""
        return [t for t in self.theses.values() if t.status == status]

    def list_all(self) -> list[Thesis]:
        """Get all theses."""
        return list(self.theses.values())

    def performance_summary(self) -> dict[str, Any]:
        """
        Calculate performance metrics for resolved theses.

        Returns:
            Dictionary with performance metrics
        """
        resolved = self.list_resolved()
        if not resolved:
            return {
                "total_resolved": 0,
                "correct_predictions": 0,
                "accuracy": None,
                "avg_brier_score": None,
                "avg_edge_when_correct": None,
                "avg_edge_when_wrong": None,
            }

        scored = [t for t in resolved if t.was_correct is not None]
        correct = [t for t in scored if t.was_correct]
        incorrect = [t for t in scored if t.was_correct is False]
        brier_scores = [t.brier_score for t in scored if t.brier_score is not None]

        return {
            "total_resolved": len(resolved),
            "correct_predictions": len(correct),
            "accuracy": len(correct) / len(scored) if scored else None,
            "avg_brier_score": sum(brier_scores) / len(brier_scores) if brier_scores else None,
            "avg_edge_when_correct": (
                sum(t.edge_size for t in correct) / len(correct) if correct else None
            ),
            "avg_edge_when_wrong": (
                sum(t.edge_size for t in incorrect) / len(incorrect) if incorrect else None
            ),
        }


ThesisManager = ThesisTracker
