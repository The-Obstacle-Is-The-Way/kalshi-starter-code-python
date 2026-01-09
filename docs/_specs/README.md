# Specifications Index

This directory contains **active** design specifications for current work (planned or implemented).

## Current Status

**2 active specifications** (both planned, pending implementation).

## Next ID Tracker

Use this ID for the next specification you create:
**SPEC-026**

---

## Active Specifications

| ID | Title | Priority | Status | Dependencies |
|---|---|---|---|---|
| **SPEC-024** | [Exa Research Agent](SPEC-024-exa-research-agent.md) | P2 | 📋 Planned | SPEC-020, SPEC-021, SPEC-023 |
| **SPEC-025** | [Market Open Time Display](SPEC-025-market-open-time-display.md) | P1 | 📋 Planned | None |

### SPEC-024: Exa Research Agent

Autonomous research agent that coordinates Exa searches, news collection, and thesis tracking. Depends on the now-implemented Exa integration (SPEC-020 through SPEC-023).

### SPEC-025: Market Open Time Display

**High Priority** - Add `open_time` and `created_time` to `market get` CLI output. This is a critical fix to prevent temporal validation errors in research workflows (see TODO-005).

Related to: A catastrophic research failure where a recommendation was made based on events that occurred BEFORE the market opened.

---

## Archive (Implemented)

Completed specifications are stored in
[`docs/_archive/specs/`](https://github.com/The-Obstacle-Is-The-Way/kalshi-starter-code-python/tree/main/docs/_archive/specs/).

Note: `docs/_archive/**` is intentionally excluded from the MkDocs site build (historical provenance only).

| ID | Title | Status |
|---|---|---|
| **SPEC-023** | Exa-Thesis Integration | ✅ Implemented (2026-01-09) |
| **SPEC-022** | Exa News & Sentiment Pipeline | ✅ Implemented (2026-01-09) |
| **SPEC-021** | Exa-Powered Market Research | ✅ Implemented (2026-01-09) |
| **SPEC-020** | Exa API Client Foundation | ✅ Implemented (2026-01-09) |
| **SPEC-019** | CLI Test Suite Refactor | ✅ Implemented |
| **SPEC-018** | CLI Refactoring | ✅ Implemented |
| **SPEC-017** | Alert Monitor Daemon Mode | ✅ Implemented |
| **SPEC-016** | Demo Environment Testing | ✅ Implemented |
| **SPEC-015** | Rate Limit Tier Management | ✅ Implemented |
| **SPEC-014** | WebSocket Real-Time Data | ✅ Implemented |
| **SPEC-013** | Portfolio Sync Implementation | ✅ Implemented |
| **SPEC-012** | Developer Experience | ✅ Implemented |
| **SPEC-011** | Manual Trading Support | ✅ Implemented |
| **SPEC-010** | CLI Completeness | ✅ Implemented |
| **SPEC-009** | Cleanup Documentation | ✅ Implemented |
| **SPEC-008** | Research Notebooks Backtesting | ✅ Implemented |
| **SPEC-007** | Probability Tracking Visualization | ✅ Implemented |
| **SPEC-006** | Event Correlation Analysis | ✅ Implemented |
| **SPEC-005** | Alerts Notifications | ✅ Implemented |
| **SPEC-004** | Research Analysis Framework | ✅ Implemented |
| **SPEC-003** | Data Layer Storage | ✅ Implemented |
| **SPEC-002** | Kalshi API Client | ✅ Implemented |
| **SPEC-001** | Modern Python Foundation | ✅ Implemented |
