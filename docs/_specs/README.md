# Kalshi Research Platform - Specification Index

## Overview

This document indexes all specifications for building a research platform on top of the Kalshi prediction market API.

**Project Goal:** Build tools for prediction market research and analysis, enabling informed manual trading decisions.

**Non-Goals:** Automated trading, HFT bots, real-time execution systems.

---

## Specifications

### Core Platform (Implemented)

| Spec | Name | Priority | Status | Dependencies |
|------|------|----------|--------|--------------|
| [SPEC-001](./SPEC-001-modern-python-foundation.md) | Modern Python Foundation | P0 | ✅ Complete | None |
| [SPEC-002](./SPEC-002-kalshi-api-client.md) | Kalshi API Client | P0 | ✅ Complete | SPEC-001 |
| [SPEC-003](./SPEC-003-data-layer-storage.md) | Data Layer & Storage | P1 | ⚠️ Partial | SPEC-001, SPEC-002 |
| [SPEC-004](./SPEC-004-research-analysis-framework.md) | Research & Analysis | P1 | ⚠️ Partial | SPEC-001, SPEC-002, SPEC-003 |

### Extended Platform (Not Started)

| Spec | Name | Priority | Status | Dependencies |
|------|------|----------|--------|--------------|
| [SPEC-005](./SPEC-005-alerts-notifications.md) | Alerts & Notifications | P1 | ❌ Not Started | SPEC-002, SPEC-003, SPEC-004 |
| [SPEC-006](./SPEC-006-event-correlation-analysis.md) | Event Correlation Analysis | P2 | ❌ Not Started | SPEC-002, SPEC-003 |
| [SPEC-007](./SPEC-007-probability-tracking-visualization.md) | Probability Tracking & Visualization | P2 | ❌ Not Started | SPEC-002, SPEC-003, SPEC-004 |
| [SPEC-008](./SPEC-008-research-notebooks-backtesting.md) | Research Notebooks & Backtesting | P2 | ❌ Not Started | SPEC-002 through SPEC-007 |

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

## Extended Implementation Order

After completing SPEC-001 through SPEC-004 (core platform), the extended features can be implemented:

```
Phase 5: Alerts & Notifications (SPEC-005)
├── AlertCondition and Alert models
├── AlertMonitor with condition checking
├── Console, File, Webhook notifiers
├── CLI commands for alert management
└── Estimated: 4-6 hours

Phase 6: Event Correlation (SPEC-006)
├── CorrelationAnalyzer class
├── Pearson/Spearman correlation
├── Inverse market detection
├── Arbitrage opportunity finder
└── Estimated: 4-6 hours

Phase 7: Visualization & Metrics (SPEC-007)
├── MarketMetrics class (spread, volatility, volume)
├── Calibration curve plotting
├── Probability timeline charts
├── Edge histograms and spread charts
└── Estimated: 4-6 hours

Phase 8: Notebooks & Backtesting (SPEC-008)
├── ThesisBacktester class
├── Notebook utility functions
├── Template notebooks (exploration, calibration, edge detection)
├── P&L and accuracy tracking
└── Estimated: 6-8 hours
```

## Future Specs (Potential)

Beyond SPEC-008, potential future specs include:

- **SPEC-009**: News Sentiment Integration
- **SPEC-010**: Portfolio Analytics (Kelly criterion, risk management)
- **SPEC-011**: Web Dashboard
- **SPEC-012**: Machine Learning Models
