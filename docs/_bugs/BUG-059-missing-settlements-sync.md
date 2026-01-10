# BUG-059: Missing Portfolio Settlements Sync

**Priority:** P1 (High - incomplete data causes downstream bugs)
**Status:** ✅ Fixed
**Found:** 2026-01-10
**Fixed:** 2026-01-10
**Owner:** Platform

---

## Summary

The `PortfolioSyncer` fetched fills (`/portfolio/fills`) but NOT settlements (`/portfolio/settlements`). This caused incomplete history and prevented “all time” P&L and win/loss stats from including resolved markets.

---

## Root Cause

### What We Sync

| Endpoint | Synced? | Purpose |
|----------|---------|---------|
| `/portfolio/fills` | ✅ Yes | Individual trade executions |
| `/portfolio/positions` | ✅ Yes | Current holdings + `realized_pnl` |
| `/portfolio/settlements` | ❌ **NO** | Position closures from market resolution |

### Why Settlements Matter

When a market settles:
1. Your position auto-closes (not a regular sell)
2. This appears in `/portfolio/settlements`, NOT `/portfolio/fills`
3. FIFO sees buys without matching sells → crash (BUG-058)

### API Response (from official docs)

```json
{
  "settlements": [{
    "ticker": "KXMARKET-123",
    "market_result": "yes",
    "yes_count": 100,
    "no_count": 0,
    "yes_total_cost": 4500,
    "no_total_cost": 0,
    "revenue": 10000,
    "settled_time": "2026-01-10T00:00:00Z",
    "fee_cost": "0.50"
  }],
  "cursor": "..."
}
```

Key fields:
- `market_result`: `yes`, `no`, `scalar`, or `void`
- `yes_count` / `no_count`: Contracts held at settlement
- `revenue`: Payout received (100¢ per winning contract)
- `yes_total_cost` / `no_total_cost`: Cost basis (Kalshi-computed)

---

## Impact

1. **BUG-058 root cause**: FIFO crashes on orphan buys (settled positions)
2. **Incomplete win/loss stats**: Settled positions not counted
3. **Data integrity**: Local DB doesn't match actual account history

---

## Fix Plan (Implemented)

### 1. Add Portfolio Settlement Model (DB)

```python
# portfolio/models.py
class PortfolioSettlement(Base):
    __tablename__ = "portfolio_settlements"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(100), nullable=False)
    event_ticker: Mapped[str | None] = mapped_column(String(100), nullable=True)
    market_result: Mapped[str] = mapped_column(String(20), nullable=False)  # yes/no/void/scalar
    yes_count: Mapped[int] = mapped_column(Integer, default=0)
    no_count: Mapped[int] = mapped_column(Integer, default=0)
    yes_total_cost: Mapped[int] = mapped_column(Integer, default=0)
    no_total_cost: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[int] = mapped_column(Integer, default=0)
    fee_cost_dollars: Mapped[str] = mapped_column(String(32), nullable=False)
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

### 2. Add Pydantic Models

```python
# api/models/portfolio.py
class Settlement(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    event_ticker: str | None = None
    market_result: str
    yes_count: int = 0
    no_count: int = 0
    yes_total_cost: int = 0
    no_total_cost: int = 0
    revenue: int = 0
    fee_cost: str = "0.0000"
    settled_time: str
    value: int | None = None

class SettlementPage(BaseModel):
    model_config = ConfigDict(frozen=True)
    settlements: list[Settlement]
    cursor: str | None = None
```

### 3. Add API Client Method

```python
# api/client.py
async def get_settlements(
    self,
    ticker: str | None = None,
    min_ts: int | None = None,
    max_ts: int | None = None,
    limit: int = 100,
    cursor: str | None = None,
) -> SettlementPage:
    """Fetch settlement history."""
    params = {"limit": limit}
    if ticker:
        params["ticker"] = ticker
    if min_ts:
        params["min_ts"] = min_ts
    if max_ts:
        params["max_ts"] = max_ts
    if cursor:
        params["cursor"] = cursor

    data = await self._auth_get("/portfolio/settlements", params=params)
    return SettlementPage.model_validate(data)
```

### 4. Add Sync Method

```python
# portfolio/syncer.py
async def sync_settlements(self, since: datetime | None = None) -> int:
    """Fetch and store settlement history."""
    # Similar to sync_trades but for settlements
```

### 5. Use Settlements in P&L Summary

Rather than inventing synthetic fills, we compute settlement P&L directly from Kalshi’s settlement record:

`settlement_pnl_cents = revenue - yes_total_cost - no_total_cost - fee_cost`

---

## Acceptance Criteria

- [x] `PortfolioSettlement` SQLAlchemy model added (`portfolio_settlements` table)
- [x] `Settlement` + `SettlementPage` Pydantic models added to `api/models/portfolio.py`
- [x] `get_settlements()` method added to `KalshiClient`
- [x] `sync_settlements()` method added to `PortfolioSyncer`
- [x] `kalshi portfolio sync` calls `sync_settlements()`
- [x] P&L summary includes settlement P&L (and counts as a closed outcome)
- [x] Unit tests for settlement sync + settlement P&L
- [x] `uv run pre-commit run --all-files` passes

---

## Test Plan

```bash
# Unit tests
uv run pytest tests/unit/portfolio/test_syncer.py -v -k settlement
uv run pytest tests/unit/api/test_client.py -v -k settlement
uv run pytest tests/unit/portfolio/test_pnl.py -v -k settlement

# Integration (requires auth)
uv run kalshi portfolio sync
# Should show "Synced X settlements"
```

---

## References

- **Caused by:** Incomplete data model
- **Blocks:** BUG-058 comprehensive fix
- **API Docs:** https://docs.kalshi.com/api-reference/portfolio/get-settlements
