# BUG-046: Datetime Serialization Error in News Collector

**Status:** Resolved
**Priority:** High
**Discovered:** 2026-01-09
**Resolved:** 2026-01-09
**Component:** `news/collector.py`, `exa/client.py`

---

## Symptom

When running `kalshi news collect`, the following error occurs:

```
Failed to collect news for query error='Object of type datetime is not JSON serializable'
```

## Root Cause

The `NewsCollector.collect_for_tracked_item()` method passes a `datetime` object to `exa.search_and_contents()`:

```python
# collector.py:70-81
cutoff = datetime.now(UTC) - timedelta(days=self._lookback_days)
response = await self._exa.search_and_contents(
    query,
    ...
    start_published_date=cutoff,  # datetime object
)
```

The Exa client's `_request()` method calls `request.model_dump(by_alias=True, exclude_none=True)`, which returns a dict with a raw `datetime` object. When `httpx` tries to serialize this to JSON for the request body, it fails because Python's `json.dumps()` can't handle `datetime` objects.

## Location

- `src/kalshi_research/news/collector.py:81`
- `src/kalshi_research/exa/client.py:282`

## Fix

Option A: Use Pydantic's `model_dump_json()` then parse back (wasteful)
Option B: Add `mode="json"` to `model_dump()` for ISO8601 serialization (preferred)

```python
# In exa/client.py, change:
json_body=request.model_dump(by_alias=True, exclude_none=True)

# To:
json_body=request.model_dump(by_alias=True, exclude_none=True, mode="json")
```

`mode="json"` tells Pydantic to serialize datetime as ISO8601 strings.

## Verification

```bash
uv run kalshi news track SOME-TICKER -q "test query"
uv run kalshi news collect  # Should not error
```

## Impact

- Without this fix, news collection fails when `start_published_date` is used.

## Regression Tests

- `tests/unit/exa/test_client.py::test_search_serializes_datetime_fields`
- `tests/integration/news/test_collector_integration.py::test_collect_for_tracked_market_inserts_articles_and_links`
- `tests/e2e/test_news_pipeline.py::test_news_track_then_collect_writes_articles_and_sentiment`
