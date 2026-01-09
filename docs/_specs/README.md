# Specifications Index

This directory contains **active** design specifications for pending features.

## Current Status

**5 active specifications** for Exa API integration.

## Next ID Tracker

Use this ID for the next specification you create:
**SPEC-025**

---

## Active Specifications (Exa Integration)

These specs define a comprehensive Exa API integration following TDD principles with thin vertical slices.

| ID | Title | Priority | Status | Dependencies |
|---|---|---|---|---|
| **SPEC-020** | [Exa API Client Foundation](SPEC-020-exa-api-client.md) | P1 | 📋 Planned | SPEC-001, SPEC-002 |
| **SPEC-021** | [Exa-Powered Market Research](SPEC-021-exa-market-research.md) | P1 | 📋 Planned | SPEC-020 |
| **SPEC-022** | [Exa News & Sentiment Pipeline](SPEC-022-exa-news-sentiment.md) | P2 | 📋 Planned | SPEC-020, SPEC-003 |
| **SPEC-023** | [Exa-Thesis Integration](SPEC-023-exa-thesis-integration.md) | P1 | 📋 Planned | SPEC-020, SPEC-021 |
| **SPEC-024** | [Exa Research Agent](SPEC-024-exa-research-agent.md) | P2 | 📋 Planned | SPEC-020, SPEC-021, SPEC-023 |

### Implementation Order

**Phase 1: Foundation**
1. SPEC-020: Build the Exa API client (async, typed, tested)

**Phase 2: Core Research**
2. SPEC-021: Market context research CLI
3. SPEC-023: Thesis research integration

**Phase 3: Advanced Features**
4. SPEC-022: News collection & sentiment pipeline
5. SPEC-024: Autonomous research agent

### Estimated Total Effort

- **Lines of Code**: ~3,000-4,000 (src + tests)
- **New Modules**: `src/kalshi_research/exa/`, `src/kalshi_research/agent/`, `src/kalshi_research/news/`
- **New CLI Commands**: ~15 new commands across `research`, `news`, `agent` groups
- **Database Tables**: 4 new tables (news tracking)

---

## Archive (Implemented)

Completed specifications are stored in
[`docs/_archive/specs/`](https://github.com/The-Obstacle-Is-The-Way/kalshi-starter-code-python/tree/main/docs/_archive/specs/).

Note: `docs/_archive/**` is intentionally excluded from the MkDocs site build (historical provenance only).

| ID | Title | Status |
|---|---|---|
| **SPEC-018** | CLI Refactoring | ✅ Implemented |
| **SPEC-019** | CLI Test Suite Refactor | ✅ Implemented |
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
