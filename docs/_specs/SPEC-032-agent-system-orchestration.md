# SPEC-032: Agent System Orchestration (Single-Agent Default + Escalation)

**Status:** Ready (blocked by SPEC-033)
**Priority:** P1 (Core “mispricing research” roadmap)
**Created:** 2026-01-10
**Owner:** Solo
**Effort:** ~3–7 days (Phase 1), ~1–2 weeks (Phase 2–3)

---

## Summary

Implement a **deterministic, schema-first “agent system”** inside this repo that can:

1. Gather market + orderbook data (Kalshi)
2. Gather evidence (Exa + local DB)
3. Synthesize a probability estimate (LLM, structured output)
4. Verify the output (rules + optional cheap auditor)
5. Escalate *only when justified* (centralized supervisor calling specialist critics)

Default execution is **single-orchestrator**, tool-heavy, sequential (per `docs/architecture/architecture-evolution-plan.md`). Multi-agent is **not** the default; it is a **gated escalation path**.

This spec defines the **interfaces, schemas, CLI surface, and gating policy**. Concrete “research” and “trade safety” components are specified separately (SPEC-033 / SPEC-034).

---

## Goals

1. **Deterministic orchestration**: the sequence is code-controlled, not “LLM vibes”.
2. **Structured contracts**: every boundary uses Pydantic models; failures are validation errors.
3. **Separation of concerns**:
   - retrieval/feature extraction (code + APIs)
   - synthesis (LLM call)
   - verification (rules + optional auditor)
4. **Safe-by-default escalation**: multi-agent critique only when the verifier or EV gating says it’s worth it.
5. **Tool-aligned CLI**: non-interactive, JSON-first, composable; suitable for cron and for external wrappers.

---

## Non-Goals

- No autonomous trading (that requires SPEC-034 and explicit “live mode”).
- No decentralized debate/voting as default (error amplification risk).
- No full RAG/embeddings/vector DB in Phase 1 (RAG is a Phase 3 add-on, per architecture plan).
- No requirement to adopt PydanticAI/Graph immediately; Phase 1 is framework-light.

---

## SSOT (What’s True Today)

1. **Kalshi client + models exist**:
   - `src/kalshi_research/api/client.py` (`KalshiPublicClient`, `KalshiClient`)
   - `src/kalshi_research/api/models/market.py` (`Market`, `MarketFilterStatus`, `settlement_ts` support)
   - Vendor SSOT: `docs/_vendor-docs/kalshi-api-reference.md`
2. **Exa client + models exist**:
   - `src/kalshi_research/exa/client.py` (search/contents/findSimilar/answer/research)
   - Vendor SSOT: `docs/_vendor-docs/exa-api-reference.md`
3. **Research + scanning exist**:
   - Exa-based research: `src/kalshi_research/research/context.py`, `src/kalshi_research/research/topic.py`
   - Scanner + liquidity scoring: `src/kalshi_research/analysis/scanner.py`, `src/kalshi_research/analysis/liquidity.py`
4. **No internal “LLM synthesis” runtime exists yet**:
   - No Instructor / PydanticAI dependency in `pyproject.toml` (this spec introduces it as optional).

---

## Architecture

### 1) Single-Orchestrator Default (Agent “Kernel”)

We implement a single orchestrator class that coordinates deterministic steps and calls exactly one synthesis
model by default.

**Proposed module layout**

```txt
src/kalshi_research/agent/
  __init__.py
  orchestrator.py          # AgentKernel orchestration (this spec)
  schemas.py               # Shared Pydantic I/O models (introduced in SPEC-033; extended here)
  verify.py                # Rule-based verification (this spec)
  escalation.py            # Escalation gating + optional critics (Phase 2)
  providers/
    __init__.py
    llm.py                 # LLM provider interface (Phase 1)
    exa.py                 # Research adapter wrapper (SPEC-033 owns details)
    kalshi.py              # Market/orderbook adapter wrapper
    history.py             # Historical provider interface (Phase 3)
    arbitrage.py           # Consistency checks interface (Phase 2–3)
```

This separation enforces Clean Architecture boundaries:

- `orchestrator.py` contains *workflow*, not HTTP details.
- `providers/*` are tool boundaries (Kalshi, Exa, LLM).
- `schemas.py` is the typed contract between all parts.

### 2) Escalation Path (Centralized Supervisor)

When escalation triggers, the orchestrator becomes a **supervisor**:

- Runs **2–3 critic passes** (e.g., ResearchCritic, ConsistencyCritic, CalibrationCritic)
- Aggregates into a single `AnalysisResult` (still schema-validated)

Critics are not “peer agents”; they are **tools called by the supervisor** (centralized pattern).

Escalation is defined and gated in `escalation.py`:

- deterministic triggers (rules)
- optional model-based trigger (cheap auditor)
- explicit budget ceilings

---

## Data Contracts (Pydantic Schemas)

All agent I/O is Pydantic. No untyped dicts except where explicitly noted.

### Core inputs

```python
class MarketInfo(BaseModel):
    ticker: str
    event_ticker: str
    series_ticker: str | None
    title: str
    subtitle: str
    status: str
    open_time: datetime
    close_time: datetime
    expiration_time: datetime
    settlement_ts: datetime | None
```

```python
class MarketPriceSnapshot(BaseModel):
    yes_bid_cents: int
    yes_ask_cents: int
    no_bid_cents: int
    no_ask_cents: int
    last_price_cents: int | None
    volume_24h: int
    open_interest: int
    midpoint_prob: float  # 0..1
    spread_cents: int
    captured_at: datetime
```

```python
class NewsArticle(BaseModel):
    title: str
    url: HttpUrl
    source_domain: str
    published_at: datetime | None
    snippet: str | None
    relevance_score: float | None
```

```python
class Factor(BaseModel):
    description: str
    impact: Literal["up", "down", "unclear"] | None = None
    source_url: HttpUrl
```

```python
class ResearchSummary(BaseModel):
    summary_text: str | None = None
    factors: list[Factor] = Field(default_factory=list)
    articles: list[NewsArticle] = Field(default_factory=list)
    budget_exhausted: bool = False
    total_cost_usd: float = 0.0
```

### Optional inputs (Phase 2–3)

```python
class HistoricalCase(BaseModel):
    reference_id: str  # e.g., settled market ticker or thesis id
    description: str
    outcome: Literal["yes", "no", "void"] | None = None
    settled_at: datetime | None = None
    similarity_score: float | None = None
```

```python
class HistoricalStats(BaseModel):
    base_rate: float | None = None
    similar_cases: list[HistoricalCase] = Field(default_factory=list)
```

```python
class ArbitrageFinding(BaseModel):
    description: str
    related_tickers: list[str]
    severity: Literal["info", "warn", "fail"]
```

### Outputs

```python
class AnalysisResult(BaseModel):
    ticker: str
    market_prob: float  # 0..1 (derived from MarketPriceSnapshot)
    predicted_prob: int  # 0..100
    confidence: Literal["low", "medium", "high"]
    reasoning: str
    factors: list[Factor] = Field(default_factory=list)
    sources: list[HttpUrl] = Field(default_factory=list)
    generated_at: datetime
    model_id: str | None = None
```

```python
class VerificationReport(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)
    checked_sources: list[HttpUrl] = Field(default_factory=list)
    suggested_escalation: bool = False
```

```python
class AgentRunResult(BaseModel):
    analysis: AnalysisResult
    verification: VerificationReport
    research: ResearchSummary | None = None
    historical: HistoricalStats | None = None
    arbitrage: list[ArbitrageFinding] = Field(default_factory=list)
    escalated: bool = False
    total_cost_usd: float = 0.0  # (Exa + LLM)
```

---

## Verification (Rule-Based First)

Verification is intentionally **non-agentic** by default:

1. Schema validation (Pydantic) already catches gross failures.
2. Rule verification checks:
   - `predicted_prob` is 0..100
   - `sources` are unique and subset of cited factor URLs
   - at least N citations when confidence is not “low”
   - reasoning length bounds (prevent huge dumps)
   - consistency checks (e.g., predicted_prob not identical to market_prob every time)
3. Optional “auditor LLM” (cheap, short prompt) only if:
   - verification fails, or
   - EV gating is high and we want extra scrutiny

The verifier returns a `VerificationReport`.

---

## Escalation Policy (When Multi-Agent is Worth It)

Escalation is a **policy**, not “always debate”.

### Deterministic triggers (default)

Escalate when any of:

- `VerificationReport.passed == False`
- citations missing for “medium/high” confidence
- cross-market inconsistency flagged by `arbitrage` tool (Phase 2)

### EV-based trigger (optional)

Escalate when:

- `abs(predicted_prob/100 - market_prob) >= EV_DELTA_THRESHOLD`
- and `volume_24h >= EV_MIN_VOLUME` (or liquidity score above threshold)

Defaults are conservative and configurable via CLI flags.

### Escalation budget ceiling

Escalation has a hard USD ceiling, e.g.:

- `--escalation-budget-usd 0.50`
- `--no-escalation` to disable entirely

---

## CLI Surface (New)

Add a new top-level CLI group `kalshi agent` to isolate “LLM/agentic” behavior from deterministic analytics.

### `kalshi agent analyze`

```bash
uv run kalshi agent analyze TICKER \
  --mode fast|standard|deep \
  --json \
  --max-exa-usd 0.25 \
  --max-llm-usd 0.25 \
  --no-escalation
```

Behavior:

1. Fetch `MarketInfo` + `MarketPriceSnapshot` (Kalshi public endpoints + orderbook).
2. Fetch `ResearchSummary` (SPEC-033 implementation).
3. Call synthesis model to produce `AnalysisResult` (Pydantic-validated).
4. Run verification to produce `VerificationReport`.
5. Optionally escalate and re-synthesize.
6. Print `AgentRunResult` as JSON (default) or Rich (optional `--human`).

### Output contract

For all `kalshi agent ...` commands:

- `--json` output is the default and prints exactly one JSON object (newline-terminated).
- `--output PATH` writes JSON to file (still prints minimal status).

---

## LLM Provider Abstraction (Phase 1)

Phase 1 does not force a specific provider, but defines an interface:

```python
class StructuredSynthesizer(Protocol):
    async def synthesize(self, *, input: SynthesisInput) -> AnalysisResult: ...
```

Implementation options:

1. **Instructor** (recommended): schema-first parsing to Pydantic models.
2. **PydanticAI** (later): migrate orchestrator steps into PydanticAI agent tools if/when needed.

Dependencies should be added as optional extras (e.g., `kalshi-research[agents]`) so the core repo remains
usable without LLM keys.

---

## Implementation Plan

### Phase 1 (single orchestrator + rules verifier)

1. Extend `src/kalshi_research/agent/schemas.py` (introduced in SPEC-033) and add `verify.py`.
2. Add `src/kalshi_research/agent/orchestrator.py` with a pure, testable workflow.
3. Add `src/kalshi_research/cli/agent.py` with `agent analyze` command.
4. Add unit tests:
   - verifier invariants
   - orchestrator behavior with stubbed providers

### Phase 2 (escalation + critics)

1. Add `escalation.py` with deterministic policy + budget enforcement.
2. Add critic “tools” (not independent agents) as pure functions or structured model calls.

### Phase 3 (historical provider + persistence)

1. Add `HistoricalStatsProvider` interface and a stub implementation that returns empty.
2. Optionally persist `AgentRunResult` to DB for later calibration scoring.

---

## Acceptance Criteria

- [ ] `kalshi agent analyze TICKER --json` returns valid `AgentRunResult` JSON and never prints stack traces for expected failures (missing Exa key, empty research, etc.).
- [ ] Agent output (JSON and `--human`) never prints secrets (`.env` contents, API keys/tokens, private key material); sensitive values must be redacted in logs/output.
- [ ] Verification failures are explicit in `VerificationReport` and do not silently pass.
- [ ] Escalation is off by default or gated; multi-agent is never automatically run without meeting policy triggers.
- [ ] Unit tests cover:
  - [ ] schema validation for `AnalysisResult`
  - [ ] verifier logic for citations/range checks
  - [ ] deterministic escalation gating

---

## References

- `docs/architecture/architecture-evolution-plan.md`
- `docs/_vendor-docs/exa-api-reference.md`
- `docs/_vendor-docs/kalshi-api-reference.md`
- SPEC-030 (Exa endpoint strategy): `docs/_specs/SPEC-030-exa-endpoint-strategy.md`
- SPEC-034 (trade safety harness): `docs/_specs/SPEC-034-trade-executor-safety-harness.md`
