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
- [ ] **SPEC-032**: Agent System Orchestration → `docs/_specs/SPEC-032-agent-system-orchestration.md`

### Phase 2: P2 Specs (Optional / When Needed)

- [ ] **SPEC-038**: Exa Websets API Coverage → `docs/_specs/SPEC-038-exa-websets-endpoint-coverage.md`
- [ ] **SPEC-034**: TradeExecutor Safety Harness (Phase 2 hardening) → `docs/_specs/SPEC-034-trade-executor-safety-harness.md`

### Phase 3: Final Verification

- [ ] **FINAL-GATES**: All quality gates pass (`pre-commit`, `mypy`, `pytest`, `mkdocs build --strict`)

---

**Guidelines:**

- SPEC-* tasks require a follow-up review iteration and a `[REVIEWED]` marker.
- Read [`AGENTS.md`](AGENTS.md) first (project intent + safety constraints).
- Complete SPEC-033 before SPEC-032 (SPEC-032 depends on SPEC-033 for the research provider + shared schemas).
- SPEC-028 is independent (local DB) and can be implemented anytime.
- Do not run cost-incurring or irreversible operations during the loop (Exa paid calls, live trading). Prefer unit tests + fixtures.

---

## Work Log

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
