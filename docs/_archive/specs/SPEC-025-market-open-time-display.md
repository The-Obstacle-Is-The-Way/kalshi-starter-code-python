# SPEC-025: Market Open Time Display in CLI

**Status:** 📋 Planned
**Priority:** P1 (Research critical - prevents temporal validation errors)
**Estimated Complexity:** Low
**Dependencies:** None
**Related:** TODO-005

---

## 1. Overview

Add `open_time` and `created_time` display to `market get` CLI command to enable temporal validation during research workflows.

### 1.1 Problem Statement

The CLI currently only shows `close_time` for markets. This led to a **catastrophic research failure** where a recommendation was made based on an event that occurred BEFORE the market opened:

- **Market**: "Will a new Stranger Things episode release before Jan 1, 2027?"
- **Market opened**: Jan 5, 2026
- **Stranger Things S5 released**: Nov-Dec 2025 (BEFORE market opened)
- **Flawed conclusion**: "Easy YES, it already released"
- **Reality**: S5 doesn't count because it predates the market

### 1.2 Goals

- Display `open_time` in `market get` output
- Display `created_time` in `market get` output
- Enable agents and users to perform temporal validation

### 1.3 Non-Goals

- Automated temporal validation in research commands (future work)
- Historical open_time tracking
- API changes (data already available)

---

## 2. Technical Specification

### 2.1 Current Output

```
$ uv run kalshi market get KXMEDIARELEASEST-27JAN01
┌───────────────┬──────────────────────────────────────────────────────────────┐
│ Ticker        │ KXMEDIARELEASEST-27JAN01                                     │
│ Title         │ Will A New Episode of Stranger Things be released...        │
│ Status        │ active                                                       │
│ Close Time    │ 2027-01-01T04:59:00+00:00                                    │
│ Yes Bid/Ask   │ 12 / 14                                                      │
│ ...           │ ...                                                          │
└───────────────┴──────────────────────────────────────────────────────────────┘
```

### 2.2 Desired Output

```
$ uv run kalshi market get KXMEDIARELEASEST-27JAN01
┌───────────────┬──────────────────────────────────────────────────────────────┐
│ Ticker        │ KXMEDIARELEASEST-27JAN01                                     │
│ Title         │ Will A New Episode of Stranger Things be released...        │
│ Status        │ active                                                       │
│ Open Time     │ 2026-01-05T20:00:00+00:00                                    │
│ Created Time  │ 2026-01-05T17:50:26+00:00                                    │
│ Close Time    │ 2027-01-01T04:59:00+00:00                                    │
│ Yes Bid/Ask   │ 12 / 14                                                      │
│ ...           │ ...                                                          │
└───────────────┴──────────────────────────────────────────────────────────────┘
```

### 2.3 Implementation Location

**File**: `src/kalshi_research/cli/market.py`

The `market get` command renders market details using Rich tables. Add rows for:
- `open_time` (from API `open_time` field)
- `created_time` (from API `created_time` field)

### 2.4 API Data Availability

The Kalshi API already returns these fields in the market object:

```json
{
  "ticker": "KXMEDIARELEASEST-27JAN01",
  "title": "Will A New Episode of Stranger Things...",
  "created_time": "2026-01-05T17:50:26Z",
  "open_time": "2026-01-05T20:00:00Z",
  "close_time": "2027-01-01T04:59:00Z",
  "expiration_time": "2027-01-01T04:59:00Z",
  "status": "active",
  ...
}
```

**No API changes required** - the data is already available.

---

## 3. Testing Strategy

### 3.1 Unit Tests

```python
# tests/unit/cli/test_market_display.py

import pytest
from typer.testing import CliRunner
from kalshi_research.cli.main import app

runner = CliRunner()


class TestMarketGetDisplay:
    """Test market get command output formatting."""

    @pytest.fixture
    def mock_market_response(self):
        """Sample market data with open_time."""
        return {
            "ticker": "TEST-MKT-01",
            "title": "Test Market",
            "status": "active",
            "open_time": "2026-01-05T20:00:00Z",
            "created_time": "2026-01-05T17:50:26Z",
            "close_time": "2027-01-01T04:59:00Z",
            "yes_bid": 45,
            "yes_ask": 47,
        }

    def test_market_get_shows_open_time(
        self, mock_market_response, mocker
    ) -> None:
        """market get displays open_time field."""
        mocker.patch(
            "kalshi_research.cli.market.fetch_market",
            return_value=mock_market_response,
        )

        result = runner.invoke(app, ["market", "get", "TEST-MKT-01"])

        assert result.exit_code == 0
        assert "Open Time" in result.output
        assert "2026-01-05" in result.output

    def test_market_get_shows_created_time(
        self, mock_market_response, mocker
    ) -> None:
        """market get displays created_time field."""
        mocker.patch(
            "kalshi_research.cli.market.fetch_market",
            return_value=mock_market_response,
        )

        result = runner.invoke(app, ["market", "get", "TEST-MKT-01"])

        assert result.exit_code == 0
        assert "Created Time" in result.output

    def test_market_get_time_ordering(
        self, mock_market_response, mocker
    ) -> None:
        """Times displayed in logical order: Open, Created, Close."""
        mocker.patch(
            "kalshi_research.cli.market.fetch_market",
            return_value=mock_market_response,
        )

        result = runner.invoke(app, ["market", "get", "TEST-MKT-01"])

        output = result.output
        open_pos = output.find("Open Time")
        created_pos = output.find("Created Time")
        close_pos = output.find("Close Time")

        # Open should come before Created, Created before Close
        assert open_pos < created_pos < close_pos

    def test_market_get_handles_missing_times(self, mocker) -> None:
        """Gracefully handles markets without open_time/created_time."""
        market_without_times = {
            "ticker": "OLD-MKT",
            "title": "Old Market",
            "status": "active",
            "close_time": "2027-01-01T04:59:00Z",
            "yes_bid": 45,
            "yes_ask": 47,
            # open_time and created_time omitted
        }
        mocker.patch(
            "kalshi_research.cli.market.fetch_market",
            return_value=market_without_times,
        )

        result = runner.invoke(app, ["market", "get", "OLD-MKT"])

        # Should not crash
        assert result.exit_code == 0
        # Should show N/A or skip the row
        assert "Close Time" in result.output
```

### 3.2 Integration Tests

```python
# tests/integration/cli/test_market_commands.py

import pytest

@pytest.mark.integration
@pytest.mark.requires_api
class TestMarketGetIntegration:
    """Integration tests for market get command."""

    def test_market_get_real_market_shows_times(self) -> None:
        """Real API call shows open_time for active markets."""
        from typer.testing import CliRunner
        from kalshi_research.cli.main import app

        runner = CliRunner()

        # Use a known active market
        result = runner.invoke(app, ["market", "get", "KXSB-26-KC"])

        assert result.exit_code == 0
        # Active markets should have these fields
        assert "Open Time" in result.output or "N/A" in result.output
```

---

## 4. Implementation Tasks

### Phase 1: Display Enhancement (TDD)

- [ ] Write unit tests for open_time display
- [ ] Write unit tests for created_time display
- [ ] Write unit test for time ordering
- [ ] Write unit test for missing time handling
- [ ] Update `market get` command to show open_time
- [ ] Update `market get` command to show created_time
- [ ] Run tests, verify all pass

### Phase 2: Documentation

- [ ] Update CLI help text if needed
- [ ] Update skill docs (WORKFLOWS.md) to reference open_time
- [ ] Close TODO-005 upon completion

---

## 5. Acceptance Criteria

1. **Visibility**: `market get` displays `Open Time` and `Created Time`
2. **Ordering**: Times appear in logical order (Open, Created, Close)
3. **Robustness**: Command doesn't crash if fields are missing
4. **Test Coverage**: Unit tests cover normal and edge cases
5. **Documentation**: Skill docs reference the new fields

---

## 6. Impact

This seemingly small change has **high research impact**:

1. **Agents** can now check market timing before recommending
2. **Users** can manually verify temporal constraints
3. **Research workflows** can validate event timing vs market creation

---

## 7. Related Documents

- [TODO-005: Market Open Date Validation](../_todo/TODO-005-market-open-date-validation.md)
- Skill references (dev branch):
  - `kalshi-cli` gotchas: https://github.com/The-Obstacle-Is-The-Way/kalshi-starter-code-python/blob/dev/.codex/skills/kalshi-cli/GOTCHAS.md
  - `kalshi-cli` workflows: https://github.com/The-Obstacle-Is-The-Way/kalshi-starter-code-python/blob/dev/.codex/skills/kalshi-cli/WORKFLOWS.md
