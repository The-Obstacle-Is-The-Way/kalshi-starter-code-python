# Specifications (Active Implementation)

This directory contains **active** design specifications - work happening NOW.

## Distinction from `_future/`

| Directory | Purpose | When to Use |
|-----------|---------|-------------|
| `_specs/` | **Active implementation** | Work happening NOW |
| `_future/` | **Backlog** | Blocked, deferred, or planned later |

---

## Current Active Specs

| ID | Title | Status |
|---|---|---|
| SPEC-028 | [Topic Search & Market Discovery (DB + CLI)](SPEC-028-topic-search-and-discovery.md) | 📝 Ready |
| SPEC-030 | [Exa Endpoint Strategy (Cost-Bounded, Verifiable Research)](SPEC-030-exa-endpoint-strategy.md) | ✅ Phase 1 Complete |
| SPEC-031 | [Scanner Quality Profiles (Slop Filtering + "Get In Early" Mode)](SPEC-031-scanner-quality-profiles.md) | ✅ Phase 1–2 Complete (Phase 3 deferred) |
| SPEC-032 | [Agent System Orchestration (Single-Agent Default + Escalation)](SPEC-032-agent-system-orchestration.md) | 🟡 **Phase 1 Complete** (uses MockSynthesizer - see [DEBT-037](../_debt/DEBT-037-mock-synthesizer-production-gap.md)) |
| SPEC-033 | [Exa Research Agent (Cost-Bounded, Reproducible)](SPEC-033-exa-research-agent.md) | ✅ **Phase 1 Complete** |
| SPEC-034 | [TradeExecutor Safety Harness (Budgeted, Safe-by-Default)](SPEC-034-trade-executor-safety-harness.md) | 🟡 Phase 1 implemented (Phase 2 deferred) |
| SPEC-038 | [Exa Websets API Coverage (Monitoring + Alerts Foundation)](SPEC-038-exa-websets-endpoint-coverage.md) | 📝 Draft |
| **SPEC-042** | [LLM Synthesizer Implementation](SPEC-042-llm-synthesizer-implementation.md) | 🔴 **P1 - NEXT** (fixes DEBT-037, enables agent value) |

**Critical:** SPEC-042 is the highest priority active spec. SPEC-032 uses MockSynthesizer until SPEC-042 is implemented.

### Implementation Order (Critical Path)

Execution order is tracked in `PROGRESS.md` (Ralph Wiggum queue). This section lists the dependency order.

```text
✅ SPEC-030 (Exa Policy)           ← DONE: ExaMode, ExaPolicy, ExaBudget
    ↓
✅ SPEC-033 (Exa Research Agent)   ← DONE: ResearchAgent, crash recovery, CLI
    ↓
🟡 SPEC-032 (Agent Orchestration)  ← DONE (Phase 1): Uses MockSynthesizer
    ↓
🔴 SPEC-042 (LLM Synthesizer)      ← NEXT: Implement real LLM synthesizer (Anthropic-first per spec)

🟡 SPEC-034 (TradeExecutor)        ← Phase 1 done; Phase 2 deferred
📝 SPEC-028 (Topic Search)         ← Independent, can implement anytime
📝 SPEC-038 (Exa Websets)          ← P2, future automation
```

---

## Next ID Tracker

Use this ID for the next specification:
**SPEC-043**

---

## Workflow

1. **New spec**: Create `SPEC-XXX-description.md` here
2. **Future work**: Move to `_future/` if deprioritized
3. **Implemented**: Move to `_archive/specs/`

---

## Archive (Implemented)

Completed specifications are stored under `docs/_archive/specs/` (excluded from the MkDocs site
build). See [`docs/_archive/README.md`](../_archive/README.md) for the archive structure.

| ID | Title | Status |
|---|---|---|
| **SPEC-041** | [Phase 5: Remaining High-Value Endpoints](../_archive/specs/SPEC-041-phase5-remaining-endpoints.md) | ✅ Complete (2026-01-16) |
| **SPEC-040** | [Complete Kalshi Endpoint Implementation (TDD)](../_archive/specs/SPEC-040-kalshi-endpoint-implementation-complete.md) | ✅ Complete (2026-01-15) |
| **SPEC-039** | [New Market Alerts (Information Arbitrage)](../_archive/specs/SPEC-039-new-market-alerts.md) | ✅ Phase 1 Complete (2026-01-16) |
| SPEC-037 | [Kalshi Missing Endpoints Phase 1](../_archive/specs/SPEC-037-kalshi-missing-endpoints-phase1.md) | 🔀 Superseded by SPEC-040 |
| SPEC-036 | [Category Filtering for Markets](../_archive/specs/SPEC-036-category-filtering.md) | ✅ Implemented |
| SPEC-035 | [Ticker Display Enhancement](../_archive/specs/SPEC-035-ticker-display-enhancement.md) | ✅ Implemented |
| SPEC-029 | [Kalshi Endpoint Coverage Strategy](../_archive/specs/SPEC-029-kalshi-endpoint-coverage-strategy.md) | 🔀 Superseded by SPEC-040 |
| SPEC-027 | [Settlement Timestamp Support](../_archive/specs/SPEC-027-settlement-timestamp.md) | ✅ Implemented |
| SPEC-026 | [Liquidity Analysis](../_archive/specs/SPEC-026-liquidity-analysis.md) | ✅ Implemented |
| SPEC-025 | [Market Open Time Display](../_archive/specs/SPEC-025-market-open-time-display.md) | ✅ Implemented |
| SPEC-023 | Exa-Thesis Integration | ✅ Implemented |
| SPEC-022 | Exa News & Sentiment Pipeline | ✅ Implemented |
| SPEC-021 | Exa-Powered Market Research | ✅ Implemented |
| SPEC-020 | Exa API Client Foundation | ✅ Implemented |
| SPEC-001 to SPEC-019 | Foundation specs | ✅ Implemented |
