# SPEC-024: Exa Research Agent

**Status:** 📋 Planned
**Priority:** P2 (Advanced feature)
**Estimated Complexity:** High
**Dependencies:** SPEC-020, SPEC-021, SPEC-023

---

## 1. Overview

Build an autonomous research agent that orchestrates multiple Exa operations to perform deep research on markets. The agent can plan research strategies, gather evidence iteratively, cross-reference sources, and produce comprehensive research reports.

### 1.1 Goals

- Autonomous multi-step research workflows
- Integration with Exa's async Research endpoint
- Structured research output (JSON schema support)
- Research report generation
- Integration with Claude for reasoning (optional)
- Cost tracking and budget limits

### 1.2 Non-Goals

- Real-time trading decisions
- Fully autonomous thesis creation/trading
- Complex multi-agent coordination (single agent)
- Training custom models
- MCP-based interactive research (handled by native Exa MCP server)

### 1.3 MCP Consideration

For **interactive research sessions** in Claude Desktop/Code, users can use the [Exa MCP server](https://github.com/exa-labs/exa-mcp-server) directly. The MCP server provides:
- `deep_researcher_start` / `deep_researcher_check` tools for async research
- `web_search_exa` and `crawling_exa` for interactive queries and URL extraction

**This agent spec complements MCP** by providing:
1. Reproducible, auditable research pipelines via CLI
2. Structured output with cost tracking
3. Integration with local thesis/portfolio data
4. Batch processing capabilities

**Hybrid approach**: Use MCP for exploratory research, then formalize findings using CLI commands.

---

## 2. Use Cases

### 2.1 Deep Market Research

```bash
# Deep research on a market
uv run kalshi agent research KXBTC-26JAN-T100000 \
    --depth deep \
    --budget 0.50

# Output:
# 🤖 Research Agent Starting
# ─────────────────────────────
# Market: Will Bitcoin exceed $100,000 by January 26?
# Budget: $0.50 | Depth: deep
#
# Phase 1: Background Research
# ├── Searching: Bitcoin price history January...
# ├── Searching: Bitcoin ETF impact analysis...
# └── Found 24 sources ($0.08)
#
# Phase 2: Current News Analysis
# ├── Searching: Bitcoin news last 48 hours...
# ├── Analyzing sentiment...
# └── Found 12 recent articles ($0.05)
#
# Phase 3: Expert Opinion Aggregation
# ├── Searching: Bitcoin price predictions experts...
# ├── Cross-referencing predictions...
# └── Found 8 expert views ($0.04)
#
# Phase 4: Deep Research (Exa Research API)
# ├── Submitting research task...
# ├── Waiting for completion...
# └── Research complete ($0.15)
#
# ════════════════════════════════════════
# RESEARCH REPORT
# ════════════════════════════════════════
#
# Executive Summary:
# Bitcoin reaching $100k by January 26 is moderately likely (55-65%)
# based on current trends and expert consensus.
#
# Key Findings:
# 1. ETF inflows remain strong ($1.2B weekly average)
# 2. Historical January performance is positive (72% of years)
# 3. Macro environment is favorable (Fed pause expected)
#
# Bull Case (60%):
# • Institutional momentum continues
# • Technical breakout above $95k suggests strength
# • Limited selling pressure from long-term holders
#
# Bear Case (40%):
# • $100k is psychological resistance
# • Profit-taking expected at round numbers
# • Regulatory uncertainty persists
#
# Suggested Thesis:
# • Position: YES at 55-60%
# • Confidence: Medium
# • Key assumption: ETF inflows sustain
# • Invalidation: Daily closes below $88k
#
# Sources: 44 articles analyzed
# Total Cost: $0.32
```

### 2.2 Comparative Market Analysis

```bash
# Compare related markets
uv run kalshi agent compare \
    KXBTC-26JAN-T100000 \
    KXBTC-26JAN-T95000 \
    KXBTC-26JAN-T90000

# Analyzes relationship between price targets
```

### 2.3 Event Deep Dive

```bash
# Research all markets in an event
uv run kalshi agent event INXD-26JAN --output report.md
```

---

## 3. Technical Specification

### 3.1 Module Structure

```txt
src/kalshi_research/
├── agent/
│   ├── __init__.py
│   ├── research_agent.py   # Main agent orchestrator
│   ├── planner.py          # Research planning
│   ├── executor.py         # Step execution
│   ├── reporter.py         # Report generation
│   └── budget.py           # Cost tracking and limits
```

### 3.2 Research Agent

```python
# src/kalshi_research/agent/research_agent.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Literal

import structlog

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market
    from kalshi_research.exa.client import ExaClient
    from kalshi_research.exa.models.research import ResearchOutput
    from kalshi_research.exa.models.search import SearchResult

logger = structlog.get_logger()


class ResearchDepth(str, Enum):
    """Depth of research to perform."""
    QUICK = "quick"      # ~5 searches, no deep research
    STANDARD = "standard"  # ~10 searches, basic analysis
    DEEP = "deep"        # ~20 searches + Exa Research API
    EXHAUSTIVE = "exhaustive"  # Maximum coverage


class ResearchPhase(str, Enum):
    """Phases of research execution."""
    BACKGROUND = "background"
    CURRENT_NEWS = "current_news"
    EXPERT_OPINIONS = "expert_opinions"
    DEEP_RESEARCH = "deep_research"
    SYNTHESIS = "synthesis"


@dataclass
class ResearchStep:
    """A single step in the research plan."""

    phase: ResearchPhase
    description: str
    query: str | None = None
    action: Literal["search", "contents", "answer", "research"] = "search"
    params: dict[str, Any] = field(default_factory=dict)
    completed: bool = False
    result: list[SearchResult] | dict[str, object] | ResearchOutput | None = None
    cost: float = 0.0


@dataclass
class ResearchPlan:
    """Plan for executing research."""

    market_ticker: str
    market_title: str
    depth: ResearchDepth
    steps: list[ResearchStep] = field(default_factory=list)
    budget_dollars: float = 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ResearchResult:
    """Complete research result."""

    market_ticker: str
    market_title: str
    depth: ResearchDepth

    # Findings
    executive_summary: str
    key_findings: list[str]
    bull_case: str
    bear_case: str
    suggested_probability: float | None
    confidence: str  # low, medium, high

    # Supporting data
    sources_analyzed: int
    unique_domains: list[str]
    expert_opinions: list[dict[str, str]]

    # Suggested thesis
    suggested_thesis: dict[str, Any] | None

    # Metadata
    total_cost: float
    duration_seconds: float
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class ResearchAgent:
    """
    Autonomous research agent for deep market analysis.

    Orchestrates multiple Exa operations to build comprehensive
    research reports for prediction market theses.
    """

    def __init__(
        self,
        exa: ExaClient,
        *,
        budget_dollars: float = 1.0,
        on_progress: Callable[[str], None] | None = None,
    ) -> None:
        """
        Initialize the research agent.

        Args:
            exa: Initialized ExaClient
            budget_dollars: Maximum budget for research
            on_progress: Optional callback for progress updates
        """
        self.exa = exa
        self.budget_dollars = budget_dollars
        self.on_progress = on_progress or (lambda msg: None)
        self._total_cost = 0.0

    def _log_progress(self, message: str) -> None:
        """Log progress and call callback."""
        logger.info(message)
        self.on_progress(message)

    def _create_plan(
        self,
        market: Market,
        depth: ResearchDepth,
    ) -> ResearchPlan:
        """
        Create a research plan based on depth.

        Args:
            market: The market to research
            depth: Research depth level

        Returns:
            ResearchPlan with steps to execute
        """
        title = market.title.replace("Will ", "").replace("?", "")
        plan = ResearchPlan(
            market_ticker=market.ticker,
            market_title=market.title,
            depth=depth,
            budget_dollars=self.budget_dollars,
        )

        # Phase 1: Background research (all depths)
        plan.steps.append(ResearchStep(
            phase=ResearchPhase.BACKGROUND,
            description="Historical context search",
            query=f"{title} history background",
            action="search",
            params={"num_results": 10, "text": True, "highlights": True},
        ))

        plan.steps.append(ResearchStep(
            phase=ResearchPhase.BACKGROUND,
            description="Market analysis search",
            query=f"{title} analysis outlook",
            action="search",
            params={"num_results": 10, "text": True, "highlights": True},
        ))

        # Phase 2: Current news (all depths)
        plan.steps.append(ResearchStep(
            phase=ResearchPhase.CURRENT_NEWS,
            description="Recent news search",
            query=f"{title} news",
            action="search",
            params={"num_results": 15, "text": True, "highlights": True, "category": "news"},
        ))

        if depth in (ResearchDepth.STANDARD, ResearchDepth.DEEP, ResearchDepth.EXHAUSTIVE):
            # Phase 3: Expert opinions
            plan.steps.append(ResearchStep(
                phase=ResearchPhase.EXPERT_OPINIONS,
                description="Expert predictions search",
                query=f"{title} predictions experts forecast",
                action="search",
                params={"num_results": 10, "text": True, "highlights": True},
            ))

            plan.steps.append(ResearchStep(
                phase=ResearchPhase.EXPERT_OPINIONS,
                description="Research papers search",
                query=title,
                action="search",
                params={"num_results": 5, "text": True, "category": "research paper"},
            ))

        if depth in (ResearchDepth.DEEP, ResearchDepth.EXHAUSTIVE):
            # Phase 4: Deep research via Exa Research API
            plan.steps.append(ResearchStep(
                phase=ResearchPhase.DEEP_RESEARCH,
                description="Comprehensive Exa Research",
                action="research",
                params={
                    "instructions": (
                        f"Provide a comprehensive analysis of: {market.title}\n\n"
                        "Include:\n"
                        "1. Historical context and precedents\n"
                        "2. Current market conditions and trends\n"
                        "3. Expert opinions and predictions\n"
                        "4. Key factors that could affect the outcome\n"
                        "5. Bull case arguments (why YES)\n"
                        "6. Bear case arguments (why NO)\n"
                        "7. Probability assessment with reasoning"
                    ),
                    # Use PRO only for exhaustive depth; DEEP uses the standard research tier by default.
                    "model": "exa-research-pro" if depth == ResearchDepth.EXHAUSTIVE else "exa-research",
                },
            ))

        if depth == ResearchDepth.EXHAUSTIVE:
            # Additional searches for exhaustive research
            plan.steps.append(ResearchStep(
                phase=ResearchPhase.CURRENT_NEWS,
                description="Social media sentiment",
                query=f"{title} twitter reddit discussion",
                action="search",
                params={"num_results": 10, "text": True},
            ))

            plan.steps.append(ResearchStep(
                phase=ResearchPhase.EXPERT_OPINIONS,
                description="Contrarian views",
                query=f"{title} skeptic concerns risks",
                action="search",
                params={"num_results": 10, "text": True},
            ))

        # Final phase: Synthesis (use Answer for summary)
        plan.steps.append(ResearchStep(
            phase=ResearchPhase.SYNTHESIS,
            description="Generate executive summary",
            query=f"What is the probability that {market.title}? Provide a balanced analysis.",
            action="answer",
            params={"text": True},
        ))

        return plan

    async def _execute_step(self, step: ResearchStep) -> None:
        """Execute a single research step."""
        self._log_progress(f"├── {step.description}...")

        try:
            if step.action == "search":
                response = await self.exa.search(
                    step.query,
                    **step.params,
                )
                step.result = response.results
                if response.cost_dollars:
                    step.cost = response.cost_dollars.total

            elif step.action == "contents":
                response = await self.exa.get_contents(**step.params)
                step.result = response.results
                # Contents pricing varies

            elif step.action == "answer":
                response = await self.exa.answer(step.query, **step.params)
                step.result = {
                    "answer": response.answer,
                    "citations": response.citations,
                }
                if response.cost_dollars:
                    step.cost = response.cost_dollars.total

            elif step.action == "research":
                # NOTE: This uses the internal `ExaClient` interface specified in SPEC-020 (async httpx client).
                # The official `exa-py` SDK has different method names/fields; keep internal APIs consistent across specs.
                task = await self.exa.create_research_task(**step.params)
                completed = await self.exa.wait_for_research(
                    task.research_id,
                    timeout=180.0,
                )
                step.result = completed.output
                if completed.cost_dollars:
                    step.cost = completed.cost_dollars.total

            step.completed = True
            self._total_cost += step.cost

            result_count = len(step.result) if isinstance(step.result, list) else 1
            self._log_progress(f"└── Found {result_count} results (${step.cost:.4f})")

        except Exception as e:
            logger.error("Step failed", step=step.description, error=str(e))
            step.result = None
            step.completed = False

    async def _execute_plan(self, plan: ResearchPlan) -> dict[ResearchPhase, list[object]]:
        """
        Execute all steps in the research plan.

        Returns results grouped by phase.
        """
        results_by_phase: dict[ResearchPhase, list[object]] = {
            phase: [] for phase in ResearchPhase
        }

        current_phase = None

        for step in plan.steps:
            # Check budget
            if self._total_cost >= self.budget_dollars:
                self._log_progress(f"⚠️ Budget limit reached (${self._total_cost:.2f})")
                break

            # Log phase transition
            if step.phase != current_phase:
                current_phase = step.phase
                phase_name = current_phase.value.replace("_", " ").title()
                self._log_progress(f"\nPhase: {phase_name}")

            await self._execute_step(step)

            if step.completed and step.result:
                results_by_phase[step.phase].append(step.result)

        return results_by_phase

    def _synthesize_results(
        self,
        market: Market,
        results: dict[ResearchPhase, list[object]],
        depth: ResearchDepth,
        duration: float,
    ) -> ResearchResult:
        """
        Synthesize all results into a research report.
        """
        # Collect all sources
        all_sources = []
        domains = set()

        for phase_results in results.values():
            for result in phase_results:
                if isinstance(result, list):
                    for item in result:
                        if hasattr(item, "url"):
                            all_sources.append(item)
                            from urllib.parse import urlparse
                            domain = urlparse(item.url).netloc.replace("www.", "")
                            domains.add(domain)

        # Extract executive summary from answer phase
        executive_summary = "Research completed."
        synthesis = results.get(ResearchPhase.SYNTHESIS, [])
        if synthesis and isinstance(synthesis[0], dict):
            executive_summary = synthesis[0].get("answer", executive_summary)

        # Extract deep research output if available
        deep_research = results.get(ResearchPhase.DEEP_RESEARCH, [])
        deep_content = ""
        if deep_research and deep_research[0]:
            output = deep_research[0]
            if hasattr(output, "content"):
                deep_content = output.content

        # Generate key findings from sources
        key_findings = self._extract_key_findings(all_sources)

        # Generate bull/bear cases
        bull_case, bear_case = self._generate_cases(all_sources, deep_content)

        # Estimate probability from research
        suggested_prob = self._estimate_probability(executive_summary, deep_content)

        # Collect expert opinions
        expert_opinions = self._extract_expert_opinions(
            results.get(ResearchPhase.EXPERT_OPINIONS, [])
        )

        # Generate suggested thesis
        suggested_thesis = None
        if suggested_prob is not None:
            suggested_thesis = {
                "position": "YES" if suggested_prob > 0.5 else "NO",
                "probability": suggested_prob,
                "confidence": "medium",
                "key_assumption": key_findings[0] if key_findings else "Based on research",
                "invalidation": "Significant contrary news or market movement",
            }

        return ResearchResult(
            market_ticker=market.ticker,
            market_title=market.title,
            depth=depth,
            executive_summary=executive_summary,
            key_findings=key_findings,
            bull_case=bull_case,
            bear_case=bear_case,
            suggested_probability=suggested_prob,
            confidence="medium" if depth == ResearchDepth.STANDARD else "high" if depth in (ResearchDepth.DEEP, ResearchDepth.EXHAUSTIVE) else "low",
            sources_analyzed=len(all_sources),
            unique_domains=list(domains),
            expert_opinions=expert_opinions,
            suggested_thesis=suggested_thesis,
            total_cost=self._total_cost,
            duration_seconds=duration,
        )

    def _extract_key_findings(self, sources: list[object]) -> list[str]:
        """
        Extract key findings from sources.

        NOTE: This is heuristic-heavy specification code. In a future phase, replace this with:
        - LLM-based clustering/summarization, or
        - an embeddings-based dedupe + top-k selection.
        """
        import difflib
        import re

        def normalize(text: str) -> str:
            cleaned = re.sub(r"[^\w\s]", "", text.lower())
            return re.sub(r"\s+", " ", cleaned).strip()

        def is_near_duplicate(candidate: str, existing: list[str]) -> bool:
            for item in existing:
                if difflib.SequenceMatcher(None, candidate, item).ratio() >= 0.92:
                    return True
            return False

        findings: list[str] = []
        seen_normalized: list[str] = []

        for source in sources[:20]:
            highlight = None
            if hasattr(source, "highlights") and source.highlights:
                highlight = source.highlights[0]

            if not isinstance(highlight, str) or not highlight.strip():
                continue

            normalized = normalize(highlight)
            if not normalized:
                continue

            if is_near_duplicate(normalized, seen_normalized):
                continue

            findings.append(highlight.strip()[:200])
            seen_normalized.append(normalized)

            if len(findings) >= 5:
                break

        return findings

    def _generate_cases(
        self,
        sources: list[object],
        deep_content: str,
    ) -> tuple[str, str]:
        """
        Generate bull and bear cases from research.

        NOTE: Heuristic implementation. Prefer LLM-structured extraction in a future phase.
        """
        import re

        bull_points: list[str] = []
        bear_points: list[str] = []

        bullish_terms = {
            "surge",
            "rally",
            "gain",
            "rise",
            "bullish",
            "positive",
            "success",
            "record",
            "outperform",
            "beat",
            "growth",
            "strong",
            "tailwind",
            "approval",
            "adoption",
            "breakthrough",
        }
        bearish_terms = {
            "fall",
            "drop",
            "crash",
            "decline",
            "bearish",
            "negative",
            "fail",
            "weak",
            "headwind",
            "risk",
            "lawsuit",
            "ban",
            "delay",
            "rejection",
            "slowdown",
            "uncertainty",
        }

        def normalize(text: str) -> str:
            cleaned = re.sub(r"[^\w\s]", " ", text.lower())
            return re.sub(r"\s+", " ", cleaned).strip()

        def score(text: str, lexicon: set[str]) -> int:
            return sum(1 for term in lexicon if term in text)

        for source in sources[:50]:
            highlight = None
            if hasattr(source, "highlights") and source.highlights:
                highlight = source.highlights[0]

            if not isinstance(highlight, str) or not highlight.strip():
                continue

            text = normalize(highlight)
            bull_score = score(text, bullish_terms)
            bear_score = score(text, bearish_terms)

            if bull_score - bear_score >= 2:
                bull_points.append(highlight.strip()[:150])
            elif bear_score - bull_score >= 2:
                bear_points.append(highlight.strip()[:150])

            if len(bull_points) >= 5 and len(bear_points) >= 5:
                break

        def extract_section(body: str, headers: list[str]) -> str | None:
            lowered = body.lower()
            for header in headers:
                idx = lowered.find(header)
                if idx == -1:
                    continue
                tail = body[idx + len(header) :]
                tail = tail.lstrip(" :\n\t-•")
                return tail.strip()
            return None

        if deep_content.strip():
            bull_section = extract_section(
                deep_content,
                headers=["bull case", "case for yes", "pros", "upside"],
            )
            bear_section = extract_section(
                deep_content,
                headers=["bear case", "case for no", "cons", "downside", "risks"],
            )

            if bull_section:
                bull_points.append(bull_section[:300])
            if bear_section:
                bear_points.append(bear_section[:300])

        bull_case = "\n• ".join(bull_points[:3]) if bull_points else "Positive indicators identified"
        bear_case = "\n• ".join(bear_points[:3]) if bear_points else "Key risk factors identified"

        return f"• {bull_case}", f"• {bear_case}"

    def _estimate_probability(
        self,
        summary: str,
        deep_content: str,
    ) -> float | None:
        """
        Estimate probability from research content.

        NOTE: Heuristic implementation. Replace with a calibrated model / LLM in a future phase.
        """
        # Look for explicit probability mentions (prefer explicit numbers over sentiment heuristics).
        import re

        combined = (summary + " " + deep_content).lower()

        patterns: list[tuple[str, str]] = [
            # Percent formats
            ("percent", r"(\d{1,3})\s*%\s*(?:chance|probability|likelihood)?"),
            ("percent", r"(\d{1,3})\s*(?:percent|per\s*cent)\s*(?:chance|probability|likelihood)?"),
            # Out-of-10 formats (7/10, 7 out of 10, 7 in 10)
            ("out_of_10", r"(\d+(?:\.\d+)?)\s*/\s*10"),
            ("out_of_10", r"(\d+(?:\.\d+)?)\s*(?:out\s+of|in)\s*10"),
            # Decimal formats with probability context
            ("decimal", r"(?:chance|probability|likelihood)\D{0,20}(0\.\d{1,3})"),
            ("decimal", r"(0\.\d{1,3})\D{0,20}(?:chance|probability|likelihood)"),
        ]

        for kind, pattern in patterns:
            match = re.search(pattern, combined)
            if match:
                raw = match.group(1)
                try:
                    value = float(raw)
                except ValueError:
                    continue

                if kind == "percent":
                    if 0 <= value <= 100:
                        return value / 100.0
                    continue

                if kind == "out_of_10":
                    # Allow 0-10 scale and normalize to 0-1.
                    if 0 <= value <= 10:
                        return value / 10.0
                    continue

                if kind == "decimal":
                    if 0.0 <= value <= 1.0:
                        return value
                    continue

        # Sentiment-based fallback (very rough; treat as last resort).
        positive_words = sum(
            1
            for w in ["likely", "probable", "expected", "tailwind", "bullish", "strong", "support"]
            if w in combined
        )
        negative_words = sum(
            1
            for w in ["unlikely", "doubtful", "uncertain", "headwind", "bearish", "risk", "concern"]
            if w in combined
        )

        score = positive_words - negative_words
        score = max(min(score, 6), -6)
        return 0.50 + (score * 0.05)

    def _extract_expert_opinions(
        self,
        expert_results: list[object],
    ) -> list[dict[str, str]]:
        """Extract expert opinions from research."""
        opinions = []

        for result in expert_results:
            if isinstance(result, list):
                for item in result:
                    if hasattr(item, "title") and hasattr(item, "url"):
                        opinions.append({
                            "source": item.title,
                            "url": item.url,
                            "snippet": item.highlights[0][:150] if hasattr(item, "highlights") and item.highlights else "",
                        })

        return opinions[:5]

    async def research(
        self,
        market: Market,
        depth: ResearchDepth = ResearchDepth.STANDARD,
    ) -> ResearchResult:
        """
        Execute full research workflow.

        Args:
            market: The market to research
            depth: Research depth level

        Returns:
            ResearchResult with complete analysis
        """
        import time
        start_time = time.monotonic()

        self._log_progress(f"🤖 Research Agent Starting")
        self._log_progress(f"─" * 40)
        self._log_progress(f"Market: {market.title}")
        self._log_progress(f"Budget: ${self.budget_dollars:.2f} | Depth: {depth.value}")
        self._log_progress("")

        # Reset cost tracking
        self._total_cost = 0.0

        # Create and execute plan
        plan = self._create_plan(market, depth)
        results = await self._execute_plan(plan)

        duration = time.monotonic() - start_time

        # Synthesize into final result
        result = self._synthesize_results(market, results, depth, duration)

        self._log_progress(f"\n{'═' * 40}")
        self._log_progress(f"Research complete: {result.sources_analyzed} sources analyzed")
        self._log_progress(f"Total cost: ${result.total_cost:.4f}")
        self._log_progress(f"Duration: {result.duration_seconds:.1f}s")

        return result
```

### 3.3 Report Generator

```python
# src/kalshi_research/agent/reporter.py
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kalshi_research.agent.research_agent import ResearchResult


class ResearchReporter:
    """Generate research reports in various formats."""

    def generate_markdown(self, result: ResearchResult) -> str:
        """Generate a Markdown research report."""
        lines = [
            f"# Research Report: {result.market_title}",
            "",
            f"**Generated:** {result.completed_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Depth:** {result.depth.value}",
            f"**Sources Analyzed:** {result.sources_analyzed}",
            f"**Cost:** ${result.total_cost:.4f}",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            result.executive_summary,
            "",
            "## Key Findings",
            "",
        ]

        for i, finding in enumerate(result.key_findings, 1):
            lines.append(f"{i}. {finding}")

        lines.extend([
            "",
            "## Bull Case",
            "",
            result.bull_case,
            "",
            "## Bear Case",
            "",
            result.bear_case,
            "",
        ])

        if result.suggested_probability is not None:
            lines.extend([
                "## Probability Assessment",
                "",
                f"**Suggested Probability:** {result.suggested_probability:.0%}",
                f"**Confidence:** {result.confidence}",
                "",
            ])

        if result.suggested_thesis:
            lines.extend([
                "## Suggested Thesis",
                "",
                f"- **Position:** {result.suggested_thesis['position']}",
                f"- **Probability:** {result.suggested_thesis['probability']:.0%}",
                f"- **Confidence:** {result.suggested_thesis['confidence']}",
                f"- **Key Assumption:** {result.suggested_thesis['key_assumption']}",
                f"- **Invalidation:** {result.suggested_thesis['invalidation']}",
                "",
            ])

        if result.expert_opinions:
            lines.extend([
                "## Expert Opinions",
                "",
            ])
            for opinion in result.expert_opinions:
                lines.append(f"- **{opinion['source']}**")
                if opinion.get("snippet"):
                    lines.append(f"  > {opinion['snippet']}")
                lines.append("")

        lines.extend([
            "---",
            "",
            "## Sources",
            "",
            f"Analysis based on {result.sources_analyzed} sources from {len(result.unique_domains)} domains.",
            "",
            "### Domains",
            "",
        ])

        for domain in sorted(result.unique_domains)[:10]:
            lines.append(f"- {domain}")

        return "\n".join(lines)

    def save_markdown(
        self,
        result: ResearchResult,
        path: Path | str,
    ) -> None:
        """Save report to Markdown file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self.generate_markdown(result)
        path.write_text(content)

    def generate_json(self, result: ResearchResult) -> dict:
        """Generate JSON-serializable report."""
        from dataclasses import asdict
        return asdict(result)
```

### 3.4 CLI Commands

```python
# src/kalshi_research/cli/agent.py
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from kalshi_research.cli.utils import console

app = typer.Typer(help="Research agent commands.")


@app.command("research")
def agent_research(
    ticker: Annotated[str, typer.Argument(help="Market ticker to research")],
    depth: Annotated[str, typer.Option("--depth", "-d", help="Research depth")] = "standard",
    budget: Annotated[float, typer.Option("--budget", "-b", help="Budget in dollars")] = 0.50,
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output file path")] = None,
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """
    Run deep research on a market.

    Examples:
        kalshi agent research KXBTC-26JAN-T100000
        kalshi agent research KXBTC-26JAN-T100000 --depth deep --budget 1.00
        kalshi agent research KXBTC-26JAN-T100000 --output report.md
    """
    from kalshi_research.agent.research_agent import ResearchAgent, ResearchDepth
    from kalshi_research.agent.reporter import ResearchReporter
    from kalshi_research.api import KalshiPublicClient
    from kalshi_research.exa.client import ExaClient

    try:
        research_depth = ResearchDepth(depth)
    except ValueError:
        console.print(f"[red]Invalid depth:[/red] {depth}")
        console.print(f"[dim]Options: {', '.join(d.value for d in ResearchDepth)}[/dim]")
        raise typer.Exit(1)

    async def _research() -> None:
        # Get market
        async with KalshiPublicClient() as kalshi:
            market = await kalshi.get_market(ticker)

        if not market:
            console.print(f"[red]Market not found:[/red] {ticker}")
            raise typer.Exit(1)

        # Progress callback
        def on_progress(msg: str) -> None:
            if not output_json:
                console.print(msg)

        try:
            async with ExaClient.from_env() as exa:
                agent = ResearchAgent(
                    exa,
                    budget_dollars=budget,
                    on_progress=on_progress,
                )
                result = await agent.research(market, depth=research_depth)

        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print("[dim]Set EXA_API_KEY in your .env file.[/dim]")
            raise typer.Exit(1)

        reporter = ResearchReporter()

        if output_json:
            import json
            console.print(json.dumps(reporter.generate_json(result), indent=2, default=str))
            return

        # Display report
        console.print("\n" + "═" * 50)
        console.print("[bold]RESEARCH REPORT[/bold]")
        console.print("═" * 50 + "\n")

        console.print(f"[bold]Executive Summary:[/bold]")
        console.print(result.executive_summary)
        console.print()

        console.print(f"[bold]Key Findings:[/bold]")
        for i, finding in enumerate(result.key_findings, 1):
            console.print(f"  {i}. {finding[:100]}...")
        console.print()

        console.print(f"[bold cyan]Bull Case:[/bold cyan]")
        console.print(result.bull_case)
        console.print()

        console.print(f"[bold red]Bear Case:[/bold red]")
        console.print(result.bear_case)
        console.print()

        if result.suggested_probability:
            prob_color = "green" if result.suggested_probability > 0.5 else "red"
            console.print(f"[bold]Suggested Probability:[/bold] [{prob_color}]{result.suggested_probability:.0%}[/{prob_color}]")
            console.print(f"[bold]Confidence:[/bold] {result.confidence}")
            console.print()

        if result.suggested_thesis:
            console.print(f"[bold]Suggested Thesis:[/bold]")
            console.print(f"  Position: {result.suggested_thesis['position']}")
            console.print(f"  Key assumption: {result.suggested_thesis['key_assumption']}")
            console.print(f"  Invalidation: {result.suggested_thesis['invalidation']}")
            console.print()

        console.print(f"[dim]Sources: {result.sources_analyzed} | Cost: ${result.total_cost:.4f} | Time: {result.duration_seconds:.1f}s[/dim]")

        # Save to file if requested
        if output:
            output_path = Path(output)
            if output_path.suffix == ".json":
                import json
                output_path.write_text(json.dumps(reporter.generate_json(result), indent=2, default=str))
            else:
                reporter.save_markdown(result, output_path)
            console.print(f"\n[green]✓[/green] Report saved to {output}")

    asyncio.run(_research())


@app.command("compare")
def agent_compare(
    tickers: Annotated[list[str], typer.Argument(help="Market tickers to compare")],
    budget: Annotated[float, typer.Option("--budget", "-b", help="Budget per market")] = 0.25,
) -> None:
    """
    Compare related markets.

    Examples:
        kalshi agent compare KXBTC-26JAN-T100000 KXBTC-26JAN-T95000
    """
    console.print("[yellow]Compare feature coming soon[/yellow]")
    console.print(f"Would compare: {', '.join(tickers)}")
```

---

## 4. Testing Strategy

### 4.1 Agent Tests

```python
# tests/unit/agent/test_research_agent.py
class TestResearchAgent:
    """Test research agent."""

    def test_create_plan_quick(self) -> None:
        """Quick depth creates minimal plan."""
        agent = ResearchAgent(MagicMock())
        market = MagicMock()
        market.ticker = "TEST"
        market.title = "Will X happen?"

        plan = agent._create_plan(market, ResearchDepth.QUICK)

        assert len(plan.steps) < 5
        assert all(s.action != "research" for s in plan.steps)

    def test_create_plan_deep(self) -> None:
        """Deep depth includes research API."""
        agent = ResearchAgent(MagicMock())
        market = MagicMock()
        market.ticker = "TEST"
        market.title = "Will X happen?"

        plan = agent._create_plan(market, ResearchDepth.DEEP)

        research_steps = [s for s in plan.steps if s.action == "research"]
        assert len(research_steps) > 0

    def test_budget_enforcement(self) -> None:
        """Agent stops when budget exceeded."""
        # Test that steps stop executing when budget is hit
        pass
```

---

## 5. Implementation Tasks

### Phase 1: Core Agent

- [ ] Create `src/kalshi_research/agent/` package
- [ ] Implement `ResearchAgent` with plan creation
- [ ] Implement step execution
- [ ] Write agent tests

### Phase 2: Synthesis

- [ ] Implement result synthesis
- [ ] Implement probability estimation
- [ ] Implement case generation
- [ ] Test synthesis logic

### Phase 3: Reporting

- [ ] Implement `ResearchReporter`
- [ ] Markdown report generation
- [ ] JSON output
- [ ] File saving

### Phase 4: CLI

- [ ] Implement `agent research` command
- [ ] Add progress display
- [ ] Add output options
- [ ] Manual CLI testing

---

## 6. Acceptance Criteria

1. **Depth Levels**: Quick/Standard/Deep produce appropriate plans
2. **Budget Control**: Agent stops at budget limit
3. **Report Quality**: Reports are coherent and actionable
4. **Performance**: Standard research completes in <60s
5. **Cost Tracking**: Accurate cost reporting
6. **Test Coverage**: >80% on agent module

---

## 7. CLI Summary

```txt
kalshi agent
├── research      # Deep research on a market
├── compare       # Compare related markets (future)
└── event         # Research all markets in event (future)
```

---

## 8. See Also

- [SPEC-020: Exa API Client](SPEC-020-exa-api-client.md)
- [SPEC-021: Exa Market Research](SPEC-021-exa-market-research.md)
- [SPEC-023: Exa-Thesis Integration](SPEC-023-exa-thesis-integration.md)
- [Exa API Reference](../_vendor-docs/exa-api-reference.md) - Includes MCP server setup
- [Exa MCP Server (GitHub)](https://github.com/exa-labs/exa-mcp-server) - For interactive research
