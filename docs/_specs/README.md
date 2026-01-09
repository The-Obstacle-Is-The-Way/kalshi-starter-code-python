# Specifications (Active Implementation)

This directory contains **active** design specifications - work happening NOW.

## Distinction from `_future/`

| Directory | Purpose | When to Use |
|-----------|---------|-------------|
| `_specs/` | **Active implementation** | Work happening NOW |
| `_future/` | **Backlog** | Blocked, deferred, or planned later |

---

## Current Active Specs

| ID | Title | Priority | Status |
|---|---|---|---|
| **SPEC-026** | [Liquidity Analysis](SPEC-026-liquidity-analysis.md) | P1 | Ready to implement |

### SPEC-026: Liquidity Analysis

Comprehensive liquidity analysis framework for Kalshi markets.

**Why now:**
- Kalshi deprecated `liquidity` field (Jan 15, 2026)
- `liquidity_dollars` is insufficient for position sizing
- Directly improves trading quality
- Prevents "trapped position" scenarios

**Deliverables:**
- `src/kalshi_research/analysis/liquidity.py` - Core metrics
- `kalshi market liquidity TICKER` - CLI command
- Composite 0-100 liquidity score with grades

**Estimated effort:** ~4-5 hours

---

## Next ID Tracker

Use this ID for the next specification:
**SPEC-027**

---

## Workflow

1. **New spec**: Create `SPEC-XXX-description.md` here
2. **Future work**: Move to `_future/` if deprioritized
3. **Implemented**: Move to `_archive/specs/`

---

## Archive (Implemented)

Completed specifications are stored in [`docs/_archive/specs/`](../_archive/specs/).

| ID | Title | Status |
|---|---|---|
| SPEC-025 | Market Open Time Display | ✅ Implemented |
| SPEC-023 | Exa-Thesis Integration | ✅ Implemented |
| SPEC-022 | Exa News & Sentiment Pipeline | ✅ Implemented |
| SPEC-021 | Exa-Powered Market Research | ✅ Implemented |
| SPEC-020 | Exa API Client Foundation | ✅ Implemented |
| SPEC-001 to SPEC-019 | Foundation specs | ✅ Implemented |
