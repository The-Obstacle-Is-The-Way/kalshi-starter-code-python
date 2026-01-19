# DEBT-035: Missing Agent Integration Tests

**Status:** Active
**Priority:** P2 (Medium - CLI commands untested end-to-end)
**Created:** 2026-01-18
**Component:** `agent`, `cli`

---

## Summary

The new agent CLI commands (`kalshi agent research`, `kalshi agent analyze`) have unit tests but **no integration tests** that verify the full CLI flow works correctly.

## Current Test Coverage

| Component | Unit Tests | Integration Tests |
|-----------|------------|-------------------|
| `orchestrator.py` | 7 tests | 0 |
| `research_agent.py` | 13 tests | 0 |
| `schemas.py` | 8 tests | 0 |
| `state.py` | 6 tests | 0 |
| `verify.py` | 11 tests | 0 |
| **CLI commands** | 0 | **0** |

## Problem

Unit tests mock the providers and test individual functions. But there are no tests that:

1. **Invoke the CLI** via Typer's test client
2. **Verify JSON output** matches schema
3. **Test error paths** (missing API keys, network failures)
4. **Test flag combinations** (`--json`, `--human`, `--mode`)

## Recommended Fix

Create `tests/integration/cli/test_agent_commands.py`:

```python
from typer.testing import CliRunner
from kalshi_research.cli.main import app

runner = CliRunner()

def test_agent_research_json_output():
    """Verify agent research returns valid JSON."""
    result = runner.invoke(app, ["agent", "research", "AAPL-25-JAN", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "summary_text" in data or "factors" in data

def test_agent_research_missing_ticker():
    """Verify helpful error for missing ticker."""
    result = runner.invoke(app, ["agent", "research"])
    assert result.exit_code != 0
    assert "TICKER" in result.stdout or "required" in result.stdout.lower()

def test_agent_analyze_warns_about_mock():
    """Verify JSON output includes mock warning."""
    result = runner.invoke(app, ["agent", "analyze", "AAPL-25-JAN", "--json"])
    # Should include warning in JSON until real LLM implemented
    # Or at minimum, exit 0 with valid structure
```

## Files to Create

- `tests/integration/cli/test_agent_commands.py`

## Acceptance Criteria

- [ ] Integration tests for `kalshi agent research` CLI
- [ ] Integration tests for `kalshi agent analyze` CLI
- [ ] Tests cover JSON output, human output, error cases
- [ ] Tests can run without real API keys (use mocks at HTTP boundary)
