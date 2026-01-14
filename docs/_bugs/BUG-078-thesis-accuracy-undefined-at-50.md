# BUG-078: Thesis Accuracy Undefined at Exactly 50% Probability

**Status:** Open
**Priority:** P3 (Low - Edge Case)
**Created:** 2026-01-13
**Found by:** Deep Audit
**Effort:** ~15 min

---

## Summary

The `Thesis.was_correct` property returns incorrect results when `your_probability` is exactly 0.5. At this probability, the user has expressed no directional view, yet the code treats both YES and NO outcomes as "incorrect."

---

## Impact

- **Severity:** Low - Rare edge case
- **Financial Impact:** None (thesis tracking only)
- **User Impact:** Misleading accuracy metrics for 50% predictions

A thesis with `your_probability=0.5` is mathematically a "no-edge" position. The current code:
- Returns `False` if outcome is "yes" (because `0.5 > 0.5` is `False`)
- Returns `False` if outcome is "no" (because `0.5 < 0.5` is `False`)

This artificially penalizes accuracy metrics for neutral positions.

---

## Root Cause

At `src/kalshi_research/research/thesis.py:125-134`:

```python
@property
def was_correct(self) -> bool | None:
    """Did your thesis predict correctly?"""
    if self.actual_outcome is None:
        return None

    if self.actual_outcome == "yes":
        return self.your_probability > 0.5  # BUG: 0.5 returns False
    if self.actual_outcome == "no":
        return self.your_probability < 0.5  # BUG: 0.5 returns False
    return None
```

---

## Expected Behavior

When `your_probability == 0.5`:
- Return `None` (undefined) - no directional prediction was made
- OR return `True` for either outcome - a 50% prediction is "correct" by definition (calibrated)

Recommended: Return `None` to exclude from accuracy calculations.

---

## Fix

```python
@property
def was_correct(self) -> bool | None:
    """Did your thesis predict correctly?"""
    if self.actual_outcome is None:
        return None

    # No directional view at exactly 50% - exclude from accuracy
    if self.your_probability == 0.5:
        return None

    if self.actual_outcome == "yes":
        return self.your_probability > 0.5
    if self.actual_outcome == "no":
        return self.your_probability < 0.5
    return None
```

---

## Verification

```python
def test_thesis_was_correct_at_50_percent():
    thesis = Thesis(
        id="test",
        title="Test",
        market_tickers=["TEST"],
        your_probability=0.5,
        market_probability=0.5,
        confidence=0.5,
        bull_case="",
        bear_case="",
        key_assumptions=[],
        invalidation_criteria=[],
    )
    thesis.resolve("yes")
    assert thesis.was_correct is None  # Not True or False
```

---

## Related

- `performance_summary()` in `ThesisTracker` filters by `t.was_correct is not None`, so this fix will correctly exclude 50% predictions from accuracy calculations
