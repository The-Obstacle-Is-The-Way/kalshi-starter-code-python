# BUG-074: Deprecated Cent Fields “Direct Usage” (False Positive)

**Priority:** P4 (Closed - incorrect risk assessment)
**Status:** ✅ Closed (False Positive)
**Found:** 2026-01-12
**Closed:** 2026-01-12

---

## Summary

This bug report originally claimed that direct usage of cent fields (`yes_bid`, `yes_ask`, etc.) would break after the
Jan 15, 2026 deprecation. That assessment was **incorrect** for the cited code paths.

---

## What We Verified (SSOT = Code)

### 1) Database snapshots are stored as integer cents intentionally

The cited usages (e.g., `PriceSnapshot.yes_bid`) are **database columns**, not raw API fields.

- `src/kalshi_research/data/models.py` defines `PriceSnapshot.yes_bid` / `yes_ask` as non-null integer columns.
- These are internal storage fields that remain present regardless of upstream API deprecations.

### 2) Snapshot ingestion already uses dollar-safe computed properties

`src/kalshi_research/data/fetcher.py` populates snapshots via:

- `api_market.yes_bid_cents`, `api_market.yes_ask_cents`, `api_market.no_bid_cents`, `api_market.no_ask_cents`

Those computed properties prefer `*_dollars` fields and fall back to legacy cent fields, so snapshot ingestion remains
forward-compatible with the Jan 15, 2026 API change.

### 3) Market cent fields are already optional in the API model

In `src/kalshi_research/api/models/market.py`, legacy cent fields like `yes_bid` are already declared as optional and
are not used directly by downstream code (except as fallbacks inside the computed properties).

---

## Outcome

No code changes required for the originally cited lines. The real “Jan 15 risk” is handled at ingestion time (and is
already implemented correctly).

If we later decide to migrate the database to store dollar fields instead of cents, that would be a separate (explicit)
schema+query change and should be tracked as technical debt, not as a Jan 15 deprecation bug.
