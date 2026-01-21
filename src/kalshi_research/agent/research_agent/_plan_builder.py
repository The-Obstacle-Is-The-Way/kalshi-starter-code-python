"""Research plan building logic.

This module handles deterministic construction of research plans based on mode and market.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from kalshi_research.agent.schemas import ResearchPlan, ResearchStep
from kalshi_research.exa.policy import ExaMode, ExaPolicy

if TYPE_CHECKING:
    from kalshi_research.api.models.market import Market


def build_research_plan(
    market: Market,
    *,
    mode: ExaMode = ExaMode.STANDARD,
    budget_usd: float,
    recency_days: int = 30,
    deep_research_timeout_seconds: float = 300.0,
    deep_research_poll_interval_seconds: float = 5.0,
) -> ResearchPlan:
    """
    Build a deterministic research plan for a given market and mode.

    Args:
        market: Market metadata
        mode: Research mode (fast/standard/deep)
        budget_usd: Budget limit
        recency_days: Recency window for news searches
        deep_research_timeout_seconds: Max seconds to wait for deep research
            completion (deep mode)
        deep_research_poll_interval_seconds: Seconds between deep research polls (deep mode)

    Returns:
        A serializable ResearchPlan with ordered steps and cost estimates.
    """
    if deep_research_timeout_seconds <= 0:
        raise ValueError("deep_research_timeout_seconds must be positive")
    if deep_research_poll_interval_seconds <= 0:
        raise ValueError("deep_research_poll_interval_seconds must be positive")

    policy = ExaPolicy.from_mode(mode=mode, budget_usd=budget_usd)

    # Generate search queries from market title
    queries = _generate_queries(market.title)

    steps: list[ResearchStep] = []
    step_counter = 0

    # Step 1: News search (all modes)
    for query in queries[: 2 if mode == ExaMode.FAST else 3]:
        step_counter += 1
        num_results = 5 if mode == ExaMode.FAST else 10
        steps.append(
            ResearchStep(
                step_id=f"news_search_{step_counter}",
                endpoint="search",
                description=f"News search for: {query}",
                estimated_cost_usd=policy.estimate_search_cost_usd(
                    num_results=num_results,
                    include_text=policy.include_full_text,
                    include_highlights=True,
                    search_type=policy.exa_search_type,
                ),
                params={
                    "query": query,
                    "num_results": num_results,
                    "start_published_date": (
                        datetime.now(UTC) - timedelta(days=recency_days)
                    ).isoformat(),
                    "category": "news",
                    "use_autoprompt": True,
                    "include_text": policy.include_full_text,
                    "include_highlights": True,
                },
            )
        )

    # Step 2: Answer call (standard/deep modes only)
    if mode != ExaMode.FAST and policy.include_answer:
        step_counter += 1
        steps.append(
            ResearchStep(
                step_id=f"answer_{step_counter}",
                endpoint="answer",
                description=f"Topic summary for: {queries[0]}",
                estimated_cost_usd=policy.estimate_answer_cost_usd(
                    include_text=policy.include_full_text
                ),
                params={
                    "query": queries[0],
                    "include_text": policy.include_full_text,
                    "num_results": 5,
                },
            )
        )

    # Step 3: Background research (deep mode only)
    if mode == ExaMode.DEEP:
        step_counter += 1
        research_query = f"Research on {market.title.rstrip('?').strip()}"
        steps.append(
            ResearchStep(
                step_id=f"deep_research_{step_counter}",
                endpoint="research",
                description=f"Deep research task: {research_query}",
                estimated_cost_usd=0.50,  # Conservative estimate for /research/v1
                params={
                    "instructions": research_query,
                    "use_autoprompt": True,
                    "timeout_seconds": deep_research_timeout_seconds,
                    "poll_interval_seconds": deep_research_poll_interval_seconds,
                },
            )
        )

    total_estimated = sum(step.estimated_cost_usd for step in steps)

    # Generate deterministic plan ID
    plan_input = f"{market.ticker}|{mode.value}|{recency_days}|{len(steps)}"
    plan_id = hashlib.sha256(plan_input.encode()).hexdigest()[:12]

    return ResearchPlan(
        plan_id=plan_id,
        ticker=market.ticker,
        mode=mode.value,
        steps=steps,
        total_estimated_cost_usd=total_estimated,
    )


def _generate_queries(title: str) -> list[str]:
    """Generate search queries from market title."""
    clean_title = title.strip()
    if clean_title.lower().startswith("will "):
        clean_title = clean_title[5:]
    clean_title = clean_title.rstrip("?").strip()

    queries = [
        clean_title,
        f"{clean_title} news",
        f"{clean_title} analysis forecast",
    ]

    # Deduplicate and limit
    return list(dict.fromkeys(q for q in queries if q))[:3]
