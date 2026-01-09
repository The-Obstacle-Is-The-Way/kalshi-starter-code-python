# TODO-010: Implement Liquidity Analysis Framework

**Priority**: High (Trading Quality)
**Status**: Active
**Created**: 2026-01-09
**Spec**: [SPEC-026: Liquidity Analysis](../_specs/SPEC-026-liquidity-analysis.md)

---

## Overview

Implement the liquidity analysis framework defined in SPEC-026. This is critical because:

1. Kalshi deprecated the `liquidity` field (Jan 15, 2026)
2. `liquidity_dollars` is a simple aggregate - not useful for position sizing
3. Without proper analysis, edge can be eaten by slippage

## Why Now?

- SPEC-026 is fully researched and designed
- All dependencies are in place (orderbook API, Market model)
- Directly improves trading quality
- Prevents "trapped position" scenarios

## Scope

### Phase 1: Core Metrics (Must Have)

Create `src/kalshi_research/analysis/liquidity.py`:

- [ ] `DepthAnalysis` dataclass
- [ ] `SlippageEstimate` dataclass
- [ ] `LiquidityAnalysis` dataclass
- [ ] `LiquidityGrade` enum (ILLIQUID, THIN, MODERATE, LIQUID)
- [ ] `orderbook_depth_score()` - weighted depth calculation
- [ ] `estimate_slippage()` - walk-the-book simulation
- [ ] `liquidity_score()` - composite 0-100 score
- [ ] `max_safe_order_size()` - binary search for safe size

### Phase 2: CLI Integration (Must Have)

- [ ] `kalshi market liquidity TICKER` command
- [ ] Rich table output with all metrics
- [ ] Order size analysis table (10/50/100/500 contracts)
- [ ] Warnings display

### Phase 3: Scanner Integration (Nice to Have)

- [ ] `--min-liquidity N` filter for scan commands
- [ ] `--show-liquidity` column option

### Phase 4: Future (Out of Scope)

- Historical liquidity tracking
- WebSocket real-time monitoring
- Pre-trade slippage enforcement

## Acceptance Criteria

- [ ] Core liquidity metrics implemented with tests
- [ ] CLI command `kalshi market liquidity` works
- [ ] Composite score grades markets correctly
- [ ] Max safe size calculation is accurate
- [ ] Quality gates pass (ruff, mypy, pytest)

## Estimated Effort

- Phase 1: 2-3 hours (core implementation)
- Phase 2: 1-2 hours (CLI integration)
- Total: ~4-5 hours

## Related Files

- `src/kalshi_research/api/models/orderbook.py` - Orderbook model
- `src/kalshi_research/analysis/edge.py` - Edge detection (uses spread)
- `src/kalshi_research/analysis/scanner.py` - Market scanner
- `docs/_specs/SPEC-026-liquidity-analysis.md` - Full specification
