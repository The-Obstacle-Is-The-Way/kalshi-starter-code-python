# TODO-008: Agent Safety Rails (Harness Protection)

## Status
- **Priority**: High (Safety)
- **Status**: Proposed
- **Owner**: TBD

## Context
The current `KalshiClient` is designed for direct developer use. Methods like `create_order` Execute trades immediately upon invocation.

As we move towards using **Autonomous Coding Agents** (LLMs) to drive this system, the lack of "Safety Rails" becomes a critical vulnerability. A hallucinating agent or a logic bug could rapidly execute unwanted trades, draining the account or violating rate limits to the point of a ban.

## Problem
- **Live Fire by Default**: `create_order` has no `dry_run` parameter.
- **No confirmation**: No mechanism to intercept and approve high-value trades.
- **No Budgeting**: No client-side enforcement of max loss or max position size.

## Proposed Solution

### 1. Update `KalshiClient`
Add a `dry_run` parameter to all write operations.
```python
async def create_order(..., dry_run: bool = False) -> OrderResponse:
    if dry_run:
        logger.info("DRY RUN: create_order", ...)
        return OrderResponse(id="dry-run", status="simulated")
    # ... real logic ...
```

### 2. Implement `TradeExecutor` Service
Create a wrapper service `src/kalshi_research/execution/executor.py` that acts as the "Agent Harness".

*   **Capabilities**:
    *   **Budget Guard**: Rejects orders if daily spend > $X.
    *   **Fat Finger Check**: Rejects orders if price deviates > X% from last trade.
    *   **Human-in-the-loop**: For orders > $Y, pause and require CLI confirmation (or explicit user approval signal).
    *   **Audit Log**: Log all agent-initiated actions to a separate `trade_audit.log`.

## Definition of Done
- [ ] `KalshiClient.create_order` accepts `dry_run=True`.
- [ ] `TradeExecutor` implemented with budget limits.
- [ ] Integration tests verify `dry_run` does not hit the API.
