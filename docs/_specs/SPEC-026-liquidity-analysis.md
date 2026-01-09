# SPEC-026: Liquidity Analysis for Kalshi Markets

**Priority**: High (Trading Quality)
**Status**: Draft
**Created**: 2026-01-09
**Context**: Kalshi deprecated the `liquidity` field (Jan 15, 2026). We must calculate our own.

---

## Problem Statement

The Kalshi API deprecated its `liquidity` field, stating developers should calculate their own metrics from raw orderbook data. Without proper liquidity analysis, we risk:

1. **Slippage eating edge** - Entering a position costs more than expected
2. **Trapped positions** - Can't exit without massive price impact
3. **False opportunities** - Detected "edge" is illusory due to thin book

## Kalshi Market Structure (First Principles)

### Binary Contract Basics
- Price range: $0.01 - $0.99 (1-99 cents)
- Settlement: $0 (NO wins) or $1 (YES wins)
- YES bid at X cents = NO ask at (100-X) cents

### Orderbook Structure
```json
{
  "yes": [[price_cents, quantity], ...],  // YES bids only
  "no": [[price_cents, quantity], ...]    // NO bids only
}
```

**Key insight**: No explicit asks. YES ask is implied by NO bid.
- Best YES ask = 100 - Best NO bid
- Spread = 100 - best_yes_bid - best_no_bid

### Liquidity Differs from Traditional Markets
| Traditional Market | Kalshi Market |
|--------------------|---------------|
| Continuous price range | Fixed 1-99 cents |
| Market makers required | Peer-to-peer matching |
| High-frequency trading | Human-speed trading |
| Shares outstanding | Open interest |
| Usually deep books | Often thin books |

---

## Proposed Liquidity Metrics

### 1. Orderbook Depth Score

**Definition**: Total contracts available within N cents of midpoint, weighted by distance.

```python
def orderbook_depth_score(orderbook: Orderbook, radius_cents: int = 10) -> float:
    """
    Calculate weighted depth score.

    Contracts closer to midpoint are weighted more heavily because
    they're more likely to execute.

    Args:
        orderbook: Orderbook snapshot
        radius_cents: How many cents from midpoint to consider

    Returns:
        Weighted depth score (higher = more liquid)
    """
    midpoint = orderbook.midpoint
    if midpoint is None:
        return 0.0

    score = 0.0
    for side in [orderbook.yes, orderbook.no]:
        if side is None:
            continue
        for price, qty in side:
            distance = abs(price - float(midpoint))
            if distance <= radius_cents:
                # Weight by inverse distance (closer = more weight)
                weight = 1.0 - (distance / radius_cents)
                score += qty * weight

    return score
```

### 2. Slippage Estimator

**Definition**: Given order size N, estimate average fill price.

```python
def estimate_slippage(
    orderbook: Orderbook,
    side: Literal["yes", "no"],
    action: Literal["buy", "sell"],
    quantity: int,
) -> SlippageEstimate:
    """
    Estimate execution price for given order size.

    Returns:
        SlippageEstimate with:
        - best_price: Best available price
        - avg_fill_price: Weighted average fill price
        - worst_price: Worst price touched
        - slippage_cents: avg_fill - best_price
        - fillable_quantity: How much can actually fill
        - remaining: Unfilled contracts (if insufficient depth)
    """
    # Walk the book, accumulating fills
    # For BUY YES: consume YES asks (implied from NO bids)
    # For SELL YES: consume YES bids
    ...
```

**Use case**: Before entering a trade, know your true cost.

### 3. Liquidity Score (Composite)

**Definition**: Single 0-100 score combining multiple factors.

```python
def liquidity_score(
    market: Market,
    orderbook: Orderbook,
    weights: LiquidityWeights | None = None,
) -> int:
    """
    Composite liquidity score for quick filtering.

    Components (default weights):
    - Spread (30%): Tighter = better
    - Depth (30%): More contracts near midpoint = better
    - Volume 24h (20%): More activity = better
    - Open Interest (20%): More outstanding = better

    Returns:
        Score 0-100 where:
        - 0-25: Illiquid (avoid)
        - 26-50: Thin (small size only)
        - 51-75: Moderate (reasonable size)
        - 76-100: Liquid (trade freely)
    """
    spread_score = max(0, 100 - (orderbook.spread or 100) * 5)  # 20c spread = 0
    depth_score = min(100, orderbook_depth_score(orderbook) / 10)
    volume_score = min(100, market.volume_24h / 100)  # 10k = 100
    oi_score = min(100, market.open_interest / 50)  # 5k = 100

    w = weights or LiquidityWeights()
    return int(
        spread_score * w.spread +
        depth_score * w.depth +
        volume_score * w.volume +
        oi_score * w.open_interest
    )
```

### 4. Max Safe Order Size

**Definition**: Largest order that won't move price more than X%.

```python
def max_safe_order_size(
    orderbook: Orderbook,
    side: Literal["yes", "no"],
    max_slippage_cents: int = 3,
) -> int:
    """
    Calculate largest order within slippage tolerance.

    Args:
        orderbook: Current orderbook
        side: Which side to buy
        max_slippage_cents: Maximum acceptable slippage

    Returns:
        Maximum contracts that can be bought within slippage limit
    """
    # Walk book until cumulative slippage exceeds threshold
    ...
```

**Use case**: Position sizing. "I want to buy YES, what's the most I can buy without moving price >3c?"

---

## Implementation Plan

### Phase 1: Core Metrics (Priority)

1. Create `src/kalshi_research/analysis/liquidity.py`:
   - `OrderbookAnalyzer` class
   - `orderbook_depth_score()`
   - `liquidity_score()`
   - `LiquidityGrade` enum (ILLIQUID, THIN, MODERATE, LIQUID)

2. Add to Market model:
   - `liquidity_score` computed property (requires orderbook)
   - Or separate `MarketWithLiquidity` enriched model

### Phase 2: Slippage Analysis

1. Add `SlippageEstimator` class:
   - `estimate_fill_price(side, action, quantity)`
   - `price_impact(side, quantity)`
   - `max_safe_size(side, max_slippage)`

2. Integration:
   - Add to CLI: `kalshi market liquidity TICKER`
   - Add to scanner: Filter by liquidity score

### Phase 3: Trading Integration

1. Pre-trade checks:
   - Warn if order > max_safe_size
   - Show expected slippage before execution

2. Research workflow:
   - Include liquidity in market recommendations
   - "This market has edge but is illiquid - reduce size"

---

## Acceptance Criteria

- [ ] `OrderbookAnalyzer` class with depth analysis
- [ ] `liquidity_score()` returns 0-100 composite score
- [ ] `estimate_slippage()` walks orderbook for fill estimation
- [ ] `max_safe_order_size()` for position sizing
- [ ] CLI command: `kalshi market liquidity TICKER`
- [ ] Scanner filter: `--min-liquidity 50`
- [ ] Documentation with examples
- [ ] Unit tests with mock orderbooks

---

## Examples

### CLI Usage
```bash
# Check liquidity before trading
$ kalshi market liquidity KXBTC-26JAN15-T100000

Liquidity Analysis: KXBTC-26JAN15-T100000
─────────────────────────────────────────
Score:        72/100 (MODERATE)
Spread:       3c ($0.03)
Depth (10c):  1,250 contracts
Volume 24h:   8,543
Open Interest: 12,301

Order Size Analysis:
  10 contracts:  0.1c slippage ($0.001/contract)
  50 contracts:  0.8c slippage ($0.008/contract)
  100 contracts: 2.1c slippage ($0.021/contract)
  500 contracts: 8.5c slippage ($0.085/contract)

Max Safe Size (3c slippage): 142 contracts
```

### Code Usage
```python
from kalshi_research.analysis.liquidity import OrderbookAnalyzer

async with KalshiPublicClient() as client:
    market = await client.get_market("KXBTC-26JAN15-T100000")
    orderbook = await client.get_orderbook("KXBTC-26JAN15-T100000")

    analyzer = OrderbookAnalyzer(market, orderbook)

    # Quick filter
    if analyzer.liquidity_score < 50:
        print("Market too illiquid, skipping")
        return

    # Position sizing
    max_size = analyzer.max_safe_order_size("yes", max_slippage_cents=3)
    print(f"Can safely buy up to {max_size} YES contracts")

    # Pre-trade check
    slippage = analyzer.estimate_slippage("yes", "buy", 100)
    print(f"Buying 100 YES: avg fill {slippage.avg_fill_price}c, slippage {slippage.slippage_cents}c")
```

---

## Related Resources

- [Kalshi API Orderbook](https://docs.kalshi.com) - Raw orderbook data
- `src/kalshi_research/api/models/orderbook.py` - Current orderbook model
- `src/kalshi_research/analysis/edge.py` - Edge detection (uses spread)
- `src/kalshi_research/analysis/scanner.py` - Market scanner (could use liquidity filter)

---

## Open Questions

1. **Orderbook snapshot frequency**: How often should we refresh orderbooks for active monitoring?
2. **Historical liquidity**: Should we track liquidity over time to detect patterns?
3. **Cross-market liquidity**: Some events have multiple markets - should we analyze aggregate liquidity?
4. **Dynamic position sizing**: Should the system auto-adjust order size based on liquidity?
