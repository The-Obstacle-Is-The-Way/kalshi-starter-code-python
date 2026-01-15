"""Research thesis framework for tracking predictions."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

from kalshi_research.paths import DEFAULT_THESES_PATH

logger = structlog.get_logger()


class ThesisStatus(str, Enum):
    """Status of a research thesis."""

    DRAFT = "draft"
    ACTIVE = "active"
    RESOLVED = "resolved"
    ABANDONED = "abandoned"


@dataclass(frozen=True)
class ThesisEvidence:
    """Evidence supporting or opposing a thesis."""

    url: str
    title: str
    source_domain: str
    published_date: datetime | None
    snippet: str
    supports: str  # bull, bear, neutral
    relevance_score: float
    added_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Thesis:
    """
    A research thesis about a market or set of markets.

    Use this to track your predictions and reasoning over time.
    """

    id: str
    title: str
    market_tickers: list[str]

    # Your predictions
    your_probability: float  # 0-1
    market_probability: float  # At time of thesis
    confidence: float  # How sure are you? 0-1

    # Reasoning
    bull_case: str  # Why it might be YES
    bear_case: str  # Why it might be NO
    key_assumptions: list[str]
    invalidation_criteria: list[str]  # What would prove you wrong?

    # Tracking
    status: ThesisStatus = ThesisStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None
    actual_outcome: str | None = None  # yes, no, void

    # Notes over time
    updates: list[dict[str, Any]] = field(default_factory=list)

    # Research evidence (optional)
    evidence: list[ThesisEvidence] = field(default_factory=list)
    research_summary: str | None = None
    last_research_at: datetime | None = None

    def add_update(self, note: str) -> None:
        """Add a timestamped update to the thesis."""
        self.updates.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "note": note,
            }
        )

    def resolve(self, outcome: str) -> None:
        """Mark thesis as resolved with outcome."""
        self.status = ThesisStatus.RESOLVED
        self.resolved_at = datetime.now(UTC)
        self.actual_outcome = outcome

    def activate(self) -> None:
        """Activate a draft thesis."""
        if self.status == ThesisStatus.DRAFT:
            self.status = ThesisStatus.ACTIVE

    def abandon(self, reason: str) -> None:
        """Abandon the thesis with a reason."""
        self.status = ThesisStatus.ABANDONED
        self.add_update(f"ABANDONED: {reason}")

    def add_evidence(self, evidence: ThesisEvidence) -> None:
        """Add research evidence to the thesis."""
        self.evidence.append(evidence)
        self.last_research_at = datetime.now(UTC)

    def get_bull_evidence(self) -> list[ThesisEvidence]:
        """Return evidence supporting the bull case."""
        return [e for e in self.evidence if e.supports == "bull"]

    def get_bear_evidence(self) -> list[ThesisEvidence]:
        """Return evidence supporting the bear case."""
        return [e for e in self.evidence if e.supports == "bear"]

    @property
    def edge_size(self) -> float:
        """Difference between your estimate and market."""
        return self.your_probability - self.market_probability

    @property
    def was_correct(self) -> bool | None:
        """Did your thesis predict correctly?"""
        if self.actual_outcome is None:
            return None

        if self.your_probability == 0.5:
            return None

        if self.actual_outcome == "yes":
            return self.your_probability > 0.5
        if self.actual_outcome == "no":
            return self.your_probability < 0.5
        return None

    @property
    def brier_score(self) -> float | None:
        """Calculate Brier score for this thesis (if resolved)."""
        if self.actual_outcome is None:
            return None

        if self.actual_outcome == "yes":
            outcome = 1.0
        elif self.actual_outcome == "no":
            outcome = 0.0
        else:
            return None
        return (self.your_probability - outcome) ** 2

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        base: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "market_tickers": self.market_tickers,
            "your_probability": self.your_probability,
            "market_probability": self.market_probability,
            "confidence": self.confidence,
            "bull_case": self.bull_case,
            "bear_case": self.bear_case,
            "key_assumptions": self.key_assumptions,
            "invalidation_criteria": self.invalidation_criteria,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "actual_outcome": self.actual_outcome,
            "updates": self.updates,
        }
        base["evidence"] = [
            {
                "url": e.url,
                "title": e.title,
                "source_domain": e.source_domain,
                "published_date": e.published_date.isoformat() if e.published_date else None,
                "snippet": e.snippet,
                "supports": e.supports,
                "relevance_score": e.relevance_score,
                "added_at": e.added_at.isoformat(),
            }
            for e in self.evidence
        ]
        base["research_summary"] = self.research_summary
        base["last_research_at"] = (
            self.last_research_at.isoformat() if self.last_research_at else None
        )
        return base

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        """Parse an ISO-8601 datetime string into a `datetime` (or return `None`)."""
        if isinstance(value, str) and value:
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Thesis:
        """Create from dictionary."""
        status_value = str(data.get("status", ThesisStatus.DRAFT.value))
        try:
            status = ThesisStatus(status_value)
        except ValueError:
            status = ThesisStatus.DRAFT

        evidence_raw = data.get("evidence", [])
        evidence: list[ThesisEvidence] = []
        if isinstance(evidence_raw, list):
            for item in evidence_raw:
                if not isinstance(item, dict):
                    continue
                published_dt = cls._parse_datetime(item.get("published_date"))
                added_dt = cls._parse_datetime(item.get("added_at")) or datetime.now(UTC)
                evidence.append(
                    ThesisEvidence(
                        url=str(item.get("url", "")),
                        title=str(item.get("title", "")),
                        source_domain=str(item.get("source_domain", "")),
                        published_date=published_dt,
                        snippet=str(item.get("snippet", "")),
                        supports=str(item.get("supports", "neutral")),
                        relevance_score=float(item.get("relevance_score", 0.0)),
                        added_at=added_dt,
                    )
                )

        thesis = cls(
            id=data["id"],
            title=data["title"],
            market_tickers=data["market_tickers"],
            your_probability=data["your_probability"],
            market_probability=data["market_probability"],
            confidence=data["confidence"],
            bull_case=data["bull_case"],
            bear_case=data["bear_case"],
            key_assumptions=data.get("key_assumptions", []),
            invalidation_criteria=data.get("invalidation_criteria", []),
            status=status,
            created_at=datetime.fromisoformat(data["created_at"]),
            resolved_at=(
                datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None
            ),
            actual_outcome=data.get("actual_outcome"),
            updates=data.get("updates", []),
        )
        thesis.evidence = evidence
        thesis.research_summary = data.get("research_summary")
        thesis.last_research_at = cls._parse_datetime(data.get("last_research_at"))
        return thesis

    def __str__(self) -> str:
        edge_pct = self.edge_size * 100
        return (
            f"[{self.status.value.upper()}] {self.title}\n"
            f"  Tickers: {', '.join(self.market_tickers)}\n"
            f"  Prob: {self.your_probability:.0%} vs {self.market_probability:.0%} "
            f"(edge: {edge_pct:+.1f}%)\n"
            f"  Confidence: {self.confidence:.0%}"
        )


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
