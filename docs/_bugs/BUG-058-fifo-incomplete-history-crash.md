# BUG-058: FIFO P&L Crashes on Incomplete Trade History

**Priority:** P1 (High - blocks CLI usage)
**Status:** 🔴 Active
**Found:** 2026-01-10
**Fixed:** (pending)
**Owner:** Platform

---

## Summary

The FIFO realized P&L calculator (`pnl.py`) raises `ValueError` and crashes when trade history is incomplete—specifically when sell trades exist without matching buy trades. This is a **regression from BUG-057's FIFO fix**.

**Error:**
```
ValueError: Sell trade exceeds available FIFO lots; trade history is incomplete
```

**Repro:**
```bash
uv run kalshi portfolio pnl
```

---

## Root Cause

### 1. Strict FIFO Without Graceful Degradation

In `src/kalshi_research/portfolio/pnl.py:88-92`:

```python
if not lots:
    raise ValueError(
        "Sell trade exceeds available FIFO lots; trade history is "
        "incomplete"
    )
```

The algorithm expects **complete** trade history where every sell has a prior buy. Real-world scenarios where this fails:

- **API pagination limits**: Kalshi may not return full history
- **Cold start**: Positions opened before syncing began
- **Cross-side closing**: Selling YES to close a NO position (economically equivalent but algorithmically different)

### 2. Observed Data Pattern

```sql
-- From user's DB:
KXNCAAFSPREAD-26JAN09OREIND-IND3|no|buy|37|2026-01-08
KXNCAAFSPREAD-26JAN09OREIND-IND3|yes|sell|37|2026-01-10
```

- User bought **37 NO** contracts
- User sold **37 YES** contracts (closes the NO position economically)
- FIFO groups by `(ticker, side)`, so YES side has 0 buys and 37 sells → crash

---

## Impact

- `kalshi portfolio pnl` command is **completely broken** for users with any incomplete history
- Users cannot view P&L metrics at all
- Blocks core portfolio analysis workflow

---

## Fix Plan

### Option A: Graceful Degradation (Recommended)

When sells exceed available FIFO lots:
1. Skip those sells for realized P&L calculation
2. Track `orphan_sells_skipped` count
3. Warn user that realized P&L is approximate due to incomplete history
4. Never crash—always return *something* useful

```python
# Instead of raising:
if not lots:
    orphan_sells += trade.quantity
    continue  # Skip this sell
```

### Option B: Cross-Side Matching (Complex)

Recognize that in binary markets:
- Buying NO at price X ≈ Selling YES at (100 - X)
- Allow FIFO to match across YES/NO sides for the same ticker

This is semantically correct but adds complexity.

**Recommendation:** Start with Option A for immediate fix, consider Option B for v2.

---

## Acceptance Criteria

- [ ] `kalshi portfolio pnl` runs without crashing on incomplete history
- [ ] Realized P&L shows approximate value when history is incomplete
- [ ] Warning message displayed: "Realized P&L approximate (N orphan sells skipped)"
- [ ] `PnLSummary` includes `orphan_sells_skipped: int` field for transparency
- [ ] Unit test covers incomplete history edge case
- [ ] `uv run pre-commit run --all-files` passes

---

## Test Plan

1. Add test with orphan sells (sells without matching buys)
2. Verify no crash and reasonable output
3. Run on user's actual data: `uv run kalshi portfolio pnl`

```bash
uv run pytest tests/unit/portfolio/test_pnl.py -v
uv run kalshi portfolio pnl
```

---

## References

- **Regression from:** BUG-057 (FIFO implementation)
- **File:** `src/kalshi_research/portfolio/pnl.py:88-92`
- **CLI:** `src/kalshi_research/cli/portfolio.py:325`
