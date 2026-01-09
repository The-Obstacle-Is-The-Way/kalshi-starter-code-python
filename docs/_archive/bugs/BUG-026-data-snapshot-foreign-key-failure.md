# BUG-026: `kalshi data snapshot` FOREIGN KEY constraint failure (P0)

**Priority:** P0 (Blocks core data pipeline)
**Status:** 🟢 Fixed (2026-01-07)
**Found:** 2026-01-07
**Spec:** SPEC-003-data-layer-storage.md, SPEC-010-cli-completeness.md
**Checklist Ref:** code-audit-checklist.md Section 15 (Silent Fallbacks)

---

## Summary

`kalshi data snapshot` crashes while inserting `price_snapshots` with:

- `sqlite3.IntegrityError: FOREIGN KEY constraint failed`

This prevents collecting any price history, which blocks analytics (metrics/correlation/calibration) and most of
the "data pipeline" workflows.

---

## Reproduction

1. `uv run kalshi data init --db /tmp/kalshi_audit.db`
2. `uv run kalshi data sync-markets --db /tmp/kalshi_audit.db --status open`
3. `uv run kalshi data snapshot --db /tmp/kalshi_audit.db --status open`

Observed failure (example ticker):

- `KXMVESPORTSMULTIGAMEEXTENDED-S2025473C9CD2E9A-30C474D2C9D`

Evidence:

- DB missing market row: `sqlite3 /tmp/kalshi_audit.db "select count(*) from markets where ticker='…';"` → `0`
- API market exists: `uv run kalshi market get KXMVESPORTSMULTIGAMEEXTENDED-S2025473C9CD2E9A-30C474D2C9D`

---

## Root Cause

- `price_snapshots.ticker` enforces a foreign key to `markets.ticker`.
- `DataFetcher.take_snapshot()` inserts snapshots for tickers returned by the live `/markets` API, but does not
  upsert the corresponding `markets` rows first.
- `kalshi data sync-markets` can be incomplete due to pagination caps (see BUG-027), so the snapshot fetch can
  encounter tickers not present in `markets`, triggering FK failure.

**Best Practice Violation:** [SQLite FK Best Practices](https://sqlite.org/foreignkeys.html) — Always insert parent
records before child records. UPSERT does not handle FK violations, only uniqueness constraints.

---

## Impact

- `kalshi data snapshot` unusable.
- `kalshi data collect` (continuous or `--once`) becomes unreliable.
- Downstream analysis commands relying on snapshots cannot function.

---

## Ironclad Fix Specification

**Approach:** Upsert minimal `Market` row before inserting snapshot (same pattern used in `sync_markets` lines 162-170).

**File:** `src/kalshi_research/data/fetcher.py`

**Change `take_snapshot()` method (lines 186-216):**

```python
async def take_snapshot(self, status: str | None = "open") -> int:
    """
    Take a price snapshot of all markets.

    Args:
        status: Optional filter for market status (default: open)

    Returns:
        Number of snapshots taken
    """
    snapshot_time = datetime.now(UTC)
    logger.info("Taking price snapshot at %s", snapshot_time.isoformat())
    count = 0

    async with self._db.session_factory() as session:
        price_repo = PriceRepository(session)
        market_repo = MarketRepository(session)  # ADD: Market repo for upsert
        event_repo = EventRepository(session)    # ADD: Event repo for FK

        async for api_market in self.client.get_all_markets(status=status):
            # ADD: Ensure market row exists (same pattern as sync_markets)
            existing_market = await market_repo.get(api_market.ticker)
            if existing_market is None:
                # Ensure event exists first
                existing_event = await event_repo.get(api_market.event_ticker)
                if existing_event is None:
                    event = DBEvent(
                        ticker=api_market.event_ticker,
                        series_ticker=api_market.series_ticker or api_market.event_ticker,
                        title=api_market.event_ticker,  # Placeholder
                    )
                    await event_repo.add(event)

                db_market = self._api_market_to_db(api_market)
                await market_repo.upsert(db_market)

            snapshot = self._api_market_to_snapshot(api_market, snapshot_time)
            await price_repo.add(snapshot)
            count += 1

            # Commit in batches
            if count % 100 == 0:
                await session.commit()
                logger.debug("Took %d snapshots so far", count)

        await session.commit()

    logger.info("Took %d price snapshots", count)
    return count
```

**Key Changes:**
1. Import `MarketRepository` and `EventRepository` in snapshot method
2. Check if market exists before inserting snapshot
3. If not, create minimal market/event records (same pattern as `sync_markets`)
4. This ensures FK constraint is always satisfied

---

## Acceptance Criteria

- [x] `uv run kalshi data snapshot --db <new_db>` completes without integrity errors (manual smoke + integration CLI test)
- [x] `uv run kalshi data collect --once --db <new_db>` completes and reports non-zero snapshots (manual smoke + integration CLI test)
- [x] `uv run kalshi analysis metrics <ticker> --db <new_db>` finds latest snapshot (manual smoke)
- [x] Unit test: `tests/unit/data/test_fetcher.py::test_take_snapshot_creates_missing_market_and_event`
- [x] DB-level regression: fresh SQLite DB → snapshot insert → no FK errors (covered by the unit test above)

---

## Test Plan

```python
async def test_take_snapshot_creates_missing_market(tmp_db: DatabaseManager) -> None:
    """Snapshot should auto-create market row if missing (FK robustness)."""
    async with DataFetcher(tmp_db) as fetcher:
        # Don't call sync_markets first - start with empty DB
        count = await fetcher.take_snapshot(status="open")

    assert count > 0

    # Verify market rows were created
    async with tmp_db.session_factory() as session:
        market_repo = MarketRepository(session)
        markets = await market_repo.count()
        assert markets > 0
```
