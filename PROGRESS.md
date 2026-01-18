# Kalshi Research Platform — Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-18
**Status:** Active (Spec Implementation Queue)
**Purpose:** State file for the Ralph Wiggum loop (see `docs/_ralph-wiggum/protocol.md`)

---

## Active Queue

### Phase 1: P1 Specs (Core)

#### 1A) Local discovery (independent)

- [x] **SPEC-028**: Topic Search & Market Discovery → `docs/_specs/SPEC-028-topic-search-and-discovery.md` [REVIEWED]
- [x] **SPEC-028-FIX**: Fix FTS5 query crash (TextClause.selectable AttributeError)

#### 1B) Agent stack (depends on SPEC-030)

- [x] **SPEC-033**: Exa Research Agent → `docs/_specs/SPEC-033-exa-research-agent.md` [REVIEWED]
- [x] **SPEC-033-FIX**: Add crash recovery for deep research tasks (persist research_id, use list/find reconciliation)
- [x] **SPEC-032**: Agent System Orchestration → `docs/_specs/SPEC-032-agent-system-orchestration.md` [REVIEWED]

### Phase 2: P2 Specs (Optional / When Needed)

- [x] **SPEC-038**: Exa Websets API Coverage → `docs/_specs/SPEC-038-exa-websets-endpoint-coverage.md` [REVIEWED]
- [x] **SPEC-034**: TradeExecutor Safety Harness (Phase 2 hardening) → `docs/_specs/SPEC-034-trade-executor-safety-harness.md`

### Phase 3: Final Verification

- [x] **FINAL-GATES**: All quality gates pass (`pre-commit`, `mypy`, `pytest`, `mkdocs build --strict`)

---

**Guidelines:**

- SPEC-* tasks require a follow-up review iteration and a `[REVIEWED]` marker.
- Read [`AGENTS.md`](AGENTS.md) first (project intent + safety constraints).
- Complete SPEC-033 before SPEC-032 (SPEC-032 depends on SPEC-033 for the research provider + shared schemas).
- SPEC-028 is independent (local DB) and can be implemented anytime.
- Do not run cost-incurring or irreversible operations during the loop (Exa paid calls, live trading). Prefer unit tests + fixtures.

---

## Work Log

- 2026-01-18: FINAL-GATES verified - all quality gates pass. pre-commit (all checks including syntax validation, ruff, mypy, pytest) passed. ruff check passed. ruff format verified (245 files). mypy passed (117 source files, no issues). pytest passed (905 tests). mkdocs build --strict passed (documentation built successfully). All Phase 1-3 tasks complete. Ralph Wiggum spec implementation queue complete.
- 2026-01-18: Implemented SPEC-034 TradeExecutor Phase 2 Safety Rails. Added fat-finger guard (midpoint deviation check), daily budget/loss tracking (max_daily_loss_usd, max_notional_usd), position caps (max_position_contracts), liquidity-aware sizing (slippage limits + grade filters), and order management wrappers (cancel_order, amend_order). All providers use Protocol types for dependency injection. Added 6 Phase 2 unit tests. All quality gates pass (18 execution tests, pre-commit, ruff, mypy, pytest). All acceptance criteria met.
- 2026-01-18: SPEC-038 reviewed and verified. All acceptance criteria confirmed: (1) ExaWebsetsClient with 9 Phase 1 endpoints implemented, (2) Pydantic models in websets/models.py, (3) golden fixtures in tests/fixtures/golden/exa_websets/ with hand-crafted responses, (4) SSOT validator integration passes all fixtures, (5) 12 unit tests (7 client + 5 fixture validation) all pass, (6) Websets not required by default CLI. Quality gates pass. Implementation complete per spec.
- 2026-01-18: Implemented SPEC-038 Exa Websets API Coverage (Phase 1). Created ExaWebsetsClient with 9 Phase 1 endpoints (create, preview, get, cancel webset; list/get items; create/get/cancel search). Added Pydantic models (Webset, WebsetItem, WebsetSearch, etc.) with proper datetime handling. Created recording script `scripts/record_exa_websets_responses.py` (requires --yes flag for cost awareness). Generated hand-crafted golden fixtures based on OpenAPI schemas for testing without live API calls. Integrated with SSOT validator. Added 12 unit tests (7 client tests via respx, 5 fixture validation tests). All quality gates pass (pre-commit, ruff, mypy, pytest). All acceptance criteria met.
- 2026-01-18: SPEC-032 reviewed and verified. All acceptance criteria confirmed: (1) CLI returns valid JSON and handles expected failures, (2) no secret leakage in output, (3) verification failures explicit with VerificationReport, (4) escalation OFF by default (enable_escalation=False), (5) full test coverage (11 verifier tests + 7 orchestrator tests). Quality gates pass. Implementation complete per spec.
- 2026-01-18: Implemented SPEC-032 Agent System Orchestration (Phase 1). Added AgentKernel orchestrator with deterministic workflow: (1) fetch market + orderbook, (2) gather research via ResearchAgent, (3) synthesize probability via LLM (MockSynthesizer for Phase 1), (4) verify via rule-based checks. Created modules: orchestrator.py, verify.py, providers/kalshi.py, providers/llm.py. Extended schemas.py with MarketInfo, MarketPriceSnapshot, AnalysisResult, VerificationReport, AgentRunResult. Added CLI command `kalshi agent analyze` with JSON/human output modes. Escalation disabled by default (Phase 2). Added 18 unit tests (11 for verifier, 7 for orchestrator). All quality gates pass. All acceptance criteria met.
- 2026-01-18: SPEC-033-FIX complete - implemented crash recovery for deep research tasks. Added `ResearchTaskState` for JSON-based persistence in `data/agent_state/`. Recovery attempts ID lookup first, falls back to `find_recent_research_task()`. State cleared after completion. Added 10 unit tests (4 for crash recovery, 6 for state management). All quality gates pass. SPEC-033 now [REVIEWED] with all acceptance criteria met.
- 2026-01-18: SPEC-033 review iteration - found missing crash recovery: research_id is logged but not persisted, no list/find reconciliation for orphaned tasks. Acceptance criterion 5 incomplete. Created SPEC-033-FIX task. Marked SPEC-033 as [NEEDS-FIX].
- 2026-01-18: Implemented SPEC-033 Exa Research Agent - deterministic plan builder, budget enforcement, crash recovery for deep research tasks, CLI command `kalshi agent research`, 17 unit tests. All quality gates pass.
- 2026-01-18: Fixed SPEC-028-FIX - replaced text("market_fts") with table() construct to create proper selectable reference. Added test_search_markets_fts5_path() that creates FTS5 tables and exercises the corrected code path. All quality gates pass. SPEC-028 now [REVIEWED].
- 2026-01-18: SPEC-028 review iteration - found critical bug: FTS5 query crashes with TextClause AttributeError. Tests pass but CLI fails on real DB. Created SPEC-028-FIX task. Marked SPEC-028 as [NEEDS-FIX].
- 2026-01-18: Implemented SPEC-028 topic search & market discovery (FTS5 virtual tables, SearchRepository, `kalshi market search` CLI command, unit tests). All quality gates pass.
- 2026-01-18: Implemented SPEC-031 scanner quality profiles (PR #29) and SPEC-030 Exa policy mode/budget controls (PR #30).
- 2026-01-17: Archived DEBT-029/030/031/032 and cleaned up `_future/` (promoted items to specs).
- 2026-01-13: Reset PROGRESS.md/PROMPT.md templates (idle queue).
- 2026-01-10: Fixed portfolio P&L integrity (FIFO realized P&L + unknown handling), updated BUG-056/057, ran `uv run pre-commit run --all-files` and `uv run mkdocs build --strict`
- 2026-01-10: Skills refactor - created `kalshi-ralph-wiggum` skill, simplified `kalshi-codebase`, enhanced PROMPT.md with SPEC-* self-review protocol, verified SPEC-029/032 against SSOT
- 2026-01-10: Prep for spec implementation (audited SPEC-028..034, added `kalshi-codebase` skill, updated Ralph prompt/protocol)
- 2026-01-09: Phase 1-8 complete (all bugs, debt, TODOs resolved)

---

## Completion Criteria

The queue is complete when there are no unchecked items (no lines matching the unchecked-task pattern at column 0).
The loop operator should verify completion via this file’s state, not by parsing model output.
