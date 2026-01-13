# DEBT-023: Production Maturity Gaps (Senior Engineer Audit)

**Priority:** P3 (Research CLI is fine as-is; these matter for production service)
**Status:** ✅ Resolved (Reference Document Only)
**Created:** 2026-01-13
**Resolved:** 2026-01-13
**Audit Type:** Senior software engineer code review

---

## Summary

This is a **reference document**, not a mandate to “productionize” the repo.

It captures **service-oriented patterns** that are common in production systems, and explains why most of them are
**intentionally out of scope** for this project today.

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

## Non-Goals (Avoid Cargo-Cult “Production Patterns”)

These are legitimate patterns in the right context, but implementing them here would be over-engineering.

| Pattern | Why it’s the wrong fit for this repo |
|---|---|
| Explicit httpx connection pool limits | `httpx.AsyncClient` already defaults to `Limits(max_connections=100, max_keepalive_connections=20)`; hardcoding the same values is a no-op. Only revisit if we add real concurrency and see pool-related errors. |
| Circuit breaker | This is a **CLI**, not a long-lived service. Most commands are one-shot; retry/backoff already provides the right UX (“try again briefly, then fail”). A circuit breaker adds state and complexity with little to no benefit here. |
| Prometheus / OpenTelemetry metrics & tracing | There is no metrics backend or dashboard for a solo CLI. Logs are the right tool; adding metrics packages would be complexity without an operational consumer. |
| Request ID correlation | For a single-process CLI, logs are already naturally ordered; correlation IDs are most useful for distributed or multi-worker systems. |
| Dependency injection for global config | The current global config pattern is appropriate for a CLI where we control the process lifecycle. DI only becomes important if the package becomes a broadly consumed library. |

This is what “best practices” means for this repo: **choose the right tool for the job**, not “implement every
enterprise pattern.”

## Legitimate, CLI-Scoped Improvements

These are "10/10" improvements that actually fit an internal research tool.

1. **Exit code correctness for missing identifiers** ✅ **FIXED (2026-01-13)**
   Commands that previously returned **success** when a requested resource didn't exist now return a non-zero
   exit code (`Exit(2)`), consistent with common Unix CLI expectations for "not found" errors:
   - `git show <missing>` → Exit 128 (error)
   - `rm <missing>` → Exit 1 (error), `rm -f <missing>` → Exit 0 (explicit flag)
   - Note: some tools (e.g. `kubectl`) vary by context and don't consistently distinguish "empty" vs "not found"
     via exit codes; prefer structured output parsing (`-o json`, inspect `.items`) where it matters.

   Fixed commands include:
   - Thesis + alerts: `alerts remove`, `thesis show`, `thesis resolve`, `thesis check-invalidation`
   - Portfolio: `portfolio link`
   - News: `news track`, `news untrack`
   - Market lookup: `market get` (and other ticker-based lookups)
   - Research: `research context` (when the market ticker doesn't exist)

   Exit code policy is now documented and complete:
   - `docs/_archive/debt/DEBT-024-cli-exit-code-policy.md`

2. **SQLite concurrency footnote (doc-only)** ✅ **FIXED (2026-01-13)**
   Added note to `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md`: "Avoid running two write-heavy commands simultaneously.
   SQLite locks the entire DB on write."

---

## Agent Audit Corrections (False Positives)

The automated audit made some incorrect claims that I corrected:

| Claim | Reality |
|-------|---------|
| "No integration tests" | **FALSE** - `tests/integration/` has 12 `test_*.py` modules (plus `__init__.py`) covering API, data/DB, CLI, Exa, and news |
| "Exa cache has no expiration" | **FALSE** - `cache.py:64-67` expires entries, `clear_expired()` exists |
| "Inconsistent CLI error handling" | **FIXED** - identifier-based "not found" paths return `Exit(2)`, and the repo exit code policy is documented in `docs/_archive/debt/DEBT-024-cli-exit-code-policy.md`. |
| "Rate limiter doesn't honor server feedback" | **PARTIAL** - `_wait_with_retry_after()` honors `Retry-After` for GET retries; write endpoints currently use exponential wait even when `Retry-After` is present |

---

## Recommendations

### For this repo (internal research CLI): keep it simple.
The current implementation is appropriate for a single-user research tool. Prefer correctness, tests, and clear UX over
production-service infrastructure.

### If this ever becomes a service:
Re-evaluate the “Non-Goals” section. Those patterns become relevant **only** when there’s a long-lived process,
multi-user concurrency, or operational ownership (dashboards, alerts, SLOs).

---

## Cross-References

| Item | Relationship |
|------|--------------|
| DEBT-018 | Test SSOT stabilization (separate scope) |
| DEBT-014 | Friction residuals (design decisions, separate) |
| CLAUDE.md / AGENTS.md / GEMINI.md | SQLite concurrency documented (see CLI-Scoped Improvements above) |

---

## Audit Methodology

This audit was performed by:
1. Reading all core modules: `api/client.py`, `exa/client.py`, `data/database.py`, `data/fetcher.py`
2. Checking for common production-service patterns (circuit breakers, connection pools, metrics)
3. Verifying test coverage exists and is meaningful
4. Running unit test suite (`uv run pytest tests/unit`)
5. Cross-referencing agent findings with actual code

The verdict: **Production-grade for single-user CLI, with documented gaps for service evolution.**
