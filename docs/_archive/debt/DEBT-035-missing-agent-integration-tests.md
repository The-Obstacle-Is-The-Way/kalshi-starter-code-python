# DEBT-035: Missing Agent Integration Tests

**Status:** ✅ Resolved (Archived)
**Priority:** P2 (Medium)
**Created:** 2026-01-18
**Closed:** 2026-01-19
**Component:** `agent`, `cli`

---

## Summary

The agent CLI now has integration tests that exercise the end-to-end Typer command flow with mocked HTTP boundaries.

## Current Test Coverage

| Component | Unit Tests | Integration Tests |
|-----------|------------|-------------------|
| `orchestrator.py` | 7 tests | 0 |
| `research_agent.py` | 13 tests | 0 |
| `schemas.py` | 8 tests | 0 |
| `state.py` | 6 tests | 0 |
| `verify.py` | 11 tests | 0 |
| **CLI commands** | 0 | **1 file** (`tests/integration/cli/test_agent_commands.py`) |

## Problem

Resolved: integration tests now cover:

1. **Invoke the CLI** via Typer's test client
2. **Verify JSON output** matches schema
3. **Test error paths** (invalid ticker)
4. **Test flag combinations** (`--mode`, JSON default output)

## Notes

Further improvement (optional): add integration tests for `--human` output and for missing `EXA_API_KEY`, but this is not
required for a single-user research CLI.

## Acceptance Criteria

✅ Integration tests exist and run without real API keys.
