# BUG-058: FIFO P&L Crashes on Incomplete Trade History

**Priority:** P1 (High - blocks CLI usage)
**Status:** ✅ Fixed
**Found:** 2026-01-10
**Fixed:** 2026-01-10
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

**Old behavior (pre-fix):** `_get_closed_trade_pnls_fifo` raised when a sell could not be matched to any FIFO lots.

```python
if not lots:
    raise ValueError("Sell trade exceeds available FIFO lots; trade history is incomplete")
```

The algorithm expects **complete** trade history where every sell has a prior buy. Real-world scenarios where this fails:

- **API pagination limits**: Kalshi may not return full history
- **Cold start**: Positions opened before syncing began
- **Side mismatches / incomplete local history**: Local DB can contain sells without corresponding buys for that side

### 2. Observed Data Pattern

```sql
-- From user's DB:
KXNCAAFSPREAD-26JAN09OREIND-IND3|no|buy|37|2026-01-08
KXNCAAFSPREAD-26JAN09OREIND-IND3|yes|sell|37|2026-01-10
```

- User bought **37 NO** contracts
- User later had **37 YES sells** recorded with no matching YES buys in local history
- FIFO groups by `(ticker, side)`, so the YES side had 0 buys and 37 sells → crash

---

## Impact

- `kalshi portfolio pnl` command is **completely broken** for users with any incomplete history
- Users cannot view P&L metrics at all
- Blocks core portfolio analysis workflow

---

## Fix Plan

### Option A: Graceful Degradation (Implemented)

When sells exceed available FIFO lots:
1. Skip those sells for realized P&L calculation
2. Track `orphan_sells_skipped` count
3. Warn user that trade stats are partial due to incomplete history
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

- [x] `kalshi portfolio pnl` runs without crashing on incomplete history
- [x] Unmatched sells are skipped and counted (no exception)
- [x] `PnLSummary` includes `orphan_sells_skipped: int` for transparency
- [x] CLI surfaces `orphan_sells_skipped` and notes trade stats are partial
- [x] Unit test covers incomplete history edge case
- [x] `uv run pre-commit run --all-files` passes

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

## API Research (2026-01-10)

### Official Kalshi Docs Findings

Source: [Get Fills - API Documentation](https://docs.kalshi.com/api-reference/portfolio/get-fills)

| Question | Answer |
|----------|--------|
| Data retention limits? | **NOT DOCUMENTED** - unknown how far back fills go |
| `side` field semantics? | Literal side ("yes"/"no"), NOT effective position |
| `purchased_side` field? | **NOT IN DOCS** - may be undocumented or removed |
| Max pagination limit? | 200 per page (we use 100) |
| Cross-side closing? | **NOT DOCUMENTED** - no guidance provided |

### Implications

1. **We cannot assume complete history** - Kalshi may truncate old fills
2. **`side` is literal** - Selling YES shows `side=yes` even when closing NO position
3. **Cross-side matching is our problem** - Kalshi doesn't help us here
4. **Option A (graceful degradation) is correct approach** - we must handle incomplete data

### Missing Endpoint: `/portfolio/settlements`

**Critical finding:** We sync `/portfolio/fills` but NOT `/portfolio/settlements`.

When a market settles:
1. Position auto-closes via settlement (not a regular sell)
2. This appears in `/portfolio/settlements`, NOT `/portfolio/fills`
3. We never fetch it → FIFO sees orphan buys with no matching "close"

**Settlement response fields (from official docs):**

| Field | Type | Description |
|-------|------|-------------|
| `ticker` | string | Market that settled |
| `market_result` | enum | `yes`, `no`, `scalar`, or `void` |
| `yes_count` | int | YES contracts held at settlement |
| `no_count` | int | NO contracts held at settlement |
| `yes_total_cost` | int | Cost basis of YES contracts (cents) |
| `no_total_cost` | int | Cost basis of NO contracts (cents) |
| `revenue` | int | Payout (100¢ per winning contract) |
| `settled_time` | string | ISO timestamp |
| `fee_cost` | string | Fees in dollars |

### Critical Finding: Kalshi Provides `realized_pnl`!

**We don't need to compute total realized P&L ourselves.**

From `/portfolio/positions` response:
- `realized_pnl` - Locked-in profit/loss in cents
- `realized_pnl_dollars` - Same in dollars

Kalshi computes this correctly including settlements. We should USE this value for totals, not compute our own.

### Robust Fix Strategy

| What | Source | Notes |
|------|--------|-------|
| **Total Realized P&L** | positions + settlements | Use Kalshi's `realized_pnl` and add `/portfolio/settlements` P&L |
| **Per-Trade/Outcome Stats** | fills + settlements | FIFO on fills, plus settlement P&L as an additional “closed outcome” |
| **Unrealized P&L** | positions + mark prices | Open position value |

Implementation note: we do **not** synthesize fake fills for settlements. Settlement P&L is computed directly from
`revenue - yes_total_cost - no_total_cost - fee_cost`.

### Safety Features from Create Order Spec

Relevant for future TODO-008 (agent safety rails):

| Field | Use Case |
|-------|----------|
| `reduce_only` | Ensures order only reduces position, never increases |
| `cancel_order_on_pause` | Auto-cancels if trading paused |
| `buy_max_cost` | Max spend in cents, enables Fill-or-Kill |

---

## References

- **Regression from:** BUG-057 (FIFO implementation)
- **File:** `src/kalshi_research/portfolio/pnl.py`
- **CLI:** `src/kalshi_research/cli/portfolio.py`
- **Kalshi Docs:** https://docs.kalshi.com/api-reference/portfolio/get-fills
