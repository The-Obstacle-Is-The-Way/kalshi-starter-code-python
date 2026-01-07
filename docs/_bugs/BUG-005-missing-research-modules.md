# BUG-005: Missing Research Modules

**Priority:** P3
**Status:** Open
**Discovered:** 2026-01-06
**Spec Reference:** SPEC-004 Section 3.1

---

## Summary

Several research modules specified in SPEC-004 are missing from `src/kalshi_research/research/`.

## Expected Files (per SPEC-004)

```
research/
├── __init__.py          ✓ EXISTS
├── thesis.py            ✓ EXISTS
├── backtest.py          ✗ MISSING
└── notebook_utils.py    ✗ MISSING
```

## Missing Modules

### 1. `backtest.py`
Historical thesis testing framework.

Key features needed:
- Backtest thesis against historical data
- Calculate hypothetical P&L
- Track accuracy over time periods
- Compare thesis performance vs market

### 2. `notebook_utils.py`
Jupyter notebook helpers.

Required utilities:
- Data loading shortcuts
- Common plot configurations
- Display formatters for markets/edges
- Interactive widgets for analysis

## Impact

- Cannot backtest research theses historically (backtest.py)
- No Jupyter notebook convenience functions (notebook_utils.py)

## Fix

Implement the two missing modules:

```python
# backtest.py
@dataclass
class BacktestResult:
    thesis_id: str
    period_start: datetime
    period_end: datetime
    hypothetical_pnl: float
    accuracy: float
    num_predictions: int

class ThesisBacktester:
    def __init__(self, db: DatabaseManager) -> None: ...

    async def backtest_thesis(
        self,
        thesis: Thesis,
        start_date: datetime,
        end_date: datetime,
    ) -> BacktestResult: ...

    async def backtest_all(
        self,
        theses: list[Thesis],
        start_date: datetime,
        end_date: datetime,
    ) -> list[BacktestResult]: ...

# notebook_utils.py
def setup_notebook() -> None:
    """Configure matplotlib, pandas display options."""
    ...

async def load_markets(status: str = "open") -> pd.DataFrame:
    """Load markets into a DataFrame."""
    ...

def display_market(market: Market) -> None:
    """Rich display of market in Jupyter."""
    ...

def display_edge(edge: Edge) -> None:
    """Rich display of edge in Jupyter."""
    ...
```

## Acceptance Criteria

- [ ] `backtest.py` implemented with thesis backtesting
- [ ] `notebook_utils.py` implemented with Jupyter helpers
- [ ] Both modules have >85% test coverage
- [ ] Both modules pass mypy --strict
- [ ] Works in Jupyter notebooks
