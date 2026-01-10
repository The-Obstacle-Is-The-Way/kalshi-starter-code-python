# TODO-00B: TradeExecutor with Budget Limits (FUTURE)

**Priority**: Low (until agent trading enabled)
**Status**: DEFERRED (Phase 2)
**Created**: 2026-01-09
**Depends On**: Active agent trading use case

> **Note (2026-01-10):** This TODO is the backlog seed. The implementation-ready spec lives in
> `docs/_specs/SPEC-034-trade-executor-safety-harness.md`.
>
> **Update (2026-01-10):** Phase 1 of `TradeExecutor` is implemented in `src/kalshi_research/execution/`.
> This TODO now tracks Phase 2 hardening only (budgets/positions/liquidity guards).

---

## Overview

Implement a full `TradeExecutor` class with budget limits, position caps, and safety rails for autonomous agent trading.

## Why Deferred?

1. **No immediate need**: The platform is currently research-focused
2. **Phase 1 implemented**: TradeExecutor exists (dry-run default, audit logging, confirmation gate, basic limits)
3. **High complexity**: Full trading harness needs careful design (budgets, positions, liquidity checks)
4. **Risk**: Financial risk if implemented poorly

## When to Implement

Consider implementing when:
- [ ] You want to enable autonomous agent trading
- [ ] You need automated position management
- [ ] You want to enforce budget constraints programmatically

## Proposed Scope (from TODO-008)

```python
class TradeExecutor:
    """Safe trading executor with budget limits."""

    def __init__(
        self,
        client: KalshiClient,
        *,
        max_daily_loss: float = 50.0,
        max_position_size: int = 100,
        require_confirmation: bool = True,
    ) -> None:
        ...

    async def execute_trade(
        self,
        ticker: str,
        side: str,
        action: str,
        quantity: int,
        price: int,
    ) -> TradeResult:
        """Execute trade with all safety checks."""
        ...
```

## Features to Include

- Daily loss limit tracking
- Per-position size limits
- Confirmation prompts (optional)
- Audit logging
- Rollback capability (cancel orders)
- Integration with liquidity analysis (SPEC-026)

## Related

- [TODO-008 (Archived)](../_archive/future/TODO-008-agent-safety-rails.md) - dry_run implementation
- [Security Audit](../_debt/security-audit.md) - Agent safety section
- [SPEC-026 (Archived)](../_archive/specs/SPEC-026-liquidity-analysis.md) - Liquidity for position sizing

---

**Note**: This is a placeholder TODO (00B series) for future work. When you decide to implement, create a proper TODO-XXX with detailed acceptance criteria.
