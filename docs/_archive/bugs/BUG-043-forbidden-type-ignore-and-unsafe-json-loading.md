# BUG-043: Forbidden `# type: ignore` + unsafe JSON persistence loading (P2)

**Priority:** P2 (Reliability + correctness; prevents silent data loss)
**Status:** 🟢 Fixed (2026-01-08)
**Found:** 2026-01-08
**Checklist Ref:** `code-audit-checklist.md` Sections 1 (Silent failures) + 2 (Type safety)

---

## Summary

The repo still contains `# type: ignore` directives (explicitly forbidden by `AGENTS.md`) and several JSON persistence
load paths that either:

- return unvalidated `Any` from `json.load`, or
- crash with an unhelpful stack trace on malformed JSON, or
- silently fall back to empty data structures (risking data loss on the next save).

---

## Evidence

### Forbidden `# type: ignore`

`rg -n "type: ignore" src tests` shows:

- `src/kalshi_research/data/repositories/prices.py` uses `# type: ignore[attr-defined]` for `.rowcount`.
- `src/kalshi_research/cli.py` uses `# type: ignore[no-any-return]` for `json.load(...)`.
- `tests/` includes `# type: ignore[...]` for patching/immutability tests.

### Unsafe JSON loading / silent fallbacks

- `src/kalshi_research/cli.py`: `_load_alerts()` and `_load_theses()` call `json.load()` without validating the
  loaded structure; malformed JSON yields a raw traceback.
- `src/kalshi_research/research/thesis.py`: `ThesisTracker._load()` has a broad fallback that can silently set
  `self.theses = {}` on unexpected formats. If the caller later saves, this can overwrite the on-disk file and
  destroy data.

---

## Root Cause

- Type checking was bypassed with `# type: ignore` instead of fixing types correctly.
- JSON persistence loaders trust disk contents too much (no schema checks, no friendly error handling).
- A “best effort” fallback in thesis loading hides failures instead of failing loudly.

---

## Ironclad Fix

- Remove all `# type: ignore` in `src/` and `tests/` by:
  - using proper SQLAlchemy result typing/casts for `.rowcount`,
  - validating JSON load results and returning typed dicts.
- Harden JSON persistence:
  - On malformed JSON or wrong schema: show a clear error and refuse to proceed (no silent empty fallback).
  - For `ThesisTracker`, raise a `ValueError` with path/context instead of silently resetting state.
- Add unit tests to lock in the behavior.

---

## Acceptance Criteria

- [x] `rg -n "type: ignore" src tests` returns no results.
- [x] Malformed `data/alerts.json` / `data/theses.json` produces a clear CLI error and exit code 1 (no traceback).
- [x] `ThesisTracker` never silently drops invalid storage content; it fails loudly without overwriting the file.
- [x] `uv run pre-commit run --all-files` passes.
