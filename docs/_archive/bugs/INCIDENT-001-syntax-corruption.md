# INCIDENT-001: Chinese Character Syntax Corruption

**Date:** 2026-01-07
**Severity:** Critical
**Status:** Resolved

## Summary

A commit (`6abe504`) introduced corrupted Python syntax that broke the entire codebase. The import statement `from tenacity import` was corrupted to `from tenacity时不时 (` - Chinese characters (`时不时` means "from time to time") replaced the ` import ` keyword.

## Root Cause Analysis

### What Happened

1. Commit `6abe504` ("Refactor API Client and WebSocket Code for Improved Readability and Consistency") was created without running quality gates
2. The commit contained corrupted syntax in `src/kalshi_research/api/client.py` line 10
3. The corruption was: `from tenacity时不时 (AsyncRetrying,` instead of `from tenacity import (AsyncRetrying,`

### Why It Happened

1. **Pre-commit hooks were NOT installed** - `.git/hooks/pre-commit` did not exist
2. **No Python syntax validation** - The original pre-commit config lacked `check-ast` hook
3. **Quality gates were bypassed** - Either via `git commit --no-verify` or manual commit without running checks
4. **Possible encoding issue** - The Chinese characters suggest copy-paste from a document with mixed encoding, or an AI agent that had encoding issues in its output

### Why It Wasn't Caught

1. Pre-commit hooks weren't installed (must run `uv run pre-commit install`)
2. The `check-ast` hook (Python syntax validation) was missing from config
3. No CI check blocked the merge

## Impact

- All Python imports failed with `SyntaxError`
- 363+ lint errors cascaded from the corruption
- Development was blocked until fixed

## Resolution

1. **Identified clean commit**: `99a2ab9` was the last clean commit
2. **Restored client.py**: From clean commit
3. **Recovered missing features**: Manually extracted trading methods from corrupted commit `6abe504`
4. **Fixed all type errors**: Properly typed WebSocket client and API client
5. **Updated pre-commit config**: Added `check-ast` hook (CRITICAL)
6. **Installed pre-commit hooks**: `uv run pre-commit install`
7. **Updated documentation**: CLAUDE.md, AGENTS.md, GEMINI.md now require pre-commit

## Prevention Measures Implemented

### Pre-commit Configuration (`.pre-commit-config.yaml`)

```yaml
# CRITICAL: check-ast validates Python syntax
- id: check-ast
  name: "Validate Python syntax (AST)"
```

### Documentation Updates

All agent files (CLAUDE.md, AGENTS.md, GEMINI.md) now include:

```bash
# MANDATORY Before ANY Commit
uv run pre-commit install        # ONCE after clone
uv run pre-commit run --all-files  # ALWAYS before commit
```

### FORBIDDEN Patterns

- `git commit --no-verify` - NEVER bypass hooks
- `# type: ignore` - Fix type errors properly
- Manual commits without running pre-commit

## Verification Checklist

- [x] Pre-commit hooks installed
- [x] `check-ast` hook validates Python syntax
- [x] All 425 tests pass
- [x] All mypy type checks pass
- [x] All ruff lint/format checks pass
- [x] Documentation updated

## Lessons Learned

1. **Always install pre-commit hooks immediately after cloning**
2. **The `check-ast` hook is essential** - It catches syntax corruption before commit
3. **Never bypass quality gates** - Even for "simple" refactoring commits
4. **Git archaeology is valuable** - Finding clean commits via `git log` and `git show` saved the day
5. **AI agents can introduce encoding issues** - Verify all code before committing
