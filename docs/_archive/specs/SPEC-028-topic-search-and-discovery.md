# SPEC-028: Topic Search & Market Discovery (DB + CLI)

**Status:** ✅ Implemented
**Priority:** P1 (Core UX / Research Loop)
**Created:** 2026-01-10
**Owner:** Solo
**Effort:** ~1–2 days

---

## Summary

Add fast, local “topic search” and filtering over markets/events using SQLite (FTS5) + a small, explicit CLI
surface.

This spec exists because:

- Kalshi’s `GET /markets` endpoint does **not** support keyword search; it supports only structured filters (SSOT:
  `../_vendor-docs/kalshi-api-reference.md`).
- The current CLI has **no keyword search** and users must use raw `sqlite3 ... LIKE '%foo%'` queries (SSOT:
  `.codex/skills/kalshi-cli/SKILL.md`).
- We already persist markets/events/snapshots in SQLite; we should leverage that database as the canonical
  “discovery index” for humans and for future automation.

---

## Goals

1. **Fast keyword search** across markets and events (sub-100ms on a warm cache for typical queries).
2. **Simple filters** that match how humans think:
   - status (`open`, `closed`, etc.)
   - category (via `markets.category` which stores denormalized `events.category`)
   - time windows (close/settle)
   - “quality” filters (min volume, max spread) via latest snapshot join
3. **Deterministic, testable behavior** (no LLM dependence).
4. **A CLI that doesn’t lie**: no invented flags; everything is implemented and backed by DB queries.

---

## Non-Goals

- No “AI topic modeling” or clustering.
- No RAG/embeddings/vector DB.
- No changes to the scanner algorithm itself (that’s SPEC-031).
- No “live API keyword search” (Kalshi doesn’t provide it; we won’t simulate it by fetching all markets unless
  explicitly requested by the user).

---

## Current State (SSOT)

### 1) CLI has no keyword search

- `uv run kalshi market list` hits the API and supports structured filters like `--status`, `--event`,
  `--event-prefix`, `--category`, `--exclude-category`, `--limit`, `--full`
  (SSOT: `src/kalshi_research/cli/market.py`).
- The `kalshi-cli` skill explicitly warns: “NO `--search` option exists” (SSOT: `.codex/skills/kalshi-cli/SKILL.md`).

### 2) Database has markets/events but no search index

- Tables: `events`, `markets`, `price_snapshots`, … (SSOT: `src/kalshi_research/data/models.py`).
- `markets.category` is populated during `data sync-markets` by denormalizing `events.category` onto markets when
  missing (SSOT: `src/kalshi_research/data/fetcher.py`).
- `markets.subcategory` exists but is currently unused (still `NULL`).
- Market responses (as represented by our `Market` API model) do not include market-level `category` fields, so
  we treat `events.category` (and its denormalized copy in `markets.category`) as the canonical category.

### 3) Price filters require joining latest snapshots

- `markets` is reference data; `price_snapshots` stores evolving prices and volume (SSOT:
  `.codex/skills/kalshi-cli/DATABASE.md`).

---

## Design

### 1) Add SQLite FTS5 indexes (virtual tables)

We add two virtual tables:

- `market_fts` for market keyword search (title/subtitle).
- `event_fts` for event keyword search (title/category).

We **do not** attempt to full-text-index snapshots; snapshots are joined via “latest snapshot per ticker”.

#### 1.1 `market_fts`

**Source table:** `markets`

**Indexed columns:**
- `title`
- `subtitle`

**Stored (UNINDEXED) columns (for fast joins / display without re-querying):**
- `ticker`
- `event_ticker`
- `series_ticker`

**DDL (contentful, trigger-maintained)**

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS market_fts USING fts5(
  ticker UNINDEXED,
  title,
  subtitle,
  event_ticker UNINDEXED,
  series_ticker UNINDEXED
);
```

**Triggers**

```sql
CREATE TRIGGER IF NOT EXISTS market_fts_ai
AFTER INSERT ON markets BEGIN
  INSERT INTO market_fts(ticker, title, subtitle, event_ticker, series_ticker)
  VALUES (new.ticker, new.title, new.subtitle, new.event_ticker, new.series_ticker);
END;

CREATE TRIGGER IF NOT EXISTS market_fts_ad
AFTER DELETE ON markets BEGIN
  DELETE FROM market_fts WHERE ticker = old.ticker;
END;

CREATE TRIGGER IF NOT EXISTS market_fts_au
AFTER UPDATE ON markets BEGIN
  DELETE FROM market_fts WHERE ticker = old.ticker;
  INSERT INTO market_fts(ticker, title, subtitle, event_ticker, series_ticker)
  VALUES (new.ticker, new.title, new.subtitle, new.event_ticker, new.series_ticker);
END;
```

#### 1.2 `event_fts`

**Source table:** `events`

**Indexed columns:**
- `title`
- `category` (tokenized; supports searching “elections”, “crypto”, etc.)

**Stored columns (UNINDEXED):**
- `ticker`
- `series_ticker`

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS event_fts USING fts5(
  ticker UNINDEXED,
  title,
  category,
  series_ticker UNINDEXED
);
```

**Triggers**

```sql
CREATE TRIGGER IF NOT EXISTS event_fts_ai
AFTER INSERT ON events BEGIN
  INSERT INTO event_fts(ticker, title, category, series_ticker)
  VALUES (new.ticker, new.title, new.category, new.series_ticker);
END;

CREATE TRIGGER IF NOT EXISTS event_fts_ad
AFTER DELETE ON events BEGIN
  DELETE FROM event_fts WHERE ticker = old.ticker;
END;

CREATE TRIGGER IF NOT EXISTS event_fts_au
AFTER UPDATE ON events BEGIN
  DELETE FROM event_fts WHERE ticker = old.ticker;
  INSERT INTO event_fts(ticker, title, category, series_ticker)
  VALUES (new.ticker, new.title, new.category, new.series_ticker);
END;
```

#### 1.3 Availability: FTS5 compile option

We must assume some environments may not include FTS5.

Implementation requirement:
- On startup (or first use), detect FTS5 availability.
- If unavailable, fall back to `LIKE` search (slower, but correct).

**FTS5 check**

```sql
SELECT 1
FROM pragma_compile_options
WHERE compile_options = 'ENABLE_FTS5';
```

---

### 2) Add a “latest snapshot” view/query helper

Many filters (min volume, max spread) require joining current-ish price information.

We standardize one query pattern in code (repository helper) and optionally materialize it as a SQLite view.

**Query pattern**

```sql
WITH latest AS (
  SELECT ticker, MAX(snapshot_time) AS max_time
  FROM price_snapshots
  GROUP BY ticker
)
SELECT
  m.ticker,
  m.title,
  m.status,
  e.category AS event_category,
  p.yes_bid,
  p.yes_ask,
  p.volume_24h
FROM markets m
JOIN events e ON e.ticker = m.event_ticker
LEFT JOIN latest l ON l.ticker = m.ticker
LEFT JOIN price_snapshots p
  ON p.ticker = m.ticker
 AND p.snapshot_time = l.max_time;
```

---

### 3) Add “Saved Topics” (optional but recommended)

“Topic” here means a **saved search preset** (FTS query + structured filters), not an AI-inferred latent
topic.

#### 3.1 Schema

Add a new table:

- `topics`
  - `id` (INTEGER PK)
  - `name` (TEXT UNIQUE, human-friendly key)
  - `description` (TEXT NULL)
  - `fts_query` (TEXT) — e.g. `"bitcoin OR btc"`, `"cpi inflation"`
  - `filters_json` (TEXT) — JSON for structured filters (status/category/min_volume/max_spread/etc.)
  - `created_at`, `updated_at`

This is intentionally small and doesn’t attempt to store “topic membership” rows; membership is computed by
running the query.

#### 3.2 Topic execution contract

Running a topic returns the same results as the underlying search command, with a stable JSON shape for
programmatic use (future automation).

---

## CLI Surface (Proposed)

### 1) `kalshi market search`

Search markets in the local DB using FTS (or fallback to LIKE).

**Command**

```bash
uv run kalshi market search "bitcoin ETF" --db data/kalshi.db --status open --category crypto --top 50
```

**Options (proposed)**

- `--db PATH` (default: `data/kalshi.db`)
- `--status unopened|open|paused|closed|settled|any` (default: `open`)
- `--category TEXT` (matches `markets.category` / denormalized `events.category`, case-insensitive)
- `--event TICKER` (exact `event_ticker`)
- `--series TICKER` (exact `series_ticker`)
- `--min-volume INT` (uses latest snapshot `volume_24h`)
- `--max-spread INT` (uses latest snapshot `yes_ask - yes_bid`)
- `--top INT` (default: 20)
- `--format table|json` (default: table)

**Output**

- Table: ticker, title, event category, status, probability (mid), spread, volume_24h
- JSON: list of objects with the same fields (plus timestamps)

### 2) `kalshi market topics` (Phase 2)

**Commands**

```bash
uv run kalshi market topics create "crypto" --query "bitcoin OR btc OR ethereum" --category crypto
uv run kalshi market topics list
uv run kalshi market topics run "crypto" --top 50 --format json
uv run kalshi market topics delete "crypto"
```

---

## Implementation Plan

### Phase 1 (Deliver search)

1. Add DB bootstrap that ensures virtual tables + triggers exist:
   - Create on `kalshi data init` and also lazily on `kalshi market search` if missing.
2. Add a `SearchRepository` (or add methods to `MarketRepository`) for:
   - `search_markets(query, filters...)`
   - `search_events(query, filters...)` (optional)
3. Add `kalshi market search` CLI command.
4. Add unit tests:
   - FTS path (skip if FTS5 not available)
   - LIKE fallback path

### Phase 2 (Saved topics)

1. Add `Topic` ORM model + repository.
2. Add `kalshi market topics ...` commands.
3. Add tests for topic CRUD and topic execution.

---

## Acceptance Criteria

- [x] Keyword searching works via CLI without requiring raw SQL.
- [x] Filtering by denormalized event categories (`markets.category`) is supported (and documented).
- [x] Search returns stable JSON when requested.
- [x] If FTS5 is unavailable, commands still work via LIKE fallback (with a warning).
- [x] `uv run mkdocs build --strict` passes after docs updates that accompany implementation.

---

## Risks & Mitigations

- **FTS5 not available:** Detect and fall back to LIKE.
- **Triggers drift / partial index:** Provide a `kalshi data reindex-search` command that rebuilds FTS from source
  tables (delete and repopulate) when needed.
- **User expects API-fresh results:** Clearly document that search operates on the local DB; users should run
  `kalshi data sync-markets` (and optionally `kalshi data snapshot`) before searching.
