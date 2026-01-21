"""Detect potential thesis invalidation signals using Exa."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import structlog

from kalshi_research.exa.policy import ExaBudget, ExaPolicy, extract_exa_cost_total

if TYPE_CHECKING:
    from kalshi_research.exa.client import ExaClient
    from kalshi_research.research.thesis import Thesis

logger = structlog.get_logger()


class InvalidationSeverity(str, Enum):
    """Severity of invalidation signal."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class InvalidationSignal:
    """A signal that might invalidate a thesis."""

    severity: InvalidationSeverity
    title: str
    url: str
    source_domain: str
    published_at: datetime | None
    reason: str
    snippet: str


@dataclass(frozen=True)
class InvalidationReport:
    """Report on potential invalidation signals."""

    thesis_id: str
    thesis_title: str
    checked_at: datetime
    signals: list[InvalidationSignal]
    recommendation: str | None

    @property
    def has_high_severity(self) -> bool:
        """Return `True` if any signal in the report is high severity."""
        return any(s.severity == InvalidationSeverity.HIGH for s in self.signals)


class InvalidationDetector:
    """Search for recent news that may contradict a thesis."""

    def __init__(
        self,
        exa: ExaClient,
        *,
        lookback_hours: int = 48,
        policy: ExaPolicy | None = None,
    ) -> None:
        self._exa = exa
        self._lookback_hours = lookback_hours
        self._policy = policy or ExaPolicy.from_mode()
        self._budget = ExaBudget(limit_usd=self._policy.budget_usd)
        self._budget_exhausted = False

    @property
    def budget(self) -> ExaBudget:
        return self._budget

    @property
    def budget_exhausted(self) -> bool:
        return self._budget_exhausted

    async def check_thesis(self, thesis: Thesis) -> InvalidationReport:
        """Search recent news for signals that might invalidate a thesis."""
        cutoff = datetime.now(UTC) - timedelta(hours=self._lookback_hours)
        signals: list[InvalidationSignal] = []

        base_query = thesis.title.replace("Will ", "").replace("?", "").strip()
        queries = [f"{base_query} news today"]

        if thesis.your_probability > 0.5:
            queries.append(f"{base_query} fails OR delays OR rejects OR concerns")
        else:
            queries.append(f"{base_query} succeeds OR approves OR confirms OR breakthrough")

        for assumption in thesis.key_assumptions[:2]:
            queries.append(f"{assumption} news")

        for query in queries[:3]:
            include_text = self._policy.include_full_text
            include_highlights = True
            estimated_cost = self._policy.estimate_search_cost_usd(
                num_results=5,
                include_text=include_text,
                include_highlights=include_highlights,
                search_type=self._policy.exa_search_type,
            )
            if not self._budget.can_spend(estimated_cost):
                self._budget_exhausted = True
                logger.info(
                    "Thesis invalidation check budget exhausted",
                    budget_spent_usd=self._budget.spent_usd,
                    budget_limit_usd=self._budget.limit_usd,
                )
                break

            try:
                response = await self._exa.search(
                    query,
                    num_results=5,
                    search_type=self._policy.exa_search_type,
                    text=include_text,
                    highlights=include_highlights,
                    category="news",
                    start_published_date=cutoff,
                )
                self._budget.record_spend(extract_exa_cost_total(response))
            except Exception as e:
                logger.warning(
                    "Invalidation search failed",
                    query=query,
                    error=str(e),
                    exc_info=True,
                )
                continue

            for result in response.results:
                signal = self._analyze_for_invalidation(
                    thesis,
                    title=result.title,
                    text=result.text or "",
                    url=result.url,
                    published_at=result.published_date,
                )
                if signal:
                    signals.append(signal)

        deduped = self._dedupe(signals)
        deduped.sort(key=lambda s: self._severity_rank(s.severity))

        recommendation = self._generate_recommendation(deduped)
        return InvalidationReport(
            thesis_id=thesis.id,
            thesis_title=thesis.title,
            checked_at=datetime.now(UTC),
            signals=deduped,
            recommendation=recommendation,
        )

    def _analyze_for_invalidation(
        self,
        thesis: Thesis,
        *,
        title: str,
        text: str,
        url: str,
        published_at: datetime | None,
    ) -> InvalidationSignal | None:
        combined = (title + " " + text).lower()

        for criterion in thesis.invalidation_criteria:
            criterion_lower = criterion.lower()
            words = [w for w in criterion_lower.split() if w]
            if not words:
                continue
            matches = sum(1 for w in words if w in combined)
            if matches >= max(1, len(words) // 2):
                return InvalidationSignal(
                    severity=InvalidationSeverity.HIGH,
                    title=title,
                    url=url,
                    source_domain=self._extract_domain(url),
                    published_at=published_at,
                    reason=f"Matches invalidation criterion: '{criterion}'",
                    snippet=text[:200],
                )

        is_bullish = thesis.your_probability > 0.5
        bearish = ("fails", "rejects", "delays", "crashes", "plunges", "concerns", "risks")
        bullish = ("succeeds", "approves", "confirms", "surges", "rallies", "breakthrough")
        contradicting = bearish if is_bullish else bullish

        contradiction_count = sum(kw in combined for kw in contradicting)
        if contradiction_count >= 2:
            return InvalidationSignal(
                severity=InvalidationSeverity.MEDIUM,
                title=title,
                url=url,
                source_domain=self._extract_domain(url),
                published_at=published_at,
                reason="News sentiment contradicts thesis direction",
                snippet=text[:200],
            )

        return None

    def _generate_recommendation(self, signals: list[InvalidationSignal]) -> str:
        if not signals:
            return "No significant invalidation signals found. Thesis appears stable."

        high_count = sum(1 for s in signals if s.severity == InvalidationSeverity.HIGH)
        medium_count = sum(1 for s in signals if s.severity == InvalidationSeverity.MEDIUM)

        if high_count:
            return (
                f"Found {high_count} high-severity signals. Review thesis assumptions and consider "
                "updating probability or adding an update note."
            )
        if medium_count:
            return (
                f"Found {medium_count} medium-severity signals. Consider reviewing for new risks "
                "or updates."
            )
        return "Only low-severity signals found. Monitor for changes."

    def _dedupe(self, signals: list[InvalidationSignal]) -> list[InvalidationSignal]:
        seen: set[str] = set()
        unique: list[InvalidationSignal] = []
        for s in signals:
            if s.url in seen:
                continue
            seen.add(s.url)
            unique.append(s)
        return unique

    def _severity_rank(self, severity: InvalidationSeverity) -> int:
        match severity:
            case InvalidationSeverity.HIGH:
                return 0
            case InvalidationSeverity.MEDIUM:
                return 1
            case InvalidationSeverity.LOW:
                return 2

    def _extract_domain(self, url: str) -> str:
        return urlparse(url).netloc.replace("www.", "")
