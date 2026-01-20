"""Research-enhanced thesis operations backed by Exa."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import structlog

from kalshi_research.exa.policy import ExaBudget, ExaPolicy, extract_exa_cost_total
from kalshi_research.research.thesis import ThesisEvidence

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market
    from kalshi_research.exa.client import ExaClient
    from kalshi_research.exa.models.search import SearchResponse

logger = structlog.get_logger()


@dataclass(frozen=True)
class ResearchedThesisData:
    """Data gathered for thesis creation."""

    suggested_bull_case: str
    suggested_bear_case: str
    bull_evidence: list[ThesisEvidence]
    bear_evidence: list[ThesisEvidence]
    neutral_evidence: list[ThesisEvidence]
    summary: str
    exa_cost_dollars: float
    budget_usd: float
    budget_spent_usd: float
    budget_exhausted: bool


class ThesisResearcher:
    """Gather and classify evidence to support thesis creation."""

    def __init__(
        self,
        exa: ExaClient,
        *,
        max_sources: int = 15,
        recent_days: int = 30,
        policy: ExaPolicy | None = None,
    ) -> None:
        self._exa = exa
        self._max_sources = max_sources
        self._recent_days = recent_days
        self._policy = policy or ExaPolicy.from_mode()

    async def _search_evidence(
        self,
        query: str,
        *,
        cutoff: datetime,
        budget: ExaBudget,
        num_results: int,
    ) -> tuple[SearchResponse | None, bool]:
        include_text = self._policy.include_full_text
        include_highlights = True

        estimated_cost = self._policy.estimate_search_cost_usd(
            num_results=num_results,
            include_text=include_text,
            include_highlights=include_highlights,
            search_type=self._policy.exa_search_type,
        )
        if not budget.can_spend(estimated_cost):
            return (None, True)

        try:
            response = await self._exa.search(
                query,
                search_type=self._policy.exa_search_type,
                num_results=num_results,
                text=include_text,
                highlights=include_highlights,
                category="news",
                start_published_date=cutoff,
            )
        except Exception as exc:
            logger.warning(
                "Thesis evidence search failed",
                query=query,
                error=str(exc),
                exc_info=True,
            )
            return (None, False)

        budget.record_spend(extract_exa_cost_total(response))
        return (response, False)

    async def _get_summary(self, prompt: str, *, budget: ExaBudget) -> tuple[str | None, bool]:
        if not self._policy.include_answer:
            return (None, False)

        estimated_cost = self._policy.estimate_answer_cost_usd(include_text=True)
        if not budget.can_spend(estimated_cost):
            return (None, True)

        try:
            answer = await self._exa.answer(prompt, text=True)
        except Exception as exc:
            logger.warning("Thesis summary generation failed", error=str(exc), exc_info=True)
            return (None, False)

        budget.record_spend(extract_exa_cost_total(answer))
        return (answer.answer, False)

    def _extract_domain(self, url: str) -> str:
        return urlparse(url).netloc.replace("www.", "")

    def _classify_evidence(self, text: str, title: str, *, thesis_direction: str) -> str:
        """Classify evidence as bull, bear, or neutral."""
        text_lower = (text + " " + title).lower()

        positive = sum(
            signal in text_lower
            for signal in (
                "surge",
                "rally",
                "gain",
                "rise",
                "bullish",
                "optimis",
                "beat",
                "exceed",
                "success",
                "approve",
                "confirm",
            )
        )
        negative = sum(
            signal in text_lower
            for signal in (
                "fall",
                "drop",
                "crash",
                "decline",
                "bearish",
                "pessimis",
                "miss",
                "fail",
                "reject",
                "delay",
                "concern",
                "risk",
            )
        )

        if positive > negative + 1:
            return "bull" if thesis_direction == "yes" else "bear"
        if negative > positive + 1:
            return "bear" if thesis_direction == "yes" else "bull"
        return "neutral"

    def _generate_case_summary(self, evidence: list[ThesisEvidence], *, case_type: str) -> str:
        if not evidence:
            return f"No {case_type} case evidence found."

        points = [f"• {e.snippet[:150]}... ({e.source_domain})" for e in evidence[:3]]
        return "\n".join(points)

    async def research_for_thesis(
        self,
        market: Market,
        *,
        thesis_direction: str,
    ) -> ResearchedThesisData:
        """Gather and classify Exa evidence to support thesis creation."""
        cutoff = datetime.now(UTC) - timedelta(days=self._recent_days)
        budget = ExaBudget(limit_usd=self._policy.budget_usd)
        budget_exhausted = False

        title = market.title.replace("Will ", "").replace("?", "").strip()
        queries = [title, f"{title} analysis", f"{title} prediction"]

        bull_evidence: list[ThesisEvidence] = []
        bear_evidence: list[ThesisEvidence] = []
        neutral_evidence: list[ThesisEvidence] = []

        num_results = max(1, self._max_sources // 2)
        for query in queries[:2]:
            response, exhausted = await self._search_evidence(
                query,
                cutoff=cutoff,
                budget=budget,
                num_results=num_results,
            )
            if exhausted:
                budget_exhausted = True
                break
            if response is None:
                continue

            for result in response.results:
                snippet = ""
                if result.highlights:
                    snippet = result.highlights[0]
                elif result.text:
                    snippet = result.text[:300]

                supports = self._classify_evidence(
                    result.text or "",
                    result.title,
                    thesis_direction=thesis_direction,
                )
                evidence = ThesisEvidence(
                    url=result.url,
                    title=result.title,
                    source_domain=self._extract_domain(result.url),
                    published_date=result.published_date,
                    snippet=snippet,
                    supports=supports,
                    relevance_score=(result.score if result.score is not None else 0.8),
                )

                if supports == "bull":
                    bull_evidence.append(evidence)
                elif supports == "bear":
                    bear_evidence.append(evidence)
                else:
                    neutral_evidence.append(evidence)

        suggested_bull = self._generate_case_summary(bull_evidence, case_type="bull")
        suggested_bear = self._generate_case_summary(bear_evidence, case_type="bear")

        summary_prompt = f"What is the outlook for: {title}? Summarize the key factors."
        summary = "Research summary unavailable."
        summary_text, exhausted = await self._get_summary(summary_prompt, budget=budget)
        if exhausted:
            budget_exhausted = True
        if summary_text is not None:
            summary = summary_text

        return ResearchedThesisData(
            suggested_bull_case=suggested_bull,
            suggested_bear_case=suggested_bear,
            bull_evidence=bull_evidence,
            bear_evidence=bear_evidence,
            neutral_evidence=neutral_evidence,
            summary=summary,
            exa_cost_dollars=budget.spent_usd,
            budget_usd=self._policy.budget_usd,
            budget_spent_usd=budget.spent_usd,
            budget_exhausted=budget_exhausted,
        )


@dataclass(frozen=True)
class ThesisSuggestion:
    """A lightweight thesis idea derived from a source article."""

    source_title: str
    source_url: str
    key_insight: str
    suggested_thesis: str
    confidence: str


class ThesisSuggester:
    """Generate thesis ideas from recent research coverage."""

    def __init__(self, exa: ExaClient, *, policy: ExaPolicy | None = None) -> None:
        self._exa = exa
        self._policy = policy or ExaPolicy.from_mode()
        self._budget = ExaBudget(limit_usd=self._policy.budget_usd)
        self._budget_exhausted = False

    @property
    def budget(self) -> ExaBudget:
        return self._budget

    @property
    def budget_exhausted(self) -> bool:
        return self._budget_exhausted

    def _extract_thesis_idea(self, title: str) -> str:
        title_clean = title.replace("Will ", "").replace("?", "").strip()
        return f"{title_clean} - thesis opportunity based on recent coverage"

    async def suggest_theses(self, *, category: str | None = None) -> list[ThesisSuggestion]:
        """Suggest lightweight thesis ideas from recent Exa search coverage."""
        search_query = "prediction market opportunities"
        if category:
            search_query = f"{category} {search_query}"

        include_text = self._policy.include_full_text
        include_highlights = True
        estimated_cost = self._policy.estimate_search_cost_usd(
            num_results=10,
            include_text=include_text,
            include_highlights=include_highlights,
            search_type=self._policy.exa_search_type,
        )
        if not self._budget.can_spend(estimated_cost):
            self._budget_exhausted = True
            return []

        try:
            response = await self._exa.search(
                search_query,
                num_results=10,
                search_type=self._policy.exa_search_type,
                text=include_text,
                highlights=include_highlights,
                category="news",
            )
        except Exception as e:
            logger.error("Thesis suggestion search failed", error=str(e), exc_info=True)
            return []
        self._budget.record_spend(extract_exa_cost_total(response))

        suggestions: list[ThesisSuggestion] = []
        for result in response.results[:5]:
            key_insight = ""
            if result.highlights:
                key_insight = result.highlights[0]
            elif result.text:
                key_insight = result.text[:200]

            suggestions.append(
                ThesisSuggestion(
                    source_title=result.title,
                    source_url=result.url,
                    key_insight=key_insight,
                    suggested_thesis=self._extract_thesis_idea(result.title),
                    confidence="medium",
                )
            )

        return suggestions
