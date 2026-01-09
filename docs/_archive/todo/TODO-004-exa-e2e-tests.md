# TODO-004: Add E2E Tests for Exa/News Pipeline

**Status:** Completed
**Priority:** High
**Created:** 2026-01-09
**Completed:** 2026-01-09
**Component:** `tests/e2e/`, `tests/integration/`

---

## Summary

The current test suite has a critical gap: **no E2E tests exercise the real Exa API integration for news collection**. This allowed BUG-046 (datetime serialization) to slip through because all news tests mock `NewsCollector` entirely.

---

## Current Test Coverage

### What Exists

| Test File | Type | Coverage |
|-----------|------|----------|
| `tests/unit/cli/test_news.py` | Unit | CLI layer only (mocks Exa/NewsCollector) |
| `tests/integration/test_exa_research.py` | Integration | `TopicResearcher` only (1 test) |

### What's Missing

1. **E2E test for news collection pipeline**
   - Track a market
   - Collect news via Exa
   - Verify articles stored in DB
   - Verify sentiment analysis runs

2. **Integration test for NewsCollector**
   - Tests `collector.py` with real Exa (or respx mock)
   - Exercises datetime serialization path

3. **E2E test for `research context` command**
   - Full CLI → Exa → output verification

4. **Integration test for Exa client datetime handling**
   - Specifically tests datetime fields serialize correctly

---

## Implementation

This gap is now covered by tests that mock **only the HTTP boundary** (respx), exercising the
real Exa client, request serialization, news collector, and DB writes:

- `tests/unit/exa/test_client.py::test_search_serializes_datetime_fields`
- `tests/integration/news/test_collector_integration.py::test_collect_for_tracked_market_inserts_articles_and_links`
- `tests/e2e/test_news_pipeline.py::test_news_track_then_collect_writes_articles_and_sentiment`

---

## Why This Matters

1. **BUG-046 was preventable** - A single E2E test hitting the real Exa API would have caught the datetime serialization bug immediately

2. **Specs marked "implemented" but non-functional** - SPEC-022 (Exa News Sentiment) is marked as implemented, but the end-to-end flow is broken

3. **False confidence from passing tests** - 9/9 news CLI tests pass, but they all mock the actual integration

---

## Acceptance Criteria

- [x] `tests/e2e/test_news_pipeline.py` exists and passes
- [x] Datetime serialization is tested (unit + integration)
- [x] BUG-046 is caught by these tests

---

## Related

- BUG-046: Datetime Serialization in News Collector
- SPEC-022: Exa News Sentiment Pipeline
- SPEC-020: Exa API Client
