# BUG-050: Silent Exception Swallowing in Alerts Sentiment Computation

**Priority**: Medium (P2)
**Status**: Active
**Created**: 2026-01-09

## Symptom

When the `alerts monitor` command computes sentiment shifts, any database or aggregation error is silently swallowed and returns an empty dictionary, making it appear as if no sentiment data exists rather than indicating a failure.

## Location

**File**: `src/kalshi_research/cli/alerts.py:117`

```python
async def _compute_sentiment_shifts(
    tickers: set[str],
    *,
    db_path: Path,
) -> dict[str, float]:
    from kalshi_research.data import DatabaseManager
    from kalshi_research.news import SentimentAggregator

    shifts: dict[str, float] = {}
    try:
        async with DatabaseManager(db_path) as db:
            aggregator = SentimentAggregator(db)
            for ticker in tickers:
                summary = await aggregator.get_market_summary(ticker, days=7, compare_previous=True)
                if summary and summary.score_change is not None:
                    shifts[ticker] = summary.score_change
    except Exception:  # <-- SILENT FAILURE
        return {}      # <-- Looks like "no data" instead of error
    return shifts
```

## Root Cause

The function catches all exceptions and returns an empty dictionary without:
1. Logging the exception
2. Distinguishing between "no sentiment data" and "error fetching data"
3. Notifying the caller that an error occurred

## Impact

- **Silent failures mask bugs**: Database connection issues, schema mismatches, or code errors go undetected
- **User confusion**: User sees no sentiment alerts but doesn't know if it's "no data" or "broken feature"
- **Debugging difficulty**: Without logging, troubleshooting requires code inspection

## Proposed Fix

Replace silent exception with logged warning and distinguishable return:

```python
async def _compute_sentiment_shifts(
    tickers: set[str],
    *,
    db_path: Path,
) -> dict[str, float]:
    from kalshi_research.data import DatabaseManager
    from kalshi_research.news import SentimentAggregator

    shifts: dict[str, float] = {}
    try:
        async with DatabaseManager(db_path) as db:
            aggregator = SentimentAggregator(db)
            for ticker in tickers:
                summary = await aggregator.get_market_summary(ticker, days=7, compare_previous=True)
                if summary and summary.score_change is not None:
                    shifts[ticker] = summary.score_change
    except Exception as e:
        logger.warning(
            "Failed to compute sentiment shifts; sentiment alerts will be skipped",
            error=str(e),
            exc_info=True,
        )
        return {}  # Graceful degradation, but now logged
    return shifts
```

## Acceptance Criteria

- [ ] Exception is logged with `logger.warning()` or `logger.exception()`
- [ ] Error message explains impact (sentiment alerts skipped)
- [ ] No traceback visible to user (logged at DEBUG level if needed)

## Related Files

- `src/kalshi_research/cli/alerts.py`
- `src/kalshi_research/news/aggregator.py`

## References

- [Code Audit Checklist](../_debt/code-audit-checklist.md) - See section "1. Silent Failures & Exception Swallowing"
