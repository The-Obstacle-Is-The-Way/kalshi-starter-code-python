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
| SPEC-030 | [Exa Endpoint Strategy (Cost-Bounded, Verifiable Research)](SPEC-030-exa-endpoint-strategy.md) | 🟡 Phase 1 Complete (DEBT-041: Phase 2/3 incomplete) |
| SPEC-034 | [TradeExecutor Safety Harness (Budgeted, Safe-by-Default)](SPEC-034-trade-executor-safety-harness.md) | 🟡 Phase 1 implemented (Phase 2 wiring deferred) |
| SPEC-042 | [LLM Synthesizer Implementation](SPEC-042-llm-synthesizer-implementation.md) | 🟡 Phase 1 Complete (OpenAI/Gemini backends not implemented) |

### Remaining Work

```text
🟡 SPEC-030 (Exa Policy)           ← Phase 1 done; Phase 2/3 require CLI budget flags
🟡 SPEC-034 (TradeExecutor)        ← Phase 1 done; Phase 2 wiring deferred
🟡 SPEC-042 (LLM Synthesizer)      ← Phase 1 done; OpenAI/Gemini backends not implemented
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

### Recently Archived (2026-01-19)

| ID | Title | Status |
|---|---|---|
| **SPEC-038** | [Exa Websets API Coverage (Monitoring + Alerts Foundation)](../_archive/specs/SPEC-038-exa-websets-endpoint-coverage.md) | ✅ Phase 1 Complete |
| **SPEC-033** | [Exa Research Agent (Cost-Bounded, Reproducible)](../_archive/specs/SPEC-033-exa-research-agent.md) | ✅ Implemented |
| **SPEC-032** | [Agent System Orchestration (Single-Agent Default + Escalation)](../_archive/specs/SPEC-032-agent-system-orchestration.md) | ✅ Phase 1 Complete |
| **SPEC-031** | [Scanner Quality Profiles (Slop Filtering + "Get In Early" Mode)](../_archive/specs/SPEC-031-scanner-quality-profiles.md) | ✅ Phase 1–2 Complete |
| **SPEC-028** | [Topic Search & Market Discovery (DB + CLI)](../_archive/specs/SPEC-028-topic-search-and-discovery.md) | ✅ Implemented |

### Previously Archived

| ID | Title | Status |
|---|---|---|
| SPEC-041 | [Phase 5: Remaining High-Value Endpoints](../_archive/specs/SPEC-041-phase5-remaining-endpoints.md) | ✅ Complete (2026-01-16) |
| SPEC-040 | [Complete Kalshi Endpoint Implementation (TDD)](../_archive/specs/SPEC-040-kalshi-endpoint-implementation-complete.md) | ✅ Complete (2026-01-15) |
| SPEC-039 | [New Market Alerts (Information Arbitrage)](../_archive/specs/SPEC-039-new-market-alerts.md) | ✅ Phase 1 Complete (2026-01-16) |
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
