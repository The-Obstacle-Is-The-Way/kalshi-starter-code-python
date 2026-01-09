# Specifications Index

This directory contains **active** design specifications for current work (planned or implemented).

## Current Status

**2 active specifications.**

## Next ID Tracker

Use this ID for the next specification you create:
**SPEC-027**

---

## Active Specifications

| ID | Title | Priority | Status | Dependencies |
|---|---|---|---|---|
| **SPEC-024** | [Exa Research Agent](SPEC-024-exa-research-agent.md) | P2 | 📋 Planned (Future) | SPEC-020-023 |
| **SPEC-026** | [Liquidity Analysis](SPEC-026-liquidity-analysis.md) | P1 | 📋 Planned (TODO-010) | None |

### SPEC-024: Exa Research Agent

**Status**: Planned (Future) - See [TODO-00C](../_todo/TODO-00C-exa-research-agent.md)

Autonomous research agent that coordinates Exa searches, news collection, and thesis tracking. This is a complex feature (~1200 lines of spec) that depends on the implemented Exa integration (SPEC-020 through SPEC-023).

**Recommendation**: Defer until there's a clear need for automated research vs interactive MCP-based research.

### SPEC-026: Liquidity Analysis

**Status**: Active - See [TODO-010](../_todo/TODO-010-liquidity-analysis.md)

Comprehensive liquidity analysis framework for Kalshi markets. Addresses the deprecated `liquidity` field by providing:
- Weighted orderbook depth scoring
- Slippage estimation (walk-the-book)
- Composite liquidity score (0-100)
- Max safe order size calculation

**Recommendation**: Implement now. High value for trading quality.

---

## Recently Implemented

### SPEC-025: Market Open Time Display

**Status**: ✅ Implemented (2026-01-09) via TODO-005

Added `open_time` and `created_time` display to `market get` CLI command. Implemented TemporalValidator for research workflows.

**Note**: Should be moved to archive.

---

## Archive (Implemented)

Completed specifications are stored in
[`docs/_archive/specs/`](https://github.com/The-Obstacle-Is-The-Way/kalshi-starter-code-python/tree/main/docs/_archive/specs/).

Note: `docs/_archive/**` is intentionally excluded from the MkDocs site build (historical provenance only).

| ID | Title | Status |
|---|---|---|
| **SPEC-025** | Market Open Time Display | ✅ Implemented (2026-01-09) |
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
