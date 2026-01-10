# Deep Codebase Audit: Financial & Safety Risks

**Date:** 2026-01-10
**Status:** ✅ Fixed (P0/P1) • ⚠️ Deferred (P3)
**Severity:** Critical (P0)
**Last Verified:** 2026-01-10 (against current codebase)
**Fixed:** 2026-01-10 (all P0/P1 issues resolved; P2-6 reclassified; P3 deferred)

## Executive Summary

A deep, adversarial audit of the `kalshi-starter-code-python` codebase validated critical financial integrity risks and imminent breaking changes. The most urgent issues were the **Orderbook dollar-field migration** (Jan 15, 2026) and **systematic precision loss** in cost-basis averaging.

**Note:** Some issues from the original audit (BUG-049, BUG-050) have since been fixed. This document reflects the current verified state.

---

## Critical Findings (P0 - Immediate Action Required)

### 1. Imminent API Breakage: Orderbook Model (P0)

**Location:** `src/kalshi_research/api/models/orderbook.py:28-59`
**Verified:** 2026-01-10 - CONFIRMED

**Issue:**
The `Orderbook` model properties (`best_yes_bid`, `best_no_bid`, `midpoint`, `spread`) rely **exclusively** on the legacy `yes` and `no` fields (integer cents), which Kalshi is removing on Jan 15, 2026.

```python
# src/kalshi_research/api/models/orderbook.py:28-32
@property
def best_yes_bid(self) -> int | None:
    """Best YES bid price in cents."""
    if not self.yes:  # <--- Will be True when API removes 'yes' field
        return None   # <--- Returns None even if 'yes_dollars' is present
    return max(price for price, _ in self.yes)
```

The model DOES have `yes_dollars` and `no_dollars` fields defined (lines 24-25), but the computed properties DO NOT use them as fallback.

**Impact (pre-fix):**
On Jan 15, 2026, `best_yes_bid`, `best_no_bid`, `midpoint`, and `spread` would return `None`, causing downstream failures in scanner/liquidity logic.

**Recommendation:**
- Update `Orderbook` properties to check `yes_dollars` / `no_dollars` if `yes` / `no` are missing.
- Implement parsing logic to convert "0.50" string to 50 cents for backward compatibility.

---

### 2. Integer Precision Loss in Cost Basis (P0)

**Location:** `src/kalshi_research/portfolio/syncer.py:76`
**Verified:** 2026-01-10 - CONFIRMED

**Issue:**
The `compute_fifo_cost_basis` function calculates average cost using floor division (`//`):

```python
# src/kalshi_research/portfolio/syncer.py:76
return total_cost // total_qty
```

Combined with the `Position` model using `Integer` for `avg_price_cents`:

```python
# src/kalshi_research/portfolio/models.py:27
avg_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
```

**Scenario:**
1. Buy 1 contract @ 50c.
2. Buy 1 contract @ 51c.
3. Total Cost = 101c, Total Qty = 2.
4. Calculated Avg Price = `101 // 2` = **50c**.
5. Actual Avg Price = **50.5c**.

**Impact (pre-fix):**
Systematic downward bias in cost basis (floor division), which can compound into incorrect unrealized P&L.

**Recommendation:**
- Option A: Change `avg_price_cents` to `Float` or `Numeric` in the database schema
- Option B: Store in sub-cent precision (e.g., tenths of cents as integer)
- Use standard division `/` in `compute_fifo_cost_basis` and round appropriately

---

## Major Findings (P1 - Safety & Reliability)

### 3. Missing Safety in Order Modification (P1)

**Location:** `src/kalshi_research/api/client.py:710-805`
**Verified:** 2026-01-10 - CONFIRMED

**Issue:**
`create_order` supports `dry_run` (lines 620, 662-676), but `amend_order` and `cancel_order` do **not**.

```python
# create_order has dry_run: bool = False (line 620)
# amend_order has NO dry_run parameter (line 753)
# cancel_order has NO dry_run parameter (line 710)
```

**Impact:**
A trading strategy running in "dry run" mode could accidentally modify or cancel **live orders** if it calls these methods, violating the safety sandbox.

**Recommendation:**
- Add `dry_run: bool = False` to `amend_order` and `cancel_order`
- Wrap logic to log and skip API calls when `dry_run` is True
- Return mock responses matching expected schema

---

### 4. Cost Basis Dependence on Partial History (P1)

**Location:** `src/kalshi_research/portfolio/syncer.py:136-140`
**Verified:** 2026-01-10 - CONFIRMED

**Issue:**
`sync_positions` recalculates cost basis from *local* `Trade` records:

```python
# src/kalshi_research/portfolio/syncer.py:136-140
trades_result = await session.execute(
    select(Trade).where(Trade.ticker == ticker).order_by(Trade.executed_at)
)
trades = list(trades_result.scalars().all())
avg_price_cents = compute_fifo_cost_basis(trades, side)
```

If the local database is fresh (partial history) but the account has existing positions, the cost basis calculation will be incorrect (missing earlier trades). `compute_fifo_cost_basis` returns 0 when there are no trades.

**Status:**
Mitigated by:
- syncing trades before positions in `kalshi portfolio sync`
- warning on “cold start” (position exists but no local trades)

Kalshi’s positions payload does not provide a reliable avg-cost field, so a true “fallback” is not always possible; instead the system must detect/report unknown cost basis and avoid emitting misleading P&L.

---

## Moderate Findings (P2 - Functional Gaps)

### 5. Missing exc_info in syncer.py Exception Handler

**Location:** `src/kalshi_research/portfolio/syncer.py:353-358`
**Verified:** 2026-01-10 - CONFIRMED

**Issue:**
The `update_mark_prices` method catches exceptions but logs without `exc_info=True`:

```python
# src/kalshi_research/portfolio/syncer.py:353-358
except Exception as e:
    logger.warning(
        "Failed to fetch market data; skipping mark price update",
        ticker=pos.ticker,
        error=str(e),  # <-- Missing exc_info=True
    )
    continue
```

**Note:** The similar pattern in `cli/alerts.py:_compute_sentiment_shifts` (lines 120-126) has ALREADY been fixed with `exc_info=True`.

**Recommendation:**
- Add `exc_info=True` to the logger.warning call in syncer.py

---

### 6. Exa Subpage Controls (P2 - Reclassified)

**Location:** `src/kalshi_research/exa/models/search.py`
**Verified:** 2026-01-10 - CONFIRMED

**Clarification (SSOT):**
This was originally described as a `SearchRequest` schema gap. In the current codebase:
- `ContentsRequest` already models `subpages` and `subpageTarget` (shared across `/search`, `/findSimilar`, `/contents`)
- `SearchRequest` supports `contents: ContentsRequest`

The remaining limitation is ergonomic/API-surface: `ExaClient.search()` and `ExaClient.get_contents()` do not currently expose `subpages` / `subpage_target` in their function signatures, so callers can’t request subpages without constructing and passing a `ContentsRequest` directly.

**Resolution:**
Reclassified as a capability enhancement tracked by `docs/_specs/SPEC-030-exa-endpoint-strategy.md` (not a production bug).

---

## Minor Findings (P3 - Technical Debt)

### 7. Magic Numbers in Analysis (P3 - Technical Debt)

**Location:** `src/kalshi_research/analysis/scanner.py`
**Verified:** 2026-01-10 - PARTIALLY ADDRESSED

**Issue:** Hardcoded scaling factors in scoring logic:
- Line 258: `score = min(math.log10(m.volume_24h + 1) / 6, 1.0)` - The `6` is unexplained
- Line 309: `score = min(spread / 20, 1.0)` - The `20` is unexplained

Some magic numbers have been documented (e.g., lines 199-201 explain the `100.0` divisor for binary market math).

**Recommendation:**
- Extract remaining magic numbers to named constants
- Add brief inline comments explaining the scaling rationale

---

### 8. Potential Integer Overflow (Downgraded)

**Location:** Database Models
**Status:** Low risk for current stack

While `Integer` in SQLite/Python is safe (arbitrary/64-bit), strict SQL dialects might treat it as 32-bit. Given current stack (SQLite), this is low risk but worth noting for future migrations to PostgreSQL/MySQL.

---

## Issues Previously Fixed (Not Active)

The following issues from the original audit have been verified as FIXED:

| Original Claim | Status | Evidence |
|----------------|--------|----------|
| BUG-049: Rate limiting asymmetry | **FIXED** | `client.py:108,508` - reads now rate limited |
| BUG-050: Silent exception in alerts | **FIXED** | `alerts.py:124` - has `exc_info=True` |
| Silent exception in exa/client.py | **NOT FOUND** | No silent swallowing in code |

---

## Fix Status

| ID | Issue | Status | Fix Location |
|----|-------|--------|--------------|
| P0-1 | Orderbook dollar field fallback | ✅ FIXED | `api/models/orderbook.py:10-70` |
| P0-2 | Integer precision in cost basis | ✅ FIXED | `portfolio/syncer.py:76-80`, `portfolio/pnl.py:96-100` |
| P1-3 | dry_run for amend/cancel | ✅ FIXED | `api/client.py:710-812` |
| P1-4 | Cold start cost basis warning | ✅ FIXED | `portfolio/syncer.py:146-155` |
| P2-5 | exc_info in syncer.py | ✅ FIXED | `portfolio/syncer.py:373` |
| P2-6 | Exa subpage controls | ✅ RECLASSIFIED | Tracked via `SPEC-030` (enhancement) |
| P3-7 | Magic number constants | ⏳ DEFERRED | Low priority tech debt |

### Implementation Details

**P0-1: Orderbook Dollar Field Fallback**
- Added `_dollar_to_cents()` helper function
- Updated `best_yes_bid` and `best_no_bid` properties to fallback to `*_dollars` fields
- Tests added: `test_orderbook_dollar_fallback_*`

**P0-2: Integer Precision Fix**
- Changed `//` (floor division) to `round(total_cost / total_qty)` in `syncer.py`
- Also fixed in `pnl.py` FIFO partial lot consumption (found during post-fix audit)
- Uses banker's rounding (round half to even) for unbiased averaging
- Tests added: `test_compute_fifo_cost_basis_precision_loss_fixed`, `test_realized_fifo_partial_lot_no_floor_bias`

**P1-3: dry_run for Order Modification**
- Added `dry_run: bool = False` parameter to `cancel_order()` and `amend_order()`
- Returns simulated response when dry_run=True
- Logs validation without executing API call

**P1-4: Cold Start Detection**
- Added warning when position exists but no local trades found
- Warns user that cost basis will be inaccurate
- Recommends running `portfolio sync` or manual verification

**P2-5: Exception Logging**
- Added `exc_info=True` to `update_mark_prices` exception handler
- Full stack trace now logged for debugging
