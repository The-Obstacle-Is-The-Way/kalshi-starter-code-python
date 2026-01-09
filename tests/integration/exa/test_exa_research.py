"""
Integration tests that hit the real Exa API.

These are skipped unless EXA_API_KEY is configured.
"""

from __future__ import annotations

import os

import pytest

from kalshi_research.exa.client import ExaClient
from kalshi_research.research.topic import TopicResearcher

pytestmark = [pytest.mark.integration]


@pytest.mark.skipif(
    not os.environ.get("EXA_API_KEY"),
    reason="EXA_API_KEY not set",
)
async def test_topic_research_real() -> None:
    async with ExaClient.from_env() as exa:
        researcher = TopicResearcher(exa, max_results=3)
        research = await researcher.research_topic(
            "Bitcoin price prediction 2026",
            include_answer=True,
        )

    assert research.summary is not None
    assert len(research.summary) > 50
    assert research.exa_cost_dollars > 0
