# Deep Codebase Audit: Financial & Safety Risks

**Date:** 2026-01-10
**Status:** Open
**Severity:** Critical (P0)

## Executive Summary

A deep audit of the `kalshi-starter-code-python` codebase has revealed significant financial integrity risks, specifically regarding P&L calculation precision and order management safety. While the architecture is generally sound, specific implementation details in the `portfolio` and `api` modules pose risks of incorrect financial reporting and accidental execution of "dry run" strategies.

## Critical Findings (P0 - Immediate Action Required)

### 1. Integer Precision Loss in Cost Basis (P0)

**Location:** `src/kalshi_research/portfolio/models.py`, `src/kalshi_research/portfolio/syncer.py`

**Issue:**
The `Position` model stores `avg_price_cents` as an `Integer`. The `compute_fifo_cost_basis` function calculates the average using integer division (`//`).

```python
# src/kalshi_research/portfolio/syncer.py
return total_cost // total_qty
```

**Scenario:**
1. Buy 1 contract @ 50¢.
2. Buy 1 contract @ 51¢.
3. Total Cost = 101¢, Total Qty = 2.
4. Calculated Avg Price = `101 // 2` = **50¢**.
5. Actual Avg Price = **50.5¢**.

**Impact:**
This causes permanent, cumulative errors in P&L tracking. In the scenario above, the system under-reports the cost basis by 0.5¢ per share. If the user sells both at 51¢, the system reports a profit of (51 - 50) * 2 = 2¢, whereas the real profit is (51 - 50.5) * 2 = 1¢. This is a **100% error** in realized P&L for this trade.

**Recommendation:**
*   Change `avg_price_cents` to `Float` or `Numeric` in the database.
*   Use `total_cost / total_qty` (float division) in calculations.
*   Alternatively, store `avg_price_micro_cents` (cents * 10000) if integer arithmetic is preferred.

---

### 2. Missing Safety in Order Modification (P1)

**Location:** `src/kalshi_research/api/client.py`

**Issue:**
While `create_order` includes a `dry_run` parameter for safety, `amend_order` and `cancel_order` **do not**.

**Impact:**
A trading strategy running in "dry run" mode (simulating trades) might attempt to amend or cancel an order. If the logic calls `client.amend_order(...)` believing it is safe/mocked, it will **modify a real live order** if the ID matches. This breaks the safety guarantee of the "dry run" concept.

**Recommendation:**
*   Add `dry_run: bool = False` to `amend_order` and `cancel_order`.
*   If `dry_run` is True, log the action and return a mock response without calling the API.

---

### 3. Cost Basis Dependence on Partial History (P1)

**Location:** `src/kalshi_research/portfolio/syncer.py`

**Issue:**
The `sync_positions` method recalculates cost basis by querying *all local trades*:
```python
select(Trade).where(Trade.ticker == ticker).order_by(Trade.executed_at)
```
It assumes the local `trades` table contains the **entire** trading history.

**Impact:**
If a user initializes the database today (`sync_trades` fetches recent history), but has relevant open positions from last year, the `trades` table will be incomplete. The FIFO calculation will either:
1. Return 0 (if no buys found).
2. Calculate a wrong average based only on recent buys.
This results in wildly incorrect P&L data for existing portfolios.

**Recommendation:**
*   Implement a "Cold Start" checks: If `Position` exists on API but no `Trade` history explains it, flag it or require a full history sync.
*   Allow fetching `avg_price` directly from Kalshi API as a fallback (if available) or manual entry for legacy positions.

## Major Findings (P2 - Reliability)

### 4. Silent Failures & Swallowed Exceptions

**Locations:**
*   `src/kalshi_research/portfolio/syncer.py`: `update_mark_prices` catches `Exception` and logs warning, continuing loop. If the API is down, this spams logs but doesn't alert the caller that pricing is stale.
*   `src/kalshi_research/exa/cache.py`: Catching `Exception` (line 75, 140).
*   `src/kalshi_research/exa/client.py`: Catching `Exception` (line 214).

**Impact:**
Critical subsystems (pricing, research) can fail silently, leaving the application in a degraded state without the user knowing.

**Recommendation:**
*   Refine exception handling to catch specific errors.
*   Propagate critical errors up to the orchestrator/CLI.

## Minor Findings (P3 - Technical Debt)

### 5. Magic Numbers in Analysis

**Location:** `src/kalshi_research/analysis/scanner.py`

**Issue:**
Scoring logic contains hardcoded scaling factors:
*   `math.log10(m.volume_24h + 1) / 6`
*   `min(spread / 20, 1.0)`

**Recommendation:**
Extract these into named constants or configuration to clarify their derivation (e.g., `MAX_SCOREable_VOLUME_LOG`, `MAX_SCOREABLE_SPREAD`).
