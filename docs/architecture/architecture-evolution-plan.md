# Kalshi Research Platform – Architecture Evolution Plan

This document is a cleaned-up, Markdown-formatted version of an externally drafted architecture plan. The intent is to preserve the original content while making it readable and actionable for this repo.

## Summary

- Default to a **single orchestrator** for tool-heavy, sequential workflows.
- Use multi-agent only as a **targeted escalation** (centralized supervisor/judge pattern).
- Keep orchestration deterministic in code: strict schemas + validation + explicit error handling.
- Prefer “structured outputs” (Pydantic) over ad-hoc text parsing.

## Architecture Recommendation (Single vs. Multi-Agent)

For the goal of “surfacing mispriced prediction markets using AI research,” a single-agent architecture is the prudent starting point. The DeepMind study indicates that adding agents can hurt tool-heavy, sequential tasks. In fact, multi-agent setups showed 39–70% performance degradation on sequential reasoning tasks, which fits our use-case (gather data → analyze → synthesize). A single capable agent using tools sequentially will avoid the coordination overhead that multi-agent teams impose on tool usage.

If we later find clear sub-tasks that benefit from parallelization (e.g. fetching independent data sources concurrently), we can introduce a centralized multi-agent pattern. The DeepMind paper suggests a central “Supervisor” agent delegating to specialist sub-agents can preserve quality better than agents working independently. In a centralized scheme, a primary agent would coordinate specialized helpers (for research, history, arbitrage), then integrate their outputs. This avoids the large error amplification seen in fully independent agents.

However, initial implementation will stay single-agent until there’s a justified need for concurrency or specialization. This aligns with the principle “start simple, add complexity only when justified.” We expect a single agent (using structured tools) to achieve a strong baseline – per the paper, coordination only yields gains if the single-agent performance is low (below ~45% task success). Given modern model capabilities, one agent will likely suffice at first. In summary, optimize for a single orchestrator agent now for reliability, and keep the door open for a centralized multi-agent upgrade if scaling demands it.

## Agent Design & Coordination Pattern

If/when we move beyond one agent, the design will follow a centralized “hub-and-spoke” pattern rather than peer-to-peer voting or independent agents. The task naturally breaks into stages, which map to potential agents:

- **Research Agent**: Uses Exa API (or similar) to fetch and summarize current news and insights relevant to a market.
- **Historical Analysis Agent**: Performs retrieval-augmented lookup of past similar markets (using embeddings) and computes statistical baselines or patterns.
- **Arbitrage/Consistency Agent**: Checks logical consistency or cross-market arbitrage opportunities.
- **Judge/Synthesizer Agent**: Acts as the central coordinator, validating inputs and producing the final probability estimate with reasoning.

In a centralized coordination, the Judge agent would sequentially call upon the others (either in parallel or series as appropriate) and aggregate their findings into the final output. This pattern aligns with recommendations that a supervisor can contain error propagation significantly better than independent agents and can improve performance on tasks that can be parallelized.

Parallel execution could speed up response time – something Pydantic Graph supports via parallel nodes – but it should be introduced only if latency becomes an issue. The Pydantic AI framework doesn’t implicitly spawn multiple agents on its own; instead it provides patterns for us to orchestrate them if needed. We can implement agent delegation (one agent calling another as a tool), programmatic hand-off (run one agent then pass control to the next via code), or define an explicit workflow graph via pydantic-graph if the logic gets complex.

Initial approach: Keep everything in a single agent’s flow. The single agent (think of it as the Judge doing all tasks itself) can call tools/functions for API queries, database fetches, and Exa search. This avoids overhead while volume is low. Only if performance bottlenecks or accuracy issues emerge will we instantiate distinct agents. At that point we’d use the centralized model – a top-level orchestrator agent explicitly coordinating specialist agents – rather than letting multiple agents free-roam. Avoid decentralized “debate” patterns unless a clear need arises.

## Step-by-Step Implementation Plan

To replace non-deterministic orchestration with a structured, maintainable pipeline, implement the following steps:

### Step 1: Create a structured analysis CLI command

Introduce a new CLI entry point (e.g. `kalshi analyze` or `kalshi predict`) that runs end-to-end analysis for a given market and outputs structured JSON. This command performs the sub-tasks in code: fetch market data (API/DB), call Exa for research, optionally retrieve historical stats, then call an LLM to synthesize the final probability and reasoning.

Example output shape:

```json
{
  "market_id": "XYZ123",
  "market_question": "...",
  "predicted_prob": 73,
  "confidence": "medium",
  "reasoning": "...",
  "factors": ["..."],
  "sources": ["https://news.example/..."]
}
```

### Step 2: Define Pydantic schemas for the data flow

All inputs/outputs between components should be defined as Pydantic models to enforce structure and validation. If any step produces invalid data, fail fast (no silent hallucinations).

### Step 3: Integrate Instructor for structured LLM output

Use Instructor (or equivalent) so that the LLM returns a Pydantic model instance directly.

Example shape:

```python
from instructor import from_provider

client = from_provider("google/gemini-flash")
result = client.chat.completions.create(
    response_model=AnalysisResult,
    messages=[...],
)
```

### Step 4: Orchestrate via external agent tools (transitional)

Keep an external agent (Claude/Codex/Gemini) as a thin wrapper that:

- runs the deterministic CLI command
- formats JSON output for humans

The key: the agent is not doing orchestration logic; our code is.

### Step 5: Upgrade to internal agents gradually

Once the structured CLI pipeline is working reliably, migrate orchestration inside the application using PydanticAI where appropriate.

### Step 6: Introduce a workflow graph (only if needed)

If the pipeline needs branching or parallelization, adopt pydantic-graph to formalize the workflow.

## Pydantic Schema Definitions

Key schema candidates (fields subject to refinement):

- **MarketInfo**: `market_id: str`, `question: str`, `category: str`, `current_price: float`, `volume: float`, `expiry_date: datetime`, ...
- **NewsArticle**: `title: str`, `url: HttpUrl`, `published_date: datetime | None`, `snippet: str`, `relevance_score: float | None`
- **Factor**: `description: str`, `impact: str | None`, `source: HttpUrl`
- **ResearchSummary**: `factors: list[Factor]`, `summary_text: str | None`
- **HistoricalStats**: `base_rate: float`, `similar_cases: list[HistoricalCase]`, ...
- **AnalysisResult**: `market_id: str`, `predicted_prob: int (0–100)`, `confidence: Literal["low","medium","high"]`, `reasoning: str`, `factors: list[Factor]`, `sources: list[HttpUrl]`, `timestamp: datetime`

## CLI Commands and Future Agents (Tooling)

Design CLI commands that map cleanly to future agent tools/functions:

- No interactive prompts
- Machine-readable output (JSON)
- Minimal side effects
- Idempotent and composable

Proposed commands:

- `kalshi markets ...`: fetch markets and output `MarketInfo[]`
- `kalshi scan ...`: scan for anomalies / close-races / movers
- `kalshi research <query>`: Exa-powered research and structured summaries
- `kalshi analyze <ticker>`: end-to-end analysis and structured output

## LLM Orchestration Strategy (Claude vs. Internal)

Hybrid plan:

- Immediate term: external tool (Claude/Codex) triggers `kalshi analyze` and formats the result.
- Next phase: embed the full loop inside the CLI and run it headless/on a schedule.
- Avoid adding additional external orchestration layers (new “agent coordinators”) unless justified.

## Volume & Frequency Scaling Strategy

- Design for idempotent re-runs.
- Start manual/on-demand, then add a scheduler once stable.
- Avoid premature distributed systems.
- Add caching and rate-limit awareness as frequency increases.

## Retrieval-Augmented Generation (RAG) Considerations

Phase approach:

1. Validate core loop without RAG
2. Add base-rate / simple historical features
3. Add embedding-based similarity search (vector store)
4. Feed retrieved similar cases into the synthesis prompt (typed `HistoricalStats`)

## Exa Search Integration Strategy

Integrate Exa as a strict boundary:

- Encapsulate Exa calls in a single client/module (tool boundary).
- Prefer raw results + our own summarization for traceability.
- Consider one-step vs two-step prompting:
  - One-step: synthesize directly from snippets (simple, cheaper).
  - Two-step: summarize into factors first, then synthesize (more calls, potentially better quality).
- Implement robust error handling and caching.

## Observability & Validation (Error Handling)

- Pydantic validation everywhere.
- Explicit source citations in output (`sources`).
- Log structured results for later calibration tracking.
- Handle partial failures gracefully (e.g., Exa down → proceed with empty research result).

## Potential Pitfalls and Mitigations

- **Overcomplicating early**: start single-agent, add complexity only when justified.
- **Undocumented magic**: keep the LLM inside strict schemas and cite sources.
- **Not testing in isolation**: unit test the tool boundaries and core transforms.
- **Cost/latency bloat**: watch prompt sizes and number of calls; cache where possible.
- **Integration hell**: integrate one new framework at a time.
- **State consistency**: transactional DB writes; avoid corruption and double-runs.
- **Key hygiene**: never log secrets; ensure observability tooling doesn’t leak credentials.

## Multi-Agent Escalation (Paper-Consistent)

The core reconciliation:

- Multi-agent can help on parallelizable subtasks or when baseline is weak.
- For tool-heavy sequential pipelines, coordination overhead can be a tax.

Recommended operating mode:

- Default: single orchestrator + deterministic feature extraction + strict validation.
- Escalation path (high-EV / low-confidence / contradictions): centralized multi-agent critique.

Notes:

- MAR-style reflection loops can be valuable, but are expensive; treat them as escalation after failure or uncertainty.
- Debate/critic patterns are best used when there’s meaningful disagreement or constraint violations to resolve.

## References

- [Towards a Science of Scaling Agent Systems (arXiv:2512.08296)](https://arxiv.org/abs/2512.08296)
- [PydanticAI Graph](https://ai.pydantic.dev/graph/)
- [Instructor](https://github.com/567-labs/instructor)
- [Logfire article](https://kadermiyanyedi.medium.com/fire-up-your-logging-needs-with-logfire-6330d7a08dfe)
