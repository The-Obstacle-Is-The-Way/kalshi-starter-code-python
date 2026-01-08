# Technical Debt Register

**Last Audit:** 2026-01-08

---

## Outstanding Debt

### 1. `cli.py` is 2,426 lines — needs splitting

**Priority:** High
**Effort:** 2-4 hours
**Risk:** Low (pure refactor, no behavior change)

The official [Typer documentation](https://typer.tiangolo.com/tutorial/one-file-per-command/) recommends one file per command group. A 2,426-line file violates the Single Responsibility Principle.

**Current:**

```text
src/kalshi_research/
└── cli.py  # 2,426 lines
```

**Target:**

```text
src/kalshi_research/
├── cli/
│   ├── __init__.py      # Main app, adds sub-apps
│   ├── data.py          # kalshi data {init, sync-markets, collect, export, stats}
│   ├── market.py        # kalshi market {get, list, orderbook}
│   ├── scan.py          # kalshi scan {opportunities, arbitrage, movers}
│   ├── alerts.py        # kalshi alerts {list, add, remove, monitor}
│   ├── analysis.py      # kalshi analysis {calibration, correlation, metrics}
│   ├── research.py      # kalshi research {thesis, backtest}
│   └── portfolio.py     # kalshi portfolio {sync, positions, pnl, balance, history}
```

---

## Deferred (Low Priority)

### 2. No `interfaces/` or `ports/` package

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

## Resolved

| Item | Resolution |
|------|------------|
| Path constants scattered across CLI | Centralized in `paths.py` |
| Mixed logging (stdlib vs structlog) | Standardized on structlog |
| Legacy sync client in codebase | Removed (BUG-045) |

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
| `cli.py` | 2,426 | Needs splitting |
| `api/client.py` | 711 | Acceptable |
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
