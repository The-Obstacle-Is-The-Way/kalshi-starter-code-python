# SPEC-023: Exa-Thesis Integration

**Status:** 📋 Planned
**Priority:** P1 (Core workflow enhancement)
**Estimated Complexity:** Medium
**Dependencies:** SPEC-020, SPEC-021

---

## 1. Overview

Connect Exa research directly into the thesis creation and management workflow. When you create a thesis, automatically gather supporting evidence. When you review a thesis, check for new relevant information that might invalidate or strengthen your position.

### 1.1 Goals

- Auto-populate bull/bear cases with real sources during thesis creation
- Store research evidence alongside theses
- Check for invalidation signals (new information that contradicts thesis)
- Generate thesis ideas from Exa research
- CLI integration for seamless workflow

### 1.2 Non-Goals

- Automatic thesis resolution (human decision required)
- Automated trading based on research
- Real-time thesis monitoring (use alerts for that)
- Full agentic reasoning (that's SPEC-024)

---

## 2. Use Cases

### 2.1 Researched Thesis Creation

```bash
# Create thesis with automatic research
uv run kalshi research thesis create "Bitcoin exceeds 100k" \
    --markets KXBTC-26JAN-T100000 \
    --your-prob 0.65 \
    --with-research

# Output:
# 🔍 Researching thesis...
#
# 📰 Found 12 relevant sources
#
# Suggested Bull Case (from sources):
# • ETF inflows reached record $1.2B this week (CoinDesk)
# • Institutional adoption accelerating per Fidelity report
# • Historical pattern: BTC typically rallies in January
#
# Suggested Bear Case (from sources):
# • SEC regulatory uncertainty continues
# • Macroeconomic headwinds from potential rate changes
#
# Accept these suggestions? [Y/n/edit]
#
# ✓ Thesis created: btc-100k-jan
#   Research attached: 12 sources
```

### 2.2 Thesis Invalidation Check

```bash
# Check if new information invalidates your thesis
uv run kalshi research thesis check-invalidation btc-100k

# Output:
# Thesis: Bitcoin exceeds 100k by January 26
# Your probability: 65% YES
# Current market: 52% YES
#
# ⚠️ Potential Invalidation Signals
# ─────────────────────────────────
# [HIGH] "SEC Delays Bitcoin ETF Decision" (2 hours ago)
#   > This directly relates to your key assumption about
#   > regulatory clarity. Consider updating your thesis.
#
# [MEDIUM] "Fed Signals Potential Rate Hike" (yesterday)
#   > Contradicts assumption about dovish monetary policy.
#
# Recommendation: Review thesis. Consider lowering probability
# or adding update note with your reasoning.
```

### 2.3 Thesis Idea Generation

```bash
# Generate thesis ideas from research
uv run kalshi research thesis suggest --category "crypto"

# Output:
# 🎯 Thesis Suggestions Based on Research
# ─────────────────────────────────────────
#
# 1. Ethereum ETF Approval by March
#    Market: KXETH-APR-ETF
#    Current: 35% | Research suggests: 45-50%
#    Key insight: "SEC staff reportedly reviewing..." (Bloomberg)
#
# 2. Bitcoin Mining Difficulty Increase
#    Market: KXBTC-DIFF-FEB
#    Current: 60% | Research suggests: 70-75%
#    Key insight: "Hash rate reaching all-time highs..." (CoinDesk)
```

---

## 3. Technical Specification

### 3.1 Module Structure

```
src/kalshi_research/
├── research/
│   ├── thesis.py           # (existing) - Add evidence fields (persisted in theses JSON)
│   ├── thesis_research.py  # NEW: Research-enhanced thesis operations
│   └── invalidation.py     # NEW: Invalidation detection
```

**Persistence (SSOT):** Theses are currently stored in `data/theses.json` via `ThesisTracker`. This spec stores
research evidence **inside the existing thesis JSON schema** (no SQLite tables or Alembic migrations in-scope).

### 3.2 Enhanced Thesis Model

```python
# src/kalshi_research/research/thesis.py (modifications)
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class ThesisEvidence:
    """Evidence supporting or opposing a thesis."""

    url: str
    title: str
    source_domain: str
    published_date: datetime | None
    snippet: str
    supports: str  # "bull", "bear", or "neutral"
    relevance_score: float
    added_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Thesis:
    """Extended thesis with research evidence."""

    # ... existing fields ...

    # NEW: Research evidence
    evidence: list[ThesisEvidence] = field(default_factory=list)
    research_summary: str | None = None
    last_research_at: datetime | None = None

    def add_evidence(
        self,
        evidence: ThesisEvidence,
    ) -> None:
        """Add research evidence to thesis."""
        self.evidence.append(evidence)
        self.last_research_at = datetime.now(UTC)

    def get_bull_evidence(self) -> list[ThesisEvidence]:
        """Get evidence supporting YES outcome."""
        return [e for e in self.evidence if e.supports == "bull"]

    def get_bear_evidence(self) -> list[ThesisEvidence]:
        """Get evidence supporting NO outcome."""
        return [e for e in self.evidence if e.supports == "bear"]

    def to_dict(self) -> dict[str, Any]:
        """Serialize including evidence."""
        base = {
            # ... existing fields ...
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
        base["last_research_at"] = self.last_research_at.isoformat() if self.last_research_at else None
        return base
```

Also update `Thesis.from_dict` to parse these new optional fields and keep backward compatibility with existing
saved theses (missing keys must not raise):

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Thesis:
    evidence_raw = data.get("evidence", [])
    evidence: list[ThesisEvidence] = []
    for item in evidence_raw:
        if not isinstance(item, dict):
            continue
        published = item.get("published_date")
        added = item.get("added_at")
        evidence.append(
            ThesisEvidence(
                url=str(item.get("url", "")),
                title=str(item.get("title", "")),
                source_domain=str(item.get("source_domain", "")),
                published_date=datetime.fromisoformat(published) if published else None,
                snippet=str(item.get("snippet", "")),
                supports=str(item.get("supports", "neutral")),
                relevance_score=float(item.get("relevance_score", 0.0)),
                added_at=datetime.fromisoformat(added) if added else datetime.now(UTC),
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
        status=ThesisStatus(data.get("status", "draft")),
        created_at=datetime.fromisoformat(data["created_at"]),
        resolved_at=(datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None),
        actual_outcome=data.get("actual_outcome"),
        updates=data.get("updates", []),
    )
    thesis.evidence = evidence
    thesis.research_summary = data.get("research_summary")
    last = data.get("last_research_at")
    thesis.last_research_at = datetime.fromisoformat(last) if last else None
    return thesis
```

### 3.3 Thesis Researcher

```python
# src/kalshi_research/research/thesis_research.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market
    from kalshi_research.exa.client import ExaClient
    from kalshi_research.research.thesis import Thesis, ThesisEvidence

logger = structlog.get_logger()


@dataclass
class ResearchedThesisData:
    """Data gathered for thesis creation."""

    suggested_bull_case: str
    suggested_bear_case: str
    bull_evidence: list[ThesisEvidence]
    bear_evidence: list[ThesisEvidence]
    neutral_evidence: list[ThesisEvidence]
    summary: str
    exa_cost_dollars: float


class ThesisResearcher:
    """
    Research-enhanced thesis operations.

    Combines Exa research with thesis management to:
    - Gather evidence during thesis creation
    - Classify sources as bull/bear
    - Generate thesis suggestions
    """

    def __init__(
        self,
        exa: ExaClient,
        *,
        max_sources: int = 15,
        recent_days: int = 30,
    ) -> None:
        """
        Initialize the researcher.

        Args:
            exa: Initialized ExaClient
            max_sources: Maximum sources to gather
            recent_days: How far back to search
        """
        self.exa = exa
        self.max_sources = max_sources
        self.recent_days = recent_days

    def _classify_evidence(
        self,
        text: str,
        title: str,
        thesis_direction: str,  # "yes" or "no"
    ) -> str:
        """
        Classify evidence as bull, bear, or neutral.

        Simple heuristic based on keywords and thesis direction.
        """
        text_lower = (text + " " + title).lower()

        # Positive indicators
        positive_signals = sum([
            "surge" in text_lower,
            "rally" in text_lower,
            "gain" in text_lower,
            "rise" in text_lower,
            "bullish" in text_lower,
            "optimis" in text_lower,
            "beat" in text_lower,
            "exceed" in text_lower,
            "success" in text_lower,
            "approve" in text_lower,
        ])

        # Negative indicators
        negative_signals = sum([
            "fall" in text_lower,
            "drop" in text_lower,
            "crash" in text_lower,
            "decline" in text_lower,
            "bearish" in text_lower,
            "pessimis" in text_lower,
            "miss" in text_lower,
            "fail" in text_lower,
            "reject" in text_lower,
            "delay" in text_lower,
        ])

        # Determine classification
        if positive_signals > negative_signals + 1:
            return "bull" if thesis_direction == "yes" else "bear"
        elif negative_signals > positive_signals + 1:
            return "bear" if thesis_direction == "yes" else "bull"
        else:
            return "neutral"

    async def research_for_thesis(
        self,
        market: Market,
        thesis_direction: str = "yes",  # Which side you're taking
    ) -> ResearchedThesisData:
        """
        Gather research evidence for thesis creation.

        Args:
            market: The Kalshi market
            thesis_direction: "yes" or "no" (your position)

        Returns:
            ResearchedThesisData with categorized evidence
        """
        from datetime import timedelta
        from kalshi_research.research.thesis import ThesisEvidence

        cutoff = datetime.now(UTC) - timedelta(days=self.recent_days)
        total_cost = 0.0

        # Generate search queries from market
        title = market.title.replace("Will ", "").replace("?", "")
        queries = [
            title,
            f"{title} analysis",
            f"{title} prediction",
        ]

        bull_evidence: list[ThesisEvidence] = []
        bear_evidence: list[ThesisEvidence] = []
        neutral_evidence: list[ThesisEvidence] = []

        # Search for news
        for query in queries[:2]:
            try:
                response = await self.exa.search(
                    query,
                    num_results=self.max_sources // 2,
                    text=True,
                    highlights=True,
                    category="news",
                    start_published_date=cutoff,
                )

                for result in response.results:
                    snippet = result.highlights[0] if result.highlights else (result.text[:300] if result.text else "")
                    classification = self._classify_evidence(
                        result.text or "",
                        result.title,
                        thesis_direction,
                    )

                    evidence = ThesisEvidence(
                        url=result.url,
                        title=result.title,
                        source_domain=self._extract_domain(result.url),
                        published_date=result.published_date,
                        snippet=snippet,
                        supports=classification,
                        relevance_score=result.score if result.score is not None else 0.8,
                    )

                    if classification == "bull":
                        bull_evidence.append(evidence)
                    elif classification == "bear":
                        bear_evidence.append(evidence)
                    else:
                        neutral_evidence.append(evidence)

                if response.cost_dollars:
                    total_cost += response.cost_dollars.total

            except Exception as e:
                logger.warning("Search failed", query=query, error=str(e))

        # Generate suggested cases from evidence
        suggested_bull = self._generate_case_summary(bull_evidence, "bull")
        suggested_bear = self._generate_case_summary(bear_evidence, "bear")

        # Get an overall summary using Exa Answer
        try:
            answer_response = await self.exa.answer(
                f"What is the outlook for: {title}? Summarize the key factors.",
                text=True,
            )
            summary = answer_response.answer
            if answer_response.cost_dollars:
                total_cost += answer_response.cost_dollars.total
        except Exception:
            summary = "Research summary unavailable."

        return ResearchedThesisData(
            suggested_bull_case=suggested_bull,
            suggested_bear_case=suggested_bear,
            bull_evidence=bull_evidence,
            bear_evidence=bear_evidence,
            neutral_evidence=neutral_evidence,
            summary=summary,
            exa_cost_dollars=total_cost,
        )

    def _generate_case_summary(
        self,
        evidence: list[ThesisEvidence],
        case_type: str,
    ) -> str:
        """Generate a summary from evidence snippets."""
        if not evidence:
            return f"No {case_type} case evidence found."

        points = []
        for e in evidence[:3]:  # Top 3 sources
            points.append(f"• {e.snippet[:150]}... ({e.source_domain})")

        return "\n".join(points)

    def _extract_domain(self, url: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")


class ThesisSuggester:
    """
    Generate thesis ideas from research.
    """

    def __init__(
        self,
        exa: ExaClient,
    ) -> None:
        self.exa = exa

    async def suggest_theses(
        self,
        category: str | None = None,
        markets: list[Market] | None = None,
    ) -> list[dict]:
        """
        Generate thesis suggestions based on research.

        Args:
            category: Optional category filter (crypto, politics, etc.)
            markets: Optional list of markets to analyze

        Returns:
            List of thesis suggestions with supporting evidence
        """
        suggestions = []

        # Strategy: Use Exa to find recent developments,
        # then match to markets that might be mispriced

        search_query = "prediction market opportunities"
        if category:
            search_query = f"{category} {search_query}"

        try:
            response = await self.exa.search(
                search_query,
                num_results=10,
                text=True,
                highlights=True,
                category="news",
            )

            for result in response.results:
                # Extract potential thesis from article
                suggestion = {
                    "source_title": result.title,
                    "source_url": result.url,
                    "key_insight": result.highlights[0] if result.highlights else result.text[:200],
                    "suggested_thesis": self._extract_thesis_idea(result.text or "", result.title),
                    "confidence": "medium",
                }
                suggestions.append(suggestion)

        except Exception as e:
            logger.error("Suggestion search failed", error=str(e))

        return suggestions[:5]

    def _extract_thesis_idea(self, text: str, title: str) -> str:
        """Extract a potential thesis statement from article content."""
        # Simple heuristic: use title as thesis base
        title_clean = title.replace("Will ", "").replace("?", "")
        return f"{title_clean} - thesis opportunity based on recent coverage"
```

### 3.4 Invalidation Detector

```python
# src/kalshi_research/research/invalidation.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from kalshi_research.exa.client import ExaClient
    from kalshi_research.research.thesis import Thesis

logger = structlog.get_logger()


class InvalidationSeverity(str, Enum):
    """Severity of invalidation signal."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class InvalidationSignal:
    """A signal that might invalidate a thesis."""

    severity: InvalidationSeverity
    title: str
    url: str
    source_domain: str
    published_at: datetime | None
    reason: str  # Why this might invalidate
    snippet: str


@dataclass
class InvalidationReport:
    """Report on potential invalidation signals."""

    thesis_id: str
    thesis_title: str
    checked_at: datetime
    signals: list[InvalidationSignal]
    recommendation: str | None

    @property
    def has_high_severity(self) -> bool:
        return any(s.severity == InvalidationSeverity.HIGH for s in self.signals)


class InvalidationDetector:
    """
    Detect signals that might invalidate a thesis.

    Looks for:
    - News that contradicts key assumptions
    - Significant events related to thesis
    - Changes in fundamental factors
    """

    def __init__(
        self,
        exa: ExaClient,
        *,
        lookback_hours: int = 48,
    ) -> None:
        self.exa = exa
        self.lookback_hours = lookback_hours

    async def check_thesis(self, thesis: Thesis) -> InvalidationReport:
        """
        Check a thesis for invalidation signals.

        Args:
            thesis: The thesis to check

        Returns:
            InvalidationReport with any signals found
        """
        signals: list[InvalidationSignal] = []
        cutoff = datetime.now(UTC) - timedelta(hours=self.lookback_hours)

        # Search for recent news related to thesis
        # Focus on potential negative developments if thesis is bullish (and vice versa)

        # Generate queries based on key assumptions
        queries = []

        # Query 1: Direct topic search
        base_query = thesis.title.replace("Will ", "").replace("?", "")
        queries.append(f"{base_query} news today")

        # Query 2: Search for contradicting news
        if thesis.your_probability > 0.5:
            # Bullish thesis - look for bearish news
            queries.append(f"{base_query} fails OR delays OR rejects OR concerns")
        else:
            # Bearish thesis - look for bullish news
            queries.append(f"{base_query} succeeds OR approves OR confirms OR breakthrough")

        # Query 3: Key assumptions
        for assumption in thesis.key_assumptions[:2]:
            queries.append(f"{assumption} news")

        for query in queries[:3]:
            try:
                response = await self.exa.search(
                    query,
                    num_results=5,
                    text=True,
                    highlights=True,
                    category="news",
                    start_published_date=cutoff,
                )

                for result in response.results:
                    signal = self._analyze_for_invalidation(
                        thesis,
                        result.title,
                        result.text or "",
                        result.url,
                        result.published_date,
                    )
                    if signal:
                        signals.append(signal)

            except Exception as e:
                logger.warning("Invalidation search failed", query=query, error=str(e))

        # Deduplicate by URL
        seen_urls = set()
        unique_signals = []
        for signal in signals:
            if signal.url not in seen_urls:
                seen_urls.add(signal.url)
                unique_signals.append(signal)

        # Sort by severity
        severity_order = {InvalidationSeverity.HIGH: 0, InvalidationSeverity.MEDIUM: 1, InvalidationSeverity.LOW: 2}
        unique_signals.sort(key=lambda s: severity_order[s.severity])

        # Generate recommendation
        recommendation = self._generate_recommendation(thesis, unique_signals)

        return InvalidationReport(
            thesis_id=thesis.id,
            thesis_title=thesis.title,
            checked_at=datetime.now(UTC),
            signals=unique_signals,
            recommendation=recommendation,
        )

    def _analyze_for_invalidation(
        self,
        thesis: Thesis,
        title: str,
        text: str,
        url: str,
        published_at: datetime | None,
    ) -> InvalidationSignal | None:
        """
        Analyze if an article invalidates the thesis.

        Returns signal if invalidation detected, None otherwise.
        """
        combined = (title + " " + text).lower()

        # Check invalidation criteria
        for criterion in thesis.invalidation_criteria:
            criterion_lower = criterion.lower()
            # Simple keyword matching
            criterion_words = criterion_lower.split()
            matches = sum(1 for word in criterion_words if word in combined)

            if matches >= len(criterion_words) // 2:
                return InvalidationSignal(
                    severity=InvalidationSeverity.HIGH,
                    title=title,
                    url=url,
                    source_domain=self._extract_domain(url),
                    published_at=published_at,
                    reason=f"Matches invalidation criterion: '{criterion}'",
                    snippet=text[:200],
                )

        # Check for contradicting sentiment
        # If thesis is bullish (prob > 0.5), look for bearish news
        is_bullish_thesis = thesis.your_probability > 0.5

        bearish_keywords = ["fails", "rejects", "delays", "crashes", "plunges", "concerns", "risks"]
        bullish_keywords = ["succeeds", "approves", "confirms", "surges", "rallies", "breakthrough"]

        if is_bullish_thesis:
            contradicting = bearish_keywords
        else:
            contradicting = bullish_keywords

        contradiction_count = sum(1 for kw in contradicting if kw in combined)

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

    def _generate_recommendation(
        self,
        thesis: Thesis,
        signals: list[InvalidationSignal],
    ) -> str | None:
        """Generate a recommendation based on signals."""
        if not signals:
            return "No significant invalidation signals found. Thesis appears stable."

        high_count = sum(1 for s in signals if s.severity == InvalidationSeverity.HIGH)
        medium_count = sum(1 for s in signals if s.severity == InvalidationSeverity.MEDIUM)

        if high_count >= 2:
            return "URGENT: Multiple high-severity signals. Consider resolving or significantly revising thesis."
        elif high_count == 1:
            return "Review recommended: High-severity signal detected. Update thesis with your analysis."
        elif medium_count >= 3:
            return "Consider review: Multiple medium-severity signals accumulated."
        else:
            return "Minor signals detected. Monitor but no immediate action needed."

    def _extract_domain(self, url: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
```

### 3.5 CLI Enhancements

```python
# src/kalshi_research/cli/research.py (additions)

@thesis_app.command("create")
def research_thesis_create(
    title: Annotated[str, typer.Argument(help="Thesis title")],
    markets: Annotated[str, typer.Option("--markets", "-m", help="Comma-separated market tickers")],
    your_prob: Annotated[float, typer.Option("--your-prob", help="Your probability (0-1)")],
    market_prob: Annotated[float, typer.Option("--market-prob", help="Market probability (0-1)")],
    confidence: Annotated[float, typer.Option("--confidence", help="Your confidence (0-1)")],
    with_research: Annotated[bool, typer.Option("--with-research", "-r", help="Auto-research evidence")] = False,
    bull_case: Annotated[str, typer.Option("--bull", help="Bull case")] = "Why YES",
    bear_case: Annotated[str, typer.Option("--bear", help="Bear case")] = "Why NO",
) -> None:
    """
    Create a new research thesis.

    With --with-research, automatically gathers supporting evidence from Exa.

    Examples:
        kalshi research thesis create "BTC 100k" -m KXBTC-26JAN-T100000 --your-prob 0.65 --market-prob 0.52
        kalshi research thesis create "BTC 100k" -m KXBTC-26JAN-T100000 --your-prob 0.65 --market-prob 0.52 --with-research
    """
    from kalshi_research.api import KalshiPublicClient

    async def _create() -> None:
        import uuid

        market_tickers = [t.strip() for t in markets.split(",")]
        final_bull = bull_case
        final_bear = bear_case
        evidence = []
        research_summary = None

        if with_research:
            from kalshi_research.exa.client import ExaClient
            from kalshi_research.research.thesis_research import ThesisResearcher

            console.print("[dim]🔍 Researching thesis...[/dim]\n")

            try:
                from kalshi_research.api.exceptions import KalshiAPIError

                try:
                    async with KalshiPublicClient() as kalshi:
                        market = await kalshi.get_market(market_tickers[0])
                except KalshiAPIError:
                    console.print(f"[yellow]Market not found: {market_tickers[0]}[/yellow]")
                    raise typer.Exit(1) from None

                async with ExaClient.from_env() as exa:
                    researcher = ThesisResearcher(exa)
                    direction = "yes" if your_prob > 0.5 else "no"
                    research_data = await researcher.research_for_thesis(market, direction)

                    console.print(
                        f"[green]📰 Found {len(research_data.bull_evidence) + len(research_data.bear_evidence)} relevant sources[/green]\n"
                    )

                    if research_data.suggested_bull_case != bull_case:
                        console.print("[bold cyan]Suggested Bull Case:[/bold cyan]")
                        console.print(research_data.suggested_bull_case)
                        console.print()

                    if research_data.suggested_bear_case != bear_case:
                        console.print("[bold cyan]Suggested Bear Case:[/bold cyan]")
                        console.print(research_data.suggested_bear_case)
                        console.print()

                    # Ask user to accept suggestions
                    if typer.confirm("Accept these suggestions?", default=True):
                        final_bull = research_data.suggested_bull_case
                        final_bear = research_data.suggested_bear_case

                    evidence = research_data.bull_evidence + research_data.bear_evidence
                    research_summary = research_data.summary

                    console.print(f"[dim]Research cost: ${research_data.exa_cost_dollars:.4f}[/dim]")

            except ValueError as e:
                console.print(f"[yellow]Research skipped: {e}[/yellow]")

        # Create thesis
        thesis_id = str(uuid.uuid4())
        thesis = {
            "id": thesis_id,
            "title": title,
            "market_tickers": market_tickers,
            "your_probability": your_prob,
            "market_probability": market_prob,
            "confidence": confidence,
            "bull_case": final_bull,
            "bear_case": final_bear,
            "key_assumptions": [],
            "invalidation_criteria": [],
            "status": "active",
            "created_at": datetime.now(UTC).isoformat(),
            "resolved_at": None,
            "actual_outcome": None,
            "updates": [],
            "evidence": [
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
                for e in evidence
            ],
            "research_summary": research_summary,
            "last_research_at": datetime.now(UTC).isoformat() if evidence else None,
        }

        data = _load_theses()
        data.setdefault("theses", []).append(thesis)
        _save_theses(data)

        console.print(f"[green]✓[/green] Thesis created: {title}")
        console.print(f"[dim]ID: {thesis_id[:8]}[/dim]")
        console.print(f"Edge: {(your_prob - market_prob) * 100:.1f}%")
        if evidence:
            console.print(f"[dim]Evidence attached: {len(evidence)} sources[/dim]")

    asyncio.run(_create())


@thesis_app.command("check-invalidation")
def research_thesis_check_invalidation(
    thesis_id: Annotated[str, typer.Argument(help="Thesis ID to check")],
    hours: Annotated[int, typer.Option("--hours", "-h", help="Lookback hours")] = 48,
) -> None:
    """
    Check for signals that might invalidate your thesis.

    Searches for recent news that contradicts your thesis
    or matches your invalidation criteria.

    Examples:
        kalshi research thesis check-invalidation btc-100k
        kalshi research thesis check-invalidation btc-100k --hours 24
    """
    from kalshi_research.exa.client import ExaClient
    from kalshi_research.research.invalidation import InvalidationDetector, InvalidationSeverity
    from kalshi_research.research.thesis import ThesisTracker

    async def _check() -> None:
        try:
            tracker = ThesisTracker()
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        thesis = tracker.get(thesis_id)
        if not thesis:
            # Try prefix match
            for t in tracker.list_all():
                if t.id.startswith(thesis_id):
                    thesis = t
                    break

        if not thesis:
            console.print(f"[yellow]Thesis not found: {thesis_id}[/yellow]")
            return

        console.print(f"\n[bold]Thesis:[/bold] {thesis.title}")
        console.print(f"Your probability: {thesis.your_probability:.0%} YES")
        console.print(f"[dim]Checking last {hours} hours...[/dim]\n")

        try:
            async with ExaClient.from_env() as exa:
                detector = InvalidationDetector(exa, lookback_hours=hours)
                report = await detector.check_thesis(thesis)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print("[dim]Set EXA_API_KEY in your .env file.[/dim]")
            raise typer.Exit(1)

        if not report.signals:
            console.print("[green]✓ No invalidation signals found[/green]")
            console.print(f"[dim]{report.recommendation}[/dim]")
            return

        console.print(f"[yellow]⚠️ Found {len(report.signals)} potential signals[/yellow]")
        console.print("─" * 40)

        for signal in report.signals:
            severity_color = {
                InvalidationSeverity.HIGH: "red",
                InvalidationSeverity.MEDIUM: "yellow",
                InvalidationSeverity.LOW: "dim",
            }[signal.severity]

            console.print(f"[{severity_color}][{signal.severity.value.upper()}][/{severity_color}] {signal.title}")
            console.print(f"  [dim]{signal.source_domain}[/dim]")
            console.print(f"  [italic]{signal.reason}[/italic]")
            if signal.snippet:
                console.print(f"  > {signal.snippet[:100]}...")
            console.print()

        if report.recommendation:
            console.print(f"[bold]Recommendation:[/bold] {report.recommendation}")

    asyncio.run(_check())


@thesis_app.command("suggest")
def research_thesis_suggest(
    category: Annotated[str | None, typer.Option("--category", "-c", help="Category filter")] = None,
) -> None:
    """
    Get thesis suggestions based on research.

    Examples:
        kalshi research thesis suggest
        kalshi research thesis suggest --category crypto
    """
    from kalshi_research.exa.client import ExaClient
    from kalshi_research.research.thesis_research import ThesisSuggester

    async def _suggest() -> None:
        try:
            async with ExaClient.from_env() as exa:
                suggester = ThesisSuggester(exa)
                suggestions = await suggester.suggest_theses(category=category)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        if not suggestions:
            console.print("[yellow]No suggestions found[/yellow]")
            return

        console.print("\n[bold]🎯 Thesis Suggestions Based on Research[/bold]")
        console.print("─" * 45)

        for i, suggestion in enumerate(suggestions, 1):
            console.print(f"\n{i}. [bold]{suggestion['source_title']}[/bold]")
            console.print(f"   [dim]{suggestion['source_url']}[/dim]")
            console.print(f"   [italic]Key insight:[/italic] {suggestion['key_insight'][:150]}...")

    asyncio.run(_suggest())
```

---

## 4. Testing Strategy

### 4.1 Thesis Researcher Tests

```python
# tests/unit/research/test_thesis_research.py
class TestThesisResearcher:
    """Test research-enhanced thesis creation."""

    def test_classify_evidence_bullish(self) -> None:
        """Positive news classified as bull for YES thesis."""
        researcher = ThesisResearcher(MagicMock())
        classification = researcher._classify_evidence(
            "Bitcoin surges to new highs amid ETF inflows",
            "BTC Rally Continues",
            thesis_direction="yes",
        )
        assert classification == "bull"

    def test_classify_evidence_bearish(self) -> None:
        """Negative news classified as bear for YES thesis."""
        researcher = ThesisResearcher(MagicMock())
        classification = researcher._classify_evidence(
            "Market crashes as regulatory concerns mount",
            "Crypto Plunges",
            thesis_direction="yes",
        )
        assert classification == "bear"


# tests/unit/research/test_invalidation.py
class TestInvalidationDetector:
    """Test invalidation detection."""

    async def test_detects_criterion_match(self) -> None:
        """High severity when invalidation criterion matched."""
        thesis = MagicMock()
        thesis.title = "Bitcoin exceeds 100k"
        thesis.your_probability = 0.65
        thesis.invalidation_criteria = ["SEC rejects Bitcoin ETF"]
        thesis.key_assumptions = []

        mock_exa = AsyncMock()
        mock_exa.search = AsyncMock(return_value=MagicMock(
            results=[
                MagicMock(
                    title="SEC Rejects Bitcoin ETF Application",
                    text="The SEC has officially rejected...",
                    url="https://example.com",
                    published_date=datetime.now(UTC),
                )
            ],
            cost_dollars=MagicMock(total=0.01),
        ))

        detector = InvalidationDetector(mock_exa)
        report = await detector.check_thesis(thesis)

        assert report.has_high_severity
        assert len(report.signals) > 0
```

---

## 5. Implementation Tasks

### Phase 1: Enhanced Thesis Model

- [ ] Add `ThesisEvidence` dataclass
- [ ] Update `Thesis` with evidence field
- [ ] Update serialization/deserialization
- [ ] Write model tests

### Phase 2: Thesis Researcher

- [ ] Implement `ThesisResearcher`
- [ ] Implement evidence classification
- [ ] Implement case summary generation
- [ ] Write researcher tests

### Phase 3: Invalidation Detector

- [ ] Implement `InvalidationDetector`
- [ ] Implement signal analysis
- [ ] Implement recommendation generation
- [ ] Write detector tests

### Phase 4: CLI Integration

- [ ] Add `--with-research` to thesis create
- [ ] Implement `thesis check-invalidation` command
- [ ] Implement `thesis suggest` command
- [ ] Manual CLI testing

---

## 6. Acceptance Criteria

1. **Researched Creation**: Can create thesis with auto-gathered evidence
2. **Evidence Storage**: Evidence persists with thesis
3. **Invalidation Check**: Detects relevant contradicting news
4. **Suggestions**: Generates reasonable thesis ideas
5. **User Control**: User approves/edits suggestions before saving
6. **Test Coverage**: >85% on new modules

---

## 7. CLI Summary

```
kalshi research thesis
├── create            # Create thesis (now with --with-research)
├── list              # List all theses
├── show              # Show thesis details (now shows evidence)
├── resolve           # Resolve thesis
├── check-invalidation # NEW: Check for invalidation signals
└── suggest           # NEW: Get thesis suggestions
```

---

## 8. See Also

- [SPEC-020: Exa API Client](SPEC-020-exa-api-client.md)
- [SPEC-021: Exa Market Research](SPEC-021-exa-market-research.md)
- [SPEC-024: Exa Research Agent](SPEC-024-exa-research-agent.md)
