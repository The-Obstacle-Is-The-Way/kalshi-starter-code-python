"""Simple sentiment analysis utilities for news articles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

import structlog

if TYPE_CHECKING:
    from collections.abc import Set

    from kalshi_research.exa.client import ExaClient

from kalshi_research.exa.models.common import SummaryOptions

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class SentimentResult:
    """Result of sentiment analysis."""

    score: float  # -1.0 (negative) to +1.0 (positive)
    label: str  # "positive", "negative", "neutral"
    confidence: float  # 0.0 to 1.0
    method: str  # Analysis method used
    keywords_matched: list[str]


class SentimentAnalyzer:
    """
    Simple keyword-based sentiment analyzer for financial/prediction-market context.

    This intentionally avoids heavy ML dependencies; it is deterministic and cheap.
    """

    POSITIVE_KEYWORDS: ClassVar[frozenset[str]] = frozenset(
        {
            # Market movement
            "surge",
            "soar",
            "rally",
            "bullish",
            "gains",
            "climbs",
            "jumps",
            "rises",
            "increases",
            "growth",
            "expansion",
            "acceleration",
            # Fundamentals
            "beat",
            "exceeds",
            "outperforms",
            "record",
            "breakthrough",
            "milestone",
            "success",
            "approval",
            "wins",
            "victory",
            "achieves",
            # Sentiment
            "optimism",
            "confidence",
            "positive",
            "favorable",
            "strong",
            "robust",
            "momentum",
            "upside",
            "opportunity",
            # Prediction specific
            "likely",
            "probable",
            "expected",
            "poised",
        }
    )

    NEGATIVE_KEYWORDS: ClassVar[frozenset[str]] = frozenset(
        {
            # Market movement
            "plunge",
            "crash",
            "tumble",
            "bearish",
            "losses",
            "falls",
            "drops",
            "declines",
            "decreases",
            "contraction",
            "slowdown",
            # Fundamentals
            "miss",
            "fails",
            "underperforms",
            "concern",
            "worry",
            "risk",
            "threat",
            "crisis",
            "collapse",
            "scandal",
            "fraud",
            # Sentiment
            "pessimism",
            "fear",
            "negative",
            "unfavorable",
            "weak",
            "fragile",
            "downside",
            "danger",
            "uncertainty",
            # Prediction specific
            "unlikely",
            "improbable",
            "doubtful",
            "delayed",
            "postponed",
        }
    )

    INTENSIFIERS: ClassVar[frozenset[str]] = frozenset(
        {"very", "extremely", "significantly", "sharply", "dramatically"}
    )
    NEGATORS: ClassVar[frozenset[str]] = frozenset(
        {"not", "no", "never", "neither", "hardly", "barely"}
    )

    def __init__(
        self,
        *,
        positive_weight: float = 1.0,
        negative_weight: float = 1.0,
        title_weight: float = 2.0,
    ) -> None:
        self.positive_weight = positive_weight
        self.negative_weight = negative_weight
        self.title_weight = title_weight

    def _tokenize(self, text: str) -> list[str]:
        text = text.lower()
        text = re.sub(r"[^\w\s']", " ", text)
        return text.split()

    def _count_keywords(self, tokens: list[str], keywords: Set[str]) -> tuple[float, list[str]]:
        matched: list[str] = []
        count = 0.0

        for i, token in enumerate(tokens):
            if token not in keywords:
                continue

            if i > 0 and tokens[i - 1] in self.NEGATORS:
                continue

            multiplier = 1.0
            if i > 0 and tokens[i - 1] in self.INTENSIFIERS:
                multiplier = 1.5

            count += multiplier
            matched.append(token)

        return count, matched

    def analyze(self, text: str, title: str | None = None) -> SentimentResult:
        """Analyze sentiment using a deterministic keyword-based heuristic."""
        all_matched: list[str] = []

        text_tokens = self._tokenize(text)
        pos_count, pos_matched = self._count_keywords(text_tokens, self.POSITIVE_KEYWORDS)
        neg_count, neg_matched = self._count_keywords(text_tokens, self.NEGATIVE_KEYWORDS)

        all_matched.extend(pos_matched)
        all_matched.extend(neg_matched)

        if title:
            title_tokens = self._tokenize(title)
            title_pos, title_pos_matched = self._count_keywords(
                title_tokens, self.POSITIVE_KEYWORDS
            )
            title_neg, title_neg_matched = self._count_keywords(
                title_tokens, self.NEGATIVE_KEYWORDS
            )
            pos_count += title_pos * self.title_weight
            neg_count += title_neg * self.title_weight
            all_matched.extend(title_pos_matched)
            all_matched.extend(title_neg_matched)

        pos_count *= self.positive_weight
        neg_count *= self.negative_weight

        total = pos_count + neg_count
        if total <= 0:
            score = 0.0
            confidence = 0.3
        else:
            score = (pos_count - neg_count) / total
            confidence = min(0.5 + (total * 0.1), 0.95)

        if score > 0.1:
            label = "positive"
        elif score < -0.1:
            label = "negative"
        else:
            label = "neutral"

        return SentimentResult(
            score=score,
            label=label,
            confidence=confidence,
            method="keyword",
            keywords_matched=sorted(set(all_matched)),
        )


class SummarySentimentAnalyzer:
    """
    Alternative analyzer that uses Exa summaries with a sentiment prompt.

    More accurate but requires extra API work; intended for opt-in usage.
    """

    def __init__(self, exa: ExaClient) -> None:
        self._exa = exa

    async def analyze(self, url: str) -> SentimentResult:
        """Analyze sentiment for a URL using Exa summaries + a prompt."""
        response = await self._exa.get_contents(
            [url],
            summary=SummaryOptions(
                query=(
                    "Analyze the sentiment of this article. Is it positive, negative, or neutral? "
                    "Return the sentiment label and a 1-sentence explanation."
                )
            ),
        )

        if not response.results:
            return SentimentResult(
                score=0.0,
                label="neutral",
                confidence=0.3,
                method="summary_failed",
                keywords_matched=[],
            )

        summary = (response.results[0].summary or "").lower()
        if "positive" in summary or "bullish" in summary:
            return SentimentResult(
                score=0.6,
                label="positive",
                confidence=0.7,
                method="summary",
                keywords_matched=["positive"],
            )
        if "negative" in summary or "bearish" in summary:
            return SentimentResult(
                score=-0.6,
                label="negative",
                confidence=0.7,
                method="summary",
                keywords_matched=["negative"],
            )

        return SentimentResult(
            score=0.0,
            label="neutral",
            confidence=0.6,
            method="summary",
            keywords_matched=["neutral"],
        )
