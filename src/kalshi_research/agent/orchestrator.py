"""Agent kernel orchestration - single-agent default with deterministic workflow.

This module implements the core orchestration logic per SPEC-032:
- Deterministic step sequence (no LLM-driven planning)
- Structured I/O via Pydantic schemas
- Rule-based verification
- Escalation is deferred; suggestions are informational only
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from kalshi_research.api.client import KalshiPublicClient

    from .providers.llm import StructuredSynthesizer
    from .research_agent import ResearchAgent
    from .schemas import AgentRunResult

from kalshi_research.constants import DEFAULT_AGENT_MAX_EXA_USD, DEFAULT_AGENT_MAX_LLM_USD
from kalshi_research.exa.policy import ExaMode

from .providers.kalshi import fetch_market_info, fetch_price_snapshot
from .providers.llm import SynthesisInput
from .schemas import AgentRunResult as ARR
from .verify import verify_analysis

logger = structlog.get_logger()


class AgentKernel:
    """Single-orchestrator agent that coordinates deterministic research + synthesis.

    The kernel executes a fixed workflow:
    1. Fetch market info + price snapshot (Kalshi)
    2. Fetch research summary (ResearchAgent)
    3. Synthesize probability estimate (LLM)
    4. Verify output (rule-based)
    5. Optionally escalate (Phase 2 - not implemented yet)

    Escalation is OFF by default in Phase 1.
    """

    def __init__(
        self,
        *,
        kalshi_client: KalshiPublicClient,
        research_agent: ResearchAgent | None = None,
        synthesizer: StructuredSynthesizer,
        max_exa_usd: float = DEFAULT_AGENT_MAX_EXA_USD,
        max_llm_usd: float = DEFAULT_AGENT_MAX_LLM_USD,
    ):
        """Initialize agent kernel.

        Args:
            kalshi_client: Kalshi public client for market data
            research_agent: Optional research agent (if None, skips research step)
            synthesizer: LLM synthesizer for probability estimates
            max_exa_usd: Maximum Exa budget per run
            max_llm_usd: Maximum LLM budget per run (Phase 2)
        """
        self.kalshi_client = kalshi_client
        self.research_agent = research_agent
        self.synthesizer = synthesizer
        self.max_exa_usd = max_exa_usd
        self.max_llm_usd = max_llm_usd

    async def analyze(
        self,
        *,
        ticker: str,
        research_mode: str = "standard",
    ) -> AgentRunResult:
        """Run complete analysis workflow for a market.

        Args:
            ticker: Market ticker (e.g., KXBTC-24DEC31-50K)
            research_mode: Research mode (fast, standard, deep)

        Returns:
            AgentRunResult with analysis, verification, and optional research

        Raises:
            httpx.HTTPStatusError: If ticker not found
            ValidationError: If synthesis output fails schema validation
        """
        total_cost_usd = 0.0

        # Step 1: Fetch market metadata + orderbook
        market_info = await fetch_market_info(self.kalshi_client, ticker)
        price_snapshot = await fetch_price_snapshot(self.kalshi_client, ticker)

        # Step 2: Fetch research (optional)
        research_summary = None
        if self.research_agent:
            # Fetch market object for research agent
            market = await self.kalshi_client.get_market(ticker)

            # Convert research_mode string to ExaMode
            mode_enum = ExaMode(research_mode.lower())

            research_summary = await self.research_agent.research(
                market,
                mode=mode_enum,
                budget_usd=self.max_exa_usd,
            )
            total_cost_usd += research_summary.total_cost_usd

        # Step 3: Synthesize probability estimate
        synthesis_input = SynthesisInput(
            market=market_info,
            snapshot=price_snapshot,
            research=research_summary,
        )
        analysis = await self.synthesizer.synthesize(input=synthesis_input)
        total_cost_usd += self.synthesizer.get_last_call_cost_usd()

        # Step 4: Verify output
        verification = verify_analysis(analysis)

        escalated = False
        if verification.suggested_escalation:
            logger.info(
                "Escalation suggested (deferred)",
                ticker=ticker,
                issues=verification.issues,
            )

        # Return complete result
        return ARR(
            analysis=analysis,
            verification=verification,
            research=research_summary,
            escalated=escalated,
            total_cost_usd=total_cost_usd,
        )
