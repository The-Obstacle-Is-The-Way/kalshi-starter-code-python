# Technical Debt Register

**Last Audit:** 2026-01-10

---

## Outstanding Debt

### DEBT-007: A+ Engineering Robustness Delta (Operational Hardening Gaps)

**Priority:** P2
**Status:** 🔴 Active
**Summary:** Close confidence gaps in runtime schema upgrades, scheduled live API contract validation, DB invariants, and trade safety harness (CI runs mocked E2E; pre-commit is unit-only).
**Plan:** `docs/_debt/DEBT-007-a-plus-engineering-robustness-delta.md`

### DEBT-008: Dead Code Cleanup (True Slop)

**Priority:** P2
**Status:** 🔴 Active
**Summary:** Delete ~400 LOC of verified unused code (`EdgeDetector`, `TemporalValidator`, etc.) identified in the bloat audit.
**Plan:** `docs/_debt/DEBT-008-dead-code-cleanup.md`

### DEBT-009: Finish Halfway Implementations

**Priority:** P3
**Status:** 🔴 Active
**Summary:** Wire in 9 functional but unreachable features: Alert Notifiers (FileNotifier, WebhookNotifier), Trade Sync, Exa Similar/Deep Research, Candlestick History, Exchange Status, WebSocket Streaming, Liquidity Safety Sizing.
**Plan:** `docs/_debt/DEBT-009-finish-halfway-implementations.md`

### DEBT-010: Reduce Boilerplate & Structural Bloat

**Priority:** P3
**Status:** 🔴 Active
**Summary:** Refactor repeated DB initialization patterns and simplify the repository layer.
**Plan:** `docs/_debt/DEBT-010-reduce-boilerplate.md`

---

## Implemented via Spec

| ID | Status | Resolution |
|----|--------|------------|
| DEBT-004 | Implemented via Spec | [SPEC-027](../_archive/specs/SPEC-027-settlement-timestamp.md) |

---

## Won't Fix (Principled Closures)

### DEBT-002 Phase 2-3 (Strategy Configuration) - CLOSED

**Decision:** Won't Fix
**Date:** 2026-01-09
**Rationale:** First-principles analysis using Clean Code (Robert C. Martin) and SOLID principles.

**Why this is NOT a problem:**
1. Current defaults are **named parameters** (not magic numbers): `high_volume_threshold=10000`
2. Current pattern uses **constructor injection** (proper Dependency Inversion)
3. Values are **typed**, **documented**, and **injectable**
4. CLI already provides override flags (`--min-volume`, `--max-spread`)
5. Adding `AnalysisConfig` would be **premature abstraction** (YAGNI violation)

**What Uncle Bob would say:** The code follows DIP - high-level modules (CLI) inject values into low-level modules (Scanner). This IS the pattern.

**Re-open if:**
- Adding config file (YAML/TOML) support for user customization
- 10+ analysis classes need shared defaults
- Runtime config reloading required

**Sources:**
- [Clean Code Principles - Uncle Bob](https://gist.github.com/wojteklu/73c6914cc446146b8b533c0988cf8d29)
- [SOLID Principles - DigitalOcean](https://www.digitalocean.com/community/conceptual-articles/s-o-l-i-d-the-first-five-principles-of-object-oriented-design)
- [Python DI Best Practices - ArjanCodes](https://arjancodes.com/blog/python-dependency-injection-best-practices/)

---

## Deferred (Low Priority)

### No `interfaces/` or `ports/` package

**Priority:** Low
**Status:** Acceptable for research platform

Hexagonal architecture purists would want explicit interface definitions (abstract base classes for repositories, clients, etc.). For a research platform that's unlikely to swap implementations, this is acceptable.

**If needed later:**

```text
src/kalshi_research/
├── interfaces/
│   ├── __init__.py
│   ├── client.py        # Protocol/ABC for API client
│   ├── repository.py    # Protocol/ABC for data access
│   └── notifier.py      # Protocol/ABC for alerts
```

---

## Resolved (Ralph Wiggum Cleanup - 2026-01-09)

| Item | Resolution |
|------|------------|
| [DEBT-003](../_archive/debt/DEBT-003-loose-db-transactions.md) | Added `session.begin()` transaction boundaries across 7 files |
| [DEBT-002 Phase 1](../_archive/debt/DEBT-002-magic-numbers-analysis.md) | Added explanatory comments for platform constants (200.0, 1000, 1-99) |
| [DEBT-001](../_archive/debt/DEBT-001-api-client-typing.md) | Created Pydantic models for all portfolio methods |

---

## Resolved (2026-01-10)

| Item | Resolution |
|------|------------|
| [DEBT-006](../_archive/debt/DEBT-006-price-snapshot-insert-batching.md) | Avoid per-row flush/refresh; restore batching intent for snapshot ingestion |
| [DEBT-005](../_archive/debt/DEBT-005-price-snapshot-liquidity-dead-column.md) | Dropped dead `price_snapshots.liquidity` column and stopped writing it |

---

## Previously Resolved

| Item | Resolution |
|------|------------|
| Exa news collector datetime serialization (BUG-046) | Fixed Exa request serialization (`mode="json"`) and added unit/integration/e2e tests to cover the news pipeline |
| CLI skills drift for Exa/news commands (TODO-003) | Updated `.claude/skills/kalshi-cli/` references (CLI-REFERENCE/WORKFLOWS/GOTCHAS/DATABASE) to include Exa + news commands and gotchas |
| `KALSHI_RATE_TIER` and `--rate-tier` not wired | Wired env + CLI option into authenticated client construction (portfolio commands) |
| Path constants scattered across CLI | Centralized in `paths.py` |
| Mixed logging (stdlib vs structlog) | Standardized on structlog |
| Legacy sync client in codebase | Removed (BUG-045) |
| `cli.py` is 2,426 lines — needs splitting | Refactored into `cli/` module (SPEC-018) |

---

## Clean (No Action Needed)

| Check | Status |
|-------|--------|
| `# type: ignore` comments | None found |
| `TODO` / `FIXME` comments | None found |
| Bare `except:` clauses | None found |
| Untyped `Any` (excluding numpy/dict) | None found |
| Module docstrings | All present |
| `__init__.py` exports | All have explicit `__all__` |
| Print statements in library code | Only in `notebook_utils.py` (acceptable for Jupyter) |

---

## File Size Analysis

| File | Lines | Status |
|------|-------|--------|
| `api/client.py` | ~750 | Acceptable |
| `analysis/correlation.py` | 394 | Acceptable |
| `portfolio/syncer.py` | 355 | Acceptable |
| `data/fetcher.py` | 344 | Acceptable |

Files under 500 lines are generally fine per Clean Code guidelines.

---

## Non-Issues (Validated as Correct)

| Pattern | Why It's Fine |
|---------|---------------|
| API limits (1000, 200, 100) | Kalshi API constraints - immutable |
| Price validation (1-99) | Kalshi business rule - invariant |
| CLI defaults with `--override` | 12-factor app pattern |
| Retry parameters (30s, 5 retries) | Industry-standard defaults |

---

## Sources

- [Typer: One File Per Command](https://typer.tiangolo.com/tutorial/one-file-per-command/)
- [Typer: Subcommands and Modular CLI](https://pytutorial.com/python-typer-subcommands-and-modular-cli/)
