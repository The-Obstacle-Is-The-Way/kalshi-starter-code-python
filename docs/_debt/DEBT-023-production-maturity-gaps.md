# DEBT-023: Production Maturity Gaps (Senior Engineer Audit)

**Priority:** P3 (Research CLI is fine as-is; these matter for production service)
**Status:** Open (Reference Document)
**Created:** 2026-01-13
**Audit Type:** Senior software engineer code review

---

## Summary

This debt documents **production maturity gaps** identified during a rigorous senior-engineer-level audit. These are NOT bugs or broken functionality - they're gaps between "works as a research CLI" and "production-grade service."

**Important context:** This codebase is a **research tool for a solo trader**, not a multi-user service. Many of these gaps are intentionally deferred as YAGNI (You Ain't Gonna Need It).

---

## Overall Assessment: 7.5/10

The codebase is **NOT AI slop**. It demonstrates:
- Correct async patterns (no sync/async mixing antipatterns)
- Proper retry logic with exponential backoff (and `Retry-After` respect on read paths)
- Thoughtful error handling with custom exception hierarchy
- Well-structured tests at HTTP boundaries (not over-mocking)
- Frozen Pydantic models preventing mutation bugs
- Pre-commit hooks preventing syntax corruption (learned from incident)

---

## What's Done RIGHT (Senior-Quality Patterns)

| Pattern | Evidence |
|---------|----------|
| Async-first design | `httpx.AsyncClient`, `aiosqlite`, proper `async with` lifecycle |
| Repository pattern | Clean separation in `data/repositories/` |
| Frozen models | All API Pydantic models use `ConfigDict(frozen=True)` |
| Explicit error types | `KalshiAPIError`, `RateLimitError`, `AuthenticationError` hierarchy |
| Type hints throughout | Full PEP 604 union syntax, proper `TYPE_CHECKING` imports |
| Pre-commit hooks | Prevents syntax corruption before commits |
| Rate limiting | Token bucket + `Retry-After` integration on GET paths |
| Golden fixtures | SSOT pattern for API response validation |
| WAL mode + FK enforcement | SQLite configured correctly for integrity |

---

## Gaps Identified (Prioritized)

### P2: May Want Eventually

#### 1. No HTTP Connection Pool Configuration
**File:** `src/kalshi_research/api/client.py:82-86`
**Issue:** `httpx.AsyncClient` uses default pool settings. Under high-throughput sync (1000+ markets), may exhaust connections.
**Impact:** Latency spikes or socket errors under load.
**Fix:** Add `limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)`
**Effort:** 5 minutes

#### 2. No Circuit Breaker
**Files:** `api/client.py`, `exa/client.py`
**Issue:** If Kalshi/Exa API is down, every CLI command retries max_retries times before failing.
**Impact:** Slow, unhelpful error messages. In a service, would cascade to dependency exhaustion.
**Fix:** Add `circuitbreaker` or `tenacity` circuit breaker pattern.
**Effort:** 30 minutes

#### 3. SQLite Concurrency Documentation
**File:** `src/kalshi_research/data/database.py`
**Issue:** SQLite locks entire DB on write. Running concurrent `data sync-markets` commands will cause "database is locked" errors.
**Impact:** User confusion if they run parallel syncs.
**Fix:** Document in CLAUDE.md that sync commands must not run concurrently, OR implement file locking.
**Effort:** 15 minutes (doc) / 1 hour (file lock)

### P3: Production Service Only (Not Needed for CLI)

#### 4. No Metrics/Tracing
**Issue:** No counters, gauges, latency histograms. Structured logging exists but no distributed tracing.
**Impact:** Can't debug "the sync is slow" without metrics in production.
**Why P3:** For CLI, `--verbose` and logs are sufficient. Only needed if this becomes a service.

#### 5. Global Config Singleton
**File:** `src/kalshi_research/api/config.py:40`
**Issue:** `_config = APIConfig()` is mutable global state, not thread-safe.
**Impact:** Tests that set different environments can interfere.
**Why P3:** Fine for CLI. Would need fix if this becomes a library.

#### 6. No Request ID Tracing
**Issue:** When a CLI command makes multiple API calls, no way to correlate them.
**Impact:** Hard to debug in production logs.
**Why P3:** Not needed for single-user CLI.

---

## Agent Audit Corrections (False Positives)

The automated audit made some incorrect claims that I corrected:

| Claim | Reality |
|-------|---------|
| "No integration tests" | **FALSE** - `tests/integration/` has 12 `test_*.py` modules (plus `__init__.py`) covering API, data/DB, CLI, Exa, and news |
| "Exa cache has no expiration" | **FALSE** - `cache.py:64-67` expires entries, `clear_expired()` exists |
| "Inconsistent CLI error handling" | **PARTIAL** - Many commands use `typer.Exit(1)` for runtime errors and `Exit(2)` for usage errors, but some \"not found\" paths return success (e.g., `thesis show`, `alerts remove`) |
| "Rate limiter doesn't honor server feedback" | **PARTIAL** - `_wait_with_retry_after()` honors `Retry-After` for GET retries; write endpoints currently use exponential wait even when `Retry-After` is present |

---

## Recommendations

### If staying as research CLI: Do nothing.
The current implementation is appropriate for a single-user research tool.

### If evolving to production service:
1. **First:** Add connection pool limits (5 min)
2. **Second:** Document SQLite concurrency limitations (15 min)
3. **Later:** Add circuit breaker if experiencing API downtime issues
4. **Service-only:** Add metrics/tracing only if deploying as multi-user service

---

## Cross-References

| Item | Relationship |
|------|--------------|
| DEBT-018 | Test SSOT stabilization (separate scope) |
| DEBT-014 | Friction residuals (design decisions, separate) |
| CLAUDE.md | Should document SQLite concurrency if we don't implement locking |

---

## Audit Methodology

This audit was performed by:
1. Reading all core modules: `api/client.py`, `exa/client.py`, `data/database.py`, `data/fetcher.py`
2. Checking for common production antipatterns (circuit breakers, connection pools, metrics)
3. Verifying test coverage exists and is meaningful
4. Running unit test suite (`uv run pytest tests/unit`) (633 tests passed)
5. Cross-referencing agent findings with actual code

The verdict: **Production-grade for single-user CLI, with documented gaps for service evolution.**
