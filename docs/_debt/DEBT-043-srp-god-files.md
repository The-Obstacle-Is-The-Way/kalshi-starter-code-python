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
788 src/kalshi_research/cli/market.py
736 src/kalshi_research/cli/data.py
694 src/kalshi_research/exa/client.py
648 src/kalshi_research/agent/research_agent.py
637 src/kalshi_research/execution/executor.py
620 src/kalshi_research/cli/portfolio.py
554 src/kalshi_research/portfolio/pnl.py
521 src/kalshi_research/cli/alerts.py
483 src/kalshi_research/portfolio/syncer.py
471 src/kalshi_research/agent/providers/llm.py
461 src/kalshi_research/analysis/liquidity.py
448 src/kalshi_research/analysis/correlation.py
442 src/kalshi_research/exa/websets/client.py
439 src/kalshi_research/analysis/scanner.py
428 src/kalshi_research/api/models/portfolio.py
421 src/kalshi_research/research/thesis.py
418 src/kalshi_research/data/fetcher.py
404 src/kalshi_research/cli/research/thesis/_commands.py
```

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

- [x] Phase A: `cli/research.py` becomes `cli/research/` package and all files ≤400 lines
- [x] Phase B: `cli/scan.py` becomes `cli/scan/` package and all files ≤400 lines
- [x] Phase C: `api/client.py` split into endpoint modules; public import path preserved; all files ≤400 lines
- [ ] Phase D: Remaining >400-line modules reduced under the ceiling (18 files remain as of 2026-01-21)

**Note (2026-01-21):** Phases A–C complete. Phase D remains — 18 files still exceed 400 lines (see Evidence section for the current list).
