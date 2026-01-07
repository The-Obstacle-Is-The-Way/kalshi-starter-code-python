# BUG-007: CI/CD Test Failures

**Priority:** P1
**Status:** Open
**Discovered:** 2026-01-06
**Spec Reference:** SPEC-001 (CI/CD)

---

## Summary

GitHub Actions CI is failing for test jobs on all Python versions (3.11, 3.12, 3.13, 3.14), despite tests passing locally. Lint & Type Check passes successfully.

## Current Behavior

```
CI / Lint & Type Check (push)     ✓ Successful
CI / Test (Python 3.11) (push)    ✗ Failing
CI / Test (Python 3.12) (push)    ✗ Failing
CI / Test (Python 3.13) (push)    ✗ Failing
CI / Test (Python 3.14) (push)    ✗ Failing
CI / Integration Tests (push)     ⊘ Skipped (depends on Test)
```

## Local Behavior

```bash
$ uv run pytest tests/unit -v
============================= 185 passed in 13.17s =============================
```

All 185 tests pass locally on Python 3.11+.

## Potential Causes

### 1. Python 3.14 Compatibility (HIGH PROBABILITY)

Python 3.14 is **not officially released** - it's in alpha/beta stage. Some dependencies may not support it:
- `cryptography` - often slow to support new Python versions
- `aiosqlite` - async SQLite may have compatibility issues
- `sqlalchemy` - complex C extensions

### 2. Missing pytest-asyncio Configuration

The CI runs `pytest tests/unit` with coverage. asyncio mode configuration may differ:

```toml
# pyproject.toml should have:
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### 3. Coverage Import Error

CI runs with `--cov=kalshi_research` which requires the package to be importable. If there's an import error on a specific Python version, coverage fails.

### 4. Dependency Version Conflicts

`uv sync --dev` in CI may resolve different versions than local due to:
- Ubuntu vs macOS platform differences
- Different Python interpreter implementations

## Investigation Steps

1. Check CI logs for actual error messages
2. Test locally with Python 3.14:
   ```bash
   uv python install 3.14
   uv sync --dev --python 3.14
   uv run pytest tests/unit
   ```
3. Run with coverage locally to replicate CI:
   ```bash
   uv run pytest tests/unit --cov=kalshi_research --cov-report=term-missing
   ```

## Recommended Fix

### Primary Recommendation: Remove Python 3.14

Since Python 3.14 is pre-release/alpha, it should not be part of the blocking CI matrix.

```yaml
# .github/workflows/ci.yml
matrix:
  python-version: ["3.11", "3.12", "3.13"]  # Removed "3.14"
```

### Alternative: Experimental Allow-Fail

If testing against 3.14 is desired for forward compatibility:

```yaml
matrix:
  python-version: ["3.11", "3.12", "3.13", "3.14"]
  include:
    - python-version: "3.14"
      experimental: true
continue-on-error: ${{ matrix.experimental == true }}
```

## Acceptance Criteria

- [ ] CI passes on Python 3.11, 3.12, 3.13
- [ ] Python 3.14 either removed or marked experimental
- [ ] All 185 tests pass in CI
- [ ] Coverage report uploads successfully
- [ ] Integration tests run on main branch pushes

## Notes

This bug may be intermittent or environment-specific. Need CI logs to confirm root cause.
