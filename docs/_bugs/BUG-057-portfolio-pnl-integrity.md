# BUG-057: Portfolio P&L Integrity (FIFO Realized P&L + Unknown Handling)

**Priority:** P1 (High - financial reporting correctness)
**Status:** ⚠️ Partially Fixed (Regression: BUG-058)
**Found:** 2026-01-10
**Fixed:** 2026-01-10 (partial - see note below)
**Owner:** Platform

> **⚠️ REGRESSION NOTE:** The FIFO fix introduced BUG-058 - the algorithm crashes on incomplete trade history (orphan sells). See BUG-058, BUG-059, BUG-060, BUG-061 for the full fix chain.

---

## Summary

Portfolio P&L reporting currently contains two correctness issues:

1. **Unknown unrealized P&L is displayed as `$0.00`** in multiple CLIs when `Position.unrealized_pnl_cents` is `NULL` (unknown), because code uses `pos.unrealized_pnl_cents or 0`.
2. **Realized P&L is computed using average-cost floats (not FIFO) and truncation**, despite docstrings claiming FIFO. This can produce incorrect realized P&L totals and misleading win-rate statistics.

These are reporting-layer bugs (local DB/cache) but can directly mislead trading decisions and model evaluation.

---

## SSOT / First-Principles Validation

### Issue A: Unknown P&L Misrepresented as Zero

**Locations (SSOT):**
- `src/kalshi_research/cli/portfolio.py` (positions table totals)
- `src/kalshi_research/cli/research.py` (thesis show `--with-positions`)
- `src/kalshi_research/portfolio/pnl.py` (`calculate_total`, `calculate_summary_with_trades`)

**Why it is incorrect:**
- `unrealized_pnl_cents` can be legitimately `NULL` when mark prices are not fetched or when cost basis is unknown (cold start / incomplete history).
- Displaying `$0.00` is a silent lie. It should display as “unknown” and be excluded from totals, or totals should explicitly label “partial/known-only”.

### Issue B: Realized P&L Not FIFO + Float Truncation

**Locations (SSOT):**
- `src/kalshi_research/portfolio/pnl.py:calculate_realized`
- `src/kalshi_research/portfolio/pnl.py:_get_closed_trades`

**Why it is incorrect:**
- The code claims “FIFO” but uses average-cost math (`avg_cost = position_cost / position_qty`) with float arithmetic.
- It truncates via `int(...)`, producing systematic bias and non-cent-accurate results.
- If users rely on `kalshi portfolio pnl` as authoritative, this violates financial integrity.

---

## Impact

- Misleading dashboards: users may believe P&L is flat when it is simply unknown.
- Incorrect realized P&L totals and win-rate stats can bias strategy evaluation.
- Makes post-trade analysis and research calibration unreliable.

---

## Fix Plan

### 1) Treat `None` P&L as unknown everywhere

- Replace `pos.unrealized_pnl_cents or 0` with explicit handling:
  - Display `"-"` (or `"N/A"`) for unknown.
  - Exclude unknown values from totals.
  - Show an explicit “unknown count” when any unknown rows exist.

### 2) Implement FIFO realized P&L with integer arithmetic

- Build a FIFO lot matcher:
  - Group by `(ticker, side)`
  - For each BUY: enqueue `(qty, price_cents, fee_cents)`
  - For each SELL: consume lots FIFO and compute per-lot P&L in integer cents:
    - `pnl += (sell_price_cents - buy_price_cents) * qty_consumed`
    - subtract proportional fees when present
- Use the per-sell realized P&L list for:
  - `realized_pnl_cents = sum(pnls)`
  - win/loss counts
  - avg win/loss, profit factor

---

## Acceptance Criteria

- [x] `kalshi portfolio positions` displays `"-"` for unknown P&L and does not treat it as `$0.00`
- [x] Totals in `kalshi portfolio positions` exclude unknown rows and display an “unknown count” when present
- [x] `kalshi research thesis show --with-positions` displays `"-"` for unknown P&L
- [x] `kalshi portfolio pnl` realized P&L uses FIFO lots (no float arithmetic, no truncation bias)
- [x] Unit tests cover FIFO realized P&L (including partial sells) and unknown P&L display logic
- [x] `uv run pre-commit run --all-files` passes

---

## Test Plan

- Add unit tests for FIFO realized P&L in `tests/unit/portfolio/test_pnl.py`
- Add CLI unit tests for “unknown” display:
  - `tests/unit/cli/test_portfolio.py` (positions + thesis-linked display)
- Run:

```bash
uv run pytest -m "not integration and not slow"
```

---

## Fix Applied (SSOT)

- `src/kalshi_research/portfolio/pnl.py`: Implemented FIFO realized P&L with integer arithmetic; added `unrealized_positions_unknown` to `PnLSummary`.
- `src/kalshi_research/cli/portfolio.py`: Displays `"-"` for unknown unrealized P&L; totals exclude unknown rows and show an explicit count.
- `src/kalshi_research/cli/research.py`: Displays `"-"` for unknown thesis-linked position P&L.
- `tests/unit/portfolio/test_pnl.py`: Corrected price units to cents, added FIFO multi-lot test, strengthened assertions.
- `tests/unit/cli/test_portfolio.py`: Added regression test for unknown unrealized P&L display.

**Verification:**
- `uv run pre-commit run --all-files`
- `uv run mkdocs build --strict`
