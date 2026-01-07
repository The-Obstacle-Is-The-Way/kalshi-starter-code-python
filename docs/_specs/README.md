# Kalshi Research Platform - Specification Index

## Overview

This document indexes all specifications for building a research platform on top of the Kalshi prediction market API.

**Project Goal:** Build tools for prediction market research and analysis, enabling informed manual trading decisions.

**Non-Goals:** Automated trading, HFT bots, real-time execution systems.

---

## Specifications

### Specs (Current Status)

| Spec | Name | Priority | Status | Dependencies |
|------|------|----------|--------|--------------|
| [SPEC-001](./SPEC-001-modern-python-foundation.md) | Modern Python Foundation | P0 | ✅ Implemented | None |
| [SPEC-002](./SPEC-002-kalshi-api-client.md) | Kalshi API Client | P0 | ✅ Implemented (core) | SPEC-001 |
| [SPEC-003](./SPEC-003-data-layer-storage.md) | Data Layer & Storage | P1 | ✅ Implemented (core) | SPEC-001, SPEC-002 |
| [SPEC-004](./SPEC-004-research-analysis-framework.md) | Research & Analysis | P1 | ✅ Implemented | SPEC-001, SPEC-002, SPEC-003 |
| [SPEC-005](./SPEC-005-alerts-notifications.md) | Alerts & Notifications | P1 | ✅ Implemented | SPEC-002, SPEC-003, SPEC-004 |
| [SPEC-006](./SPEC-006-event-correlation-analysis.md) | Event Correlation Analysis | P2 | ✅ Implemented | SPEC-002, SPEC-003 |
| [SPEC-007](./SPEC-007-probability-tracking-visualization.md) | Probability Tracking & Visualization | P2 | ✅ Implemented | SPEC-002, SPEC-003, SPEC-004 |
| [SPEC-008](./SPEC-008-research-notebooks-backtesting.md) | Research Notebooks & Backtesting | P2 | ✅ Implemented | SPEC-002 through SPEC-007 |
| [SPEC-009](./SPEC-009-cleanup-documentation.md) | Legacy Cleanup & Documentation | P2 | ✅ Implemented | SPEC-001 through SPEC-008 |
| [SPEC-010](./SPEC-010-cli-completeness.md) | CLI Completeness | P2 | ✅ Implemented | SPEC-005 through SPEC-008 |
| [SPEC-011](./SPEC-011-manual-trading-support.md) | Manual Trading Support | P2 | ✅ Implemented (partial) | SPEC-002, SPEC-004 |
| [SPEC-012](./SPEC-012-developer-experience.md) | Developer Experience | P3 | ✅ Complete | All previous specs |

---

## Implementation Order

```
Phase 1: Foundation (SPEC-001)
├── Set up pyproject.toml with uv
├── Configure ruff, mypy, pytest
├── Create src/ layout
├── Set up GitHub Actions CI
└── Estimated: 2-4 hours

Phase 2: API Client (SPEC-002)
├── Implement Pydantic models
├── Build public client (no auth)
├── Add pagination, rate limiting
├── Port existing auth client
└── Estimated: 4-8 hours

Phase 3: Data Layer (SPEC-003)
├── Design SQLite schema
├── Implement repositories
├── Build data fetcher
├── Add scheduler for collection
└── Estimated: 6-10 hours

Phase 4: Analysis (SPEC-004)
├── Calibration module
├── Edge detection
├── Market scanner
├── Thesis tracking
└── Estimated: 8-12 hours
```

---

## Quick Start After Implementation

```bash
# Install dependencies
uv sync --dev

# Initialize database
kalshi data init

# Sync market data
kalshi data sync-markets

# Take price snapshot
kalshi data snapshot

# Run market scanner
kalshi scan opportunities --filter close-race

# Start continuous collection
kalshi data collect --interval 15
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │    CLI      │  │  Jupyter    │  │    (Future: Web UI)     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Analysis Layer (SPEC-004)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Calibration │  │   Scanner   │  │    Edge Detection       │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     Data Layer (SPEC-003)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  Fetcher    │  │ Repositories│  │       SQLite DB         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    API Client (SPEC-002)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │Public Client│  │ Auth Client │  │    Pydantic Models      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────────────┐
                    │   Kalshi API    │
                    │  (REST + WS)    │
                    └─────────────────┘
```

---

## Key Decisions

### Why uv over pip/poetry?

- 10-100x faster dependency resolution
- Built-in lockfile
- No virtualenv management needed
- Active development by Astral (ruff authors)

### Why SQLite over PostgreSQL?

- Zero deployment complexity
- Single file backup
- Fast enough for our scale (<10GB/year)
- Can migrate later if needed

### Why httpx over requests?

- Native async support
- Better timeout handling
- Modern API
- Built-in retry support

### Why Pydantic over dataclasses?

- Automatic validation
- JSON serialization built-in
- Great IDE support
- Industry standard

---

## Testing Strategy

| Layer | Test Type | Tools | Coverage Target |
|-------|-----------|-------|-----------------|
| API Client | Unit + Integration | pytest, respx | 90% |
| Data Layer | Unit | pytest, in-memory SQLite | 85% |
| Analysis | Unit + Property | pytest, hypothesis | 85% |
| CLI | Integration | pytest, click testing | 70% |

---

## Risk Registry

| Risk | Mitigation |
|------|------------|
| Kalshi API changes | Version pin, monitor changelog |
| Rate limiting | Configurable limits, backoff |
| Data corruption | Regular backups, validation |
| Scope creep | Stick to research, no auto-trading |

---

## Future Work

- Portfolio authenticated sync (`kalshi portfolio sync`) once credentials + endpoints are wired.
- Additional Kalshi endpoints (fills, settlements history, series metadata) as needed.
