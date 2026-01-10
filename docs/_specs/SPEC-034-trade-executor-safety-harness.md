# SPEC-034: TradeExecutor Safety Harness (Budgeted, Safe-by-Default)

**Status:** Draft
**Priority:** P2 (Blocked until agent trading is desired)
**Created:** 2026-01-10
**Owner:** Solo
**Effort:** ~2–6 days (Phase 1), ongoing hardening

---

## Summary

Create a `TradeExecutor` service that wraps authenticated Kalshi trading operations with **hard safety rails**:

- safe-by-default execution (`dry_run` unless explicitly live),
- risk limits (daily loss, max notional, max position size),
- price sanity checks (fat-finger guard),
- liquidity-aware sizing (integrate SPEC-026 liquidity analysis),
- structured audit logging.

This is the missing “agent harness” described in `docs/_archive/future/TODO-008-agent-safety-rails.md` and
`docs/_future/TODO-00B-trade-executor-phase2.md`.

---

## Goals

1. Prevent accidental/unauthorized trading by any automation (LLM or otherwise).
2. Make all trade attempts auditable and replayable (structured logs).
3. Provide a single entry point for order creation/cancel with policy enforcement.

---

## Non-Goals

- No automated strategy selection (“when to trade” is not here).
- No portfolio optimization or market making logic.
- No multi-agent decision-making.

---

## SSOT

- Write endpoints + limits: `docs/_vendor-docs/kalshi-api-reference.md`
- Authenticated client: `src/kalshi_research/api/client.py` (`KalshiClient.create_order(..., dry_run=...)`)
- Liquidity scoring: `src/kalshi_research/analysis/liquidity.py` (SPEC-026 implemented)
- Security findings: `docs/_debt/security-audit.md` (Agent Harness Safety)

---

## Design

### 1) Safe-by-default execution model

`TradeExecutor` must default to **non-live** operation.

Proposed constructor:

```python
TradeExecutor(
  client: KalshiClient,
  *,
  live: bool = False,                 # default False
  max_daily_loss_usd: float = 50.0,
  max_notional_usd: float = 200.0,
  max_position_contracts: int = 100,
  max_orders_per_day: int = 25,
  require_confirmation: bool = True,  # only for interactive CLI usage
)
```

Rules:

- If `live=False`, all order placement uses `dry_run=True` and never hits the network write endpoint.
- If `live=True`, `dry_run=False` is allowed *only after* all checks pass.

### 2) Risk checks (hard fails)

Before placing an order:

1. **Price bounds**: enforce Kalshi invariant `1 <= price_cents <= 99` (already in client; executor double-checks).
2. **Fat-finger guard**:
   - fetch current orderbook midpoint
   - require `abs(price - midpoint) <= max_price_deviation_cents` (configurable)
3. **Budget guard**:
   - maintain daily P&L / spend counters in a local store (DB table or JSON log-derived)
   - reject if trade would exceed `max_notional_usd` or `max_daily_loss_usd`
4. **Position cap**:
   - query current position (local DB or API)
   - reject if trade would exceed `max_position_contracts`
5. **Liquidity-aware sizing** (optional hard gate):
   - compute liquidity score / depth for the market
   - for low liquidity, cap quantity or require explicit override

### 3) Audit logging (append-only)

Every call produces a structured audit event:

```json
{
  "timestamp": "...",
  "mode": "dry_run|live",
  "ticker": "...",
  "side": "yes|no",
  "action": "buy|sell",
  "count": 10,
  "price_cents": 55,
  "checks": {"passed": true, "failures": []},
  "order_id": "dry-run-...|real-order-id",
  "client_order_id": "...",
  "notes": "..."
}
```

Storage options:

- `data/trade_audit.log` (JSONL), or
- a dedicated DB table (`trade_audit_events`) for querying.

Phase 1 uses JSONL for minimal migration surface; DB persistence is Phase 2.

---

## Module Layout

```txt
src/kalshi_research/execution/
  __init__.py
  executor.py            # TradeExecutor
  models.py              # Pydantic models for requests/results
  audit.py               # JSONL writer + schema
```

This avoids mixing trading safety logic into the API client.

---

## Testing

Unit tests (no network):

- `live=False` always calls `create_order(..., dry_run=True)` (mock client)
- risk checks reject invalid price/count
- fat-finger guard rejects extreme deviation

Integration tests (optional, require Kalshi write keys):

- in demo env only, with `live=True`, places a tiny order behind an explicit flag and then cancels.

---

## Implementation Plan

### Phase 1 (library only, dry-run by default)

1. Implement `TradeExecutor` with:
   - dry-run default
   - budget + position caps (pluggable providers)
   - audit logging JSONL
2. Add unit tests around safety rails.

### Phase 2 (optional persistence + CLI plumbing)

1. Add DB table for audit events + daily counters (Alembic migration).
2. Add a CLI wrapper (`kalshi trade ...` or `kalshi agent trade ...`) only when needed.

---

## Acceptance Criteria

- It is impossible to hit Kalshi write endpoints without explicitly setting `live=True`.
- Every order attempt (dry-run or live) emits one audit log event.
- Violations of risk checks fail fast with actionable error messages and do not place orders.

---

## References

- `docs/_archive/future/TODO-008-agent-safety-rails.md`
- `docs/_future/TODO-00B-trade-executor-phase2.md`
- `docs/_debt/security-audit.md`
- `docs/_archive/specs/SPEC-026-liquidity-analysis.md`
