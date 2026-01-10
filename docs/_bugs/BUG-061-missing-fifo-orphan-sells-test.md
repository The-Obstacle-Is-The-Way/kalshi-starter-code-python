# BUG-061: Test Suite Missing Coverage for FIFO Edge Cases

**Priority:** P2 (Medium - test gap allowed BUG-058 regression)
**Status:** 🔴 Active
**Found:** 2026-01-10
**Fixed:** (pending)
**Owner:** Platform

---

## Summary

The test suite for `portfolio/pnl.py` lacks coverage for critical edge cases, which allowed BUG-057's "fix" to introduce BUG-058 (a regression). The FIFO implementation crashes on incomplete history, but no test catches this.

---

## Missing Test Cases

### 1. Orphan Sells (BUG-058 scenario)

**Not tested:** Sells without matching buys
```python
def test_realized_fifo_orphan_sells_graceful():
    """FIFO should handle sells without matching buys (incomplete history)."""
    trades = [
        # No buy trade - only a sell (orphan)
        _make_trade("yes", "sell", 10, 50),
    ]
    calculator = PnLCalculator()
    # Should NOT crash - should skip or return partial result
    result = calculator.calculate_realized(trades)
    assert result == 0  # Or whatever graceful behavior we implement
```

### 2. Cross-Side Closing

**Not tested:** Binary market cross-side semantics
```python
def test_realized_fifo_cross_side_closing():
    """Buying NO and selling YES should be recognized as a close."""
    trades = [
        _make_trade("no", "buy", 10, 40),   # Buy NO
        _make_trade("yes", "sell", 10, 60),  # Sell YES (closes NO economically)
    ]
    calculator = PnLCalculator()
    # What should happen? Currently crashes.
```

### 3. Settlement as Close

**Not tested:** Settlement closing a position
```python
def test_realized_fifo_with_settlement():
    """Settlement should close remaining position."""
    trades = [
        _make_trade("yes", "buy", 10, 40),
    ]
    settlement = Settlement(
        ticker="TEST",
        market_result="yes",
        yes_count=10,
        revenue=1000,  # Won 10 * 100¢
    )
    # Should compute realized P&L = 1000 - 400 = 600
```

### 4. Empty Trades with Non-Zero Positions

**Not tested:** Position exists but no local trades (cold start)
```python
def test_summary_with_positions_but_no_trades():
    """Positions with no trade history should use Kalshi's realized_pnl."""
    positions = [
        Position(
            ticker="TEST",
            quantity=10,
            realized_pnl_cents=500,  # From Kalshi API
        )
    ]
    trades = []  # No local trades
    calculator = PnLCalculator()
    summary = calculator.calculate_summary_with_trades(positions, trades)
    # Should use positions.realized_pnl_cents, not crash
    assert summary.realized_pnl_cents == 500
```

---

## Impact

1. **BUG-058 was a regression** - test suite didn't catch it
2. **False confidence** - BUG-057 marked "Fixed" but broke production
3. **Missing edge cases** - real-world data causes crashes

---

## Fix Plan

Add the following test cases to `tests/unit/portfolio/test_pnl.py`:

1. `test_realized_fifo_orphan_sells_graceful` - Incomplete history
2. `test_realized_fifo_cross_side_closing` - Binary market semantics
3. `test_summary_uses_position_realized_pnl` - Uses Kalshi's value
4. `test_summary_with_empty_trades_no_crash` - Graceful degradation

---

## Acceptance Criteria

- [ ] Test for orphan sells (incomplete history) added
- [ ] Test for cross-side closing added
- [ ] Test for using Kalshi's `realized_pnl` added
- [ ] Test for empty trades with positions added
- [ ] All new tests initially fail (TDD red)
- [ ] After fix, all tests pass (TDD green)
- [ ] `uv run pre-commit run --all-files` passes

---

## Test Plan

```bash
# Run new tests (should fail before fix)
uv run pytest tests/unit/portfolio/test_pnl.py -v -k "orphan or cross_side or empty"

# After fix, all should pass
uv run pytest tests/unit/portfolio/test_pnl.py -v
```

---

## References

- **Regression from:** BUG-057
- **Exposed by:** BUG-058
- **File:** `tests/unit/portfolio/test_pnl.py`
