# DEBT-043: SRP — Reduce “God Files” (≤400 LoC ceiling)

## Status

- **Severity:** CRITICAL
- **Effort:** L (multi-day, cross-cutting refactor)
- **Blocking:** Yes (future work keeps getting harder until this is addressed)
- **Target Date:** 2026-02-09
- **Status:** Active

## Problem

The repo has many **oversized source files** that violate Single Responsibility at a practical level:
they are difficult to review, hard to test in isolation, and guarantee future copy-paste and accidental coupling.

Clean Code standard for maintainability:
- If you can’t comfortably fit it in your head, it’s too big.

## Evidence

Reproduce:

```bash
find src/kalshi_research -name '*.py' -print0 | xargs -0 wc -l | sort -nr | head -n 25
find src/kalshi_research -name '*.py' -print0 | xargs -0 wc -l | sort -nr | awk '$1>400 {print}'
```

Current files > 400 lines (2026-01-21 audit, SSOT verified):

```text
554 src/kalshi_research/portfolio/pnl.py
483 src/kalshi_research/portfolio/syncer.py
461 src/kalshi_research/analysis/liquidity.py
448 src/kalshi_research/analysis/correlation.py
442 src/kalshi_research/exa/websets/client.py
439 src/kalshi_research/analysis/scanner.py
428 src/kalshi_research/api/models/portfolio.py
421 src/kalshi_research/research/thesis.py
418 src/kalshi_research/data/fetcher.py
```

Note: `cli/portfolio.py` (620 LoC) was split into `cli/portfolio/` package (D3, 2026-01-21).
Note: `cli/alerts.py` (521 LoC) was split into `cli/alerts/` package (D4, 2026-01-21).
Note: `agent/research_agent.py` (648 LoC) was split into `agent/research_agent/` package (D6, 2026-01-21).
Note: `agent/providers/llm.py` (471 LoC) was split into `agent/providers/llm/` package (D7, 2026-01-21).
Note: `execution/executor.py` (637 LoC) was split into `execution/` package (D8, 2026-01-21).
Note: `exa/client.py` (694 LoC) was split into `exa/` package with mixins (D9, 2026-01-21).

## Solution (Concrete, No Hand-Waving)

### Rule: No file > 400 lines

Adopt a strict size ceiling for `src/kalshi_research/**/*.py`:
- **Target:** ≤400 lines per file
- **Exception:** None (if a module is too big, it becomes a package)

### Refactor Strategy (by module family)

1. **CLI modules → packages by command group**
   - `src/kalshi_research/cli/research.py` → `src/kalshi_research/cli/research/` package (✅ done):
     - `__init__.py` registers Typer app
     - `context.py`, `topic.py`, `similar.py`, `deep.py`, `backtest.py`, `cache.py`
     - thesis commands live under `cli/research/thesis/`
   - `src/kalshi_research/cli/scan.py` → `src/kalshi_research/cli/scan/` package (✅ done):
     - `opportunities.py`, `arbitrage.py`, `movers.py`
     - shared helpers in `cli/scan/_helpers.py` and `cli/scan/_opportunities_helpers.py`

2. **API client → endpoint mixins (no surface-area break)**
   - Split `src/kalshi_research/api/client.py` into:
     - `src/kalshi_research/api/_base.py` (request plumbing + retries)
     - `src/kalshi_research/api/_mixins/*.py` (markets/events/series/exchange/multivariate/orders/order_groups/portfolio/trading)
   - Compose via multiple inheritance in `src/kalshi_research/api/client.py` (✅ done).

3. **Domain modules**
   - `execution/executor.py`, `portfolio/pnl.py`, `agent/research_agent.py` get split by responsibility:
     - executor: separate “live checks” from “order API operations” from “sizing”
     - pnl: split parsing/aggregation vs formatting/reporting
     - research_agent: split recovery vs polling vs plan execution

## Definition of Done (Objective)

- [ ] `find src/kalshi_research -name '*.py' -print0 | xargs -0 wc -l | awk '$1>400 {print}'` prints nothing (ignoring the final `total` line)
- [ ] All tests pass: `uv run pytest`
- [ ] All quality gates pass: `uv run pre-commit run --all-files`

## Acceptance Criteria (Phased)

- [x] Phase A: `cli/research.py` becomes `cli/research/` package (structure split)
- [x] Phase B: `cli/scan.py` becomes `cli/scan/` package (structure split)
- [x] Phase C: `api/client.py` split into endpoint modules; public import path preserved; all files ≤400 lines
- [ ] Phase D: Remaining >400-line modules reduced under the ceiling (tracked below; 16 files remain as of 2026-01-21)

Phase D sub-phases (one file-family per iteration):

- [x] Phase D1: `cli/market.py` becomes `cli/market/` package and all files ≤400 lines
- [x] Phase D2: `cli/data.py` becomes `cli/data/` package and all files ≤400 lines
- [x] Phase D3: `cli/portfolio.py` becomes `cli/portfolio/` package and all files ≤400 lines
- [x] Phase D4: `cli/alerts.py` becomes `cli/alerts/` package and all files ≤400 lines
- [x] Phase D5: `cli/research/thesis/_commands.py` reduced to ≤400 lines (split/move helpers as needed)
- [x] Phase D6: `agent/research_agent.py` split into focused modules and all files ≤400 lines
- [x] Phase D7: `agent/providers/llm.py` split into focused modules and all files ≤400 lines
- [x] Phase D8: `execution/executor.py` split into focused modules and all files ≤400 lines
- [x] Phase D9: `exa/client.py` split into focused modules and all files ≤400 lines
- [ ] Phase D10: `exa/websets/client.py` split into focused modules and all files ≤400 lines
- [ ] Phase D11: `portfolio/pnl.py` split into focused modules and all files ≤400 lines
- [ ] Phase D12: `portfolio/syncer.py` split into focused modules and all files ≤400 lines
- [ ] Phase D13: `analysis/liquidity.py` split into focused modules and all files ≤400 lines
- [ ] Phase D14: `analysis/scanner.py` split into focused modules and all files ≤400 lines
- [ ] Phase D15: `analysis/correlation.py` split into focused modules and all files ≤400 lines
- [ ] Phase D16: `api/models/portfolio.py` split into focused modules and all files ≤400 lines
- [ ] Phase D17: `research/thesis.py` split into focused modules and all files ≤400 lines
- [ ] Phase D18: `data/fetcher.py` split into focused modules and all files ≤400 lines

**Note (2026-01-21):** Phases A–C complete. Phase D in progress — 9 files still exceed 400 lines (see Evidence section for the current list). D1–D9 completed (cli/market.py, cli/data.py, cli/portfolio.py, cli/alerts.py, cli/research/thesis/_commands.py, agent/research_agent.py, agent/providers/llm.py, execution/executor.py, exa/client.py → packages).
