# Kalshi Research Platform - Specification Index

## Overview

This document indexes all specifications for building a research platform on top of the Kalshi prediction market API.

**Project Goal:** Build tools for prediction market research and analysis, enabling informed manual trading decisions.

**Non-Goals:** Automated trading, HFT bots, real-time execution systems.

---

## Specifications

| Spec | Name | Priority | Status | Dependencies |
|------|------|----------|--------|--------------|
| [SPEC-001](./SPEC-001-modern-python-foundation.md) | Modern Python Foundation | P0 | Draft | None |
| [SPEC-002](./SPEC-002-kalshi-api-client.md) | Kalshi API Client | P0 | Draft | SPEC-001 |
| [SPEC-003](./SPEC-003-data-layer-storage.md) | Data Layer & Storage | P1 | Draft | SPEC-001, SPEC-002 |
| [SPEC-004](./SPEC-004-research-analysis-framework.md) | Research & Analysis | P1 | Draft | SPEC-001, SPEC-002, SPEC-003 |

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
kalshi scan --filter high_volume --filter close_races

# Start continuous collection
kalshi data collect --interval 15m
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

## Future Specs (Not Yet Written)

- **SPEC-005**: Alerting & Notifications
- **SPEC-006**: Backtesting Framework
- **SPEC-007**: Correlation Analysis
- **SPEC-008**: News Sentiment Integration
