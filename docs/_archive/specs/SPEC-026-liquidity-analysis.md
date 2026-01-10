# SPEC-026: Liquidity Analysis for Kalshi Markets

**Priority**: High (Trading Quality)
**Status**: Implemented
**Created**: 2026-01-09
**Completed**: 2026-01-09
**Context**: Kalshi deprecated the `liquidity` field (Jan 15, 2026). We must calculate our own.

---

## Executive Summary

Kalshi prediction markets have unique liquidity characteristics that differ significantly from traditional financial markets. This spec defines a comprehensive liquidity analysis framework tailored to Kalshi's binary contract structure, enabling:

1. **Smart position sizing** - Know how much you can trade without excessive slippage
2. **Opportunity filtering** - Skip markets where edge would be eaten by illiquidity
3. **Execution optimization** - Time and size orders for best fills

---

## Problem Statement

**Deprecation Clarification:**
- `liquidity` (integer, cents) → **REMOVED** Jan 15, 2026
- `liquidity_dollars` (string, dollars) → **REMAINS** as the replacement

The new `liquidity_dollars` field represents "current offer value" - a simple sum that doesn't capture depth distribution, slippage, or execution quality. Without proper liquidity analysis, we risk:

1. **Slippage eating edge** - Entering a position costs more than expected
2. **Trapped positions** - Can't exit without massive price impact
3. **False opportunities** - Detected "edge" is illusory due to thin book

---

## Kalshi's `liquidity_dollars` vs Our Metrics

> **Note:** `liquidity_dollars` is the **surviving replacement** for the deprecated `liquidity` field.
> It remains available in the API after Jan 15, 2026.

**What Kalshi provides:**
- `liquidity_dollars` - "Current offer value" in dollar format (e.g., `"1250.00"`)
- Simple aggregate of all resting orders (NOT being deprecated - this is the new standard)

**Limitations of Kalshi's metric:**
- No depth weighting (distant orders count same as BBO)
- No slippage estimation for specific order sizes
- No imbalance detection (YES vs NO side)
- Single number doesn't inform position sizing

**What our custom metrics provide:**
- **Weighted Depth Score** - Distance-weighted contracts (BBO matters more)
- **Slippage Estimator** - Walk-the-book simulation for any order size
- **Max Safe Size** - Largest order within slippage tolerance
- **Imbalance Detection** - Which side has more depth
- **Composite Score** - Actionable 0-100 grade with warnings

---

## Industry Research & Best Practices

### Kalshi-Specific Liquidity Reality

From [The Economics of the Kalshi Prediction Market (UCD 2025)](https://www.ucd.ie/economics/t4media/WP2025_19.pdf):

> "Average final trading volume in the top decile of Kalshi markets was only $526,245. And at any point in time, the amount of liquidity available is far smaller, with relatively small amounts available in the order book."

**Key insight**: Even "liquid" Kalshi markets are thin by traditional standards. The orderbook at any moment is much smaller than cumulative volume suggests.

### The Favorite-Longshot Bias

From academic research on Kalshi:

> "Kalshi prices display a systematic favorite-longshot bias. Contracts with low prices win less than required for them to break even on average while the opposite applies to contracts with high prices."

**Implication**: Liquidity analysis should account for price level - contracts near 0% or 100% may have different liquidity profiles.

### Market Making Economics

From [Metamask Prediction Market Guide](https://metamask.io/news/prediction-markets-concepts-terminology):

> "It is not +EV for market-makers to provide liquidity on prediction markets because of the tail risk of being stuck with zeroed-out shares."

**Implication**: Unlike traditional markets, Kalshi doesn't have professional market makers providing constant liquidity. Orderbook depth is organic and can evaporate quickly.

### Standard Liquidity Metrics

From [CME Group Liquidity Research](https://www.cmegroup.com/articles/2025/reassessing-liquidity-beyond-order-book-depth.html):

The industry standard **Square-Root Impact Model**:
```
Estimated Impact = Spread Cost + Factor × Daily Vol × sqrt(Order Qty / ADTV)
```

And from [Altrady Order Book Analysis](https://www.altrady.com/crypto-trading/fundamental-analysis/liquidity-order-book-depth):

> "Advanced quantitative strategies move beyond simple volume summation, weighting the significance of liquidity based on its distance from the current price. Liquidity closer to the best bid/offer (BBO) is weighted more heavily."

### Temporal Liquidity Patterns

From [Amberdata Liquidity Research](https://blog.amberdata.io/the-rhythm-of-liquidity-temporal-patterns-in-market-depth):

> "At 11:00 UTC on Binance, the Bitcoin orderbook shows $3.86 million in liquidity within 10 basis points of the mid-price. By 21:00 UTC, the same pair shows only $2.71 million in depth—a 42% reduction."

**Implication**: Liquidity varies significantly by time of day. Kalshi markets likely follow US trading hours patterns.

### Kalshi Performance Benchmark

From [Phemex Prediction Markets Guide](https://phemex.com/academy/what-are-prediction-markets):

> "Kalshi's market depth is a core performance pillar, with average slippage of less than 0.1%, materially below the sector average."

---

## Kalshi Market Structure (First Principles)

### Binary Contract Basics
- Price range: $0.01 - $0.99 (1-99 cents)
- Settlement: $0 (NO wins) or $1 (YES wins)
- YES bid at X cents = NO ask at (100-X) cents
- Fees: Volume rewards up to $0.005/contract for trades $0.03-$0.97

### Orderbook API Endpoint

**REST Endpoint:** `GET /markets/{ticker}/orderbook`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `depth` | integer | 0 | Depth levels to retrieve (0 = all, 1-100 for specific depth) |

**Response Structure:**
```json
{
  "orderbook": {
    "yes": [[price_cents, quantity], ...],
    "no": [[price_cents, quantity], ...],
    "yes_dollars": [["0.4700", quantity], ...],
    "no_dollars": [["0.5300", quantity], ...]
  }
}
```

**Key insight**: No explicit asks. YES ask is implied by NO bid.
- Best YES ask = 100 - Best NO bid
- Spread = 100 - best_yes_bid - best_no_bid
- Levels sorted best-to-worst price (highest bid first)
- Use `depth` parameter to limit API response size for performance

### WebSocket Real-Time Orderbook (Optional Enhancement)

For active trading scenarios requiring real-time liquidity monitoring, use the `orderbook_delta` WebSocket channel:

**Subscription:**
```json
{
  "id": 2,
  "cmd": "subscribe",
  "params": {
    "channels": ["orderbook_delta"],
    "market_tickers": ["KXBTC-26JAN15-T100000"]
  }
}
```

**Message Flow:**
1. **Initial Snapshot** (`orderbook_snapshot`) - Full orderbook state
2. **Incremental Deltas** (`orderbook_delta`) - Price/quantity changes

**Delta Message:**
```json
{
  "type": "orderbook_delta",
  "sid": 2,
  "seq": 3,
  "msg": {
    "market_ticker": "KXBTC-26JAN15-T100000",
    "price": 47,
    "price_dollars": "0.470",
    "delta": -50,
    "side": "yes"
  }
}
```

**Implementation Note:** Track `seq` numbers to detect gaps. If gap detected, re-subscribe to get fresh snapshot. See `docs/_vendor-docs/kalshi-api-reference.md` for full WebSocket protocol details.

### How Liquidity Differs from Traditional Markets

| Aspect | Traditional Markets | Kalshi Markets |
|--------|---------------------|----------------|
| Price range | Continuous | Fixed 1-99 cents |
| Market makers | Professional, obligated | Organic, opportunistic |
| Trading speed | Milliseconds (HFT) | Seconds to minutes |
| Book depth | Usually deep | Often thin |
| Liquidity source | Market makers + flow | Peer-to-peer only |
| Exit risk | Low (can always sell) | High (may be trapped) |
| Price impact | Manageable | Can be severe |

### Liquidity Challenges Unique to Prediction Markets

1. **Binary settlement risk** - Contracts go to $0 or $1, creating tail risk for liquidity providers
2. **Event-driven spikes** - News can cause liquidity to vanish instantly
3. **No shorting mechanism** - Can't easily hedge positions
4. **Expiration certainty** - Unlike stocks, all contracts expire at known dates

---

## Proposed Liquidity Metrics

### 1. Orderbook Depth Score (Weighted)

**Definition**: Total contracts available within N cents of midpoint, weighted by distance from BBO.

```python
@dataclass
class DepthAnalysis:
    """Orderbook depth analysis results."""
    total_contracts: int          # Raw count within radius
    weighted_score: float         # Distance-weighted score
    yes_side_depth: int          # Contracts on YES side
    no_side_depth: int           # Contracts on NO side
    imbalance_ratio: float       # Positive = more YES depth

def orderbook_depth_score(
    orderbook: Orderbook,
    radius_cents: int = 10,
) -> DepthAnalysis:
    """
    Calculate weighted depth score.

    Uses inverse-distance weighting as recommended by CME Group research:
    contracts closer to midpoint are weighted more heavily because
    they represent immediately executable liquidity.

    Args:
        orderbook: Orderbook snapshot
        radius_cents: How many cents from midpoint to consider

    Returns:
        DepthAnalysis with weighted and raw metrics
    """
    midpoint = orderbook.midpoint
    if midpoint is None:
        return DepthAnalysis(0, 0.0, 0, 0, 0.0)

    weighted_score = 0.0
    yes_depth = 0
    no_depth = 0

    for side_name, levels in [("yes", orderbook.yes), ("no", orderbook.no)]:
        if levels is None:
            continue
        for price, qty in levels:
            # Orderbook returns YES bids and NO bids. Convert NO bids to implied YES asks so both
            # sides are comparable around the YES midpoint.
            effective_price = price if side_name == "yes" else 100 - price
            distance = abs(effective_price - float(midpoint))
            if distance <= radius_cents:
                # Inverse distance weighting (BBO = weight 1.0)
                weight = 1.0 - (distance / (radius_cents + 1))
                weighted_score += qty * weight

                if side_name == "yes":
                    yes_depth += qty
                else:
                    no_depth += qty

    total = yes_depth + no_depth
    imbalance = (yes_depth - no_depth) / max(total, 1)

    return DepthAnalysis(
        total_contracts=total,
        weighted_score=weighted_score,
        yes_side_depth=yes_depth,
        no_side_depth=no_depth,
        imbalance_ratio=imbalance,
    )
```

### 2. Slippage Estimator

**Definition**: Given order size N, estimate average fill price by walking the book.

```python
@dataclass
class SlippageEstimate:
    """Slippage estimation results."""
    best_price: int              # Best available price (cents)
    avg_fill_price: float        # Volume-weighted average fill
    worst_price: int             # Worst price level touched
    slippage_cents: float        # avg_fill - best_price
    slippage_pct: float          # Slippage as % of best price
    fillable_quantity: int       # How much can actually fill
    remaining_unfilled: int      # Contracts that can't fill (insufficient depth)
    levels_crossed: int          # How many price levels consumed

def estimate_slippage(
    orderbook: Orderbook,
    side: Literal["yes", "no"],
    action: Literal["buy", "sell"],
    quantity: int,
) -> SlippageEstimate:
    """
    Estimate execution price for given order size.

    Walks the orderbook level by level, simulating fills.

    For BUY YES: consume YES asks (implied from NO bids at 100-price)
    For SELL YES: consume YES bids directly
    For BUY NO: consume NO asks (implied from YES bids at 100-price)
    For SELL NO: consume NO bids directly

    Args:
        orderbook: Current orderbook state
        side: "yes" or "no"
        action: "buy" or "sell"
        quantity: Number of contracts to estimate

    Returns:
        SlippageEstimate with fill analysis
    """
    # Determine which side of book to consume
    if side == "yes":
        if action == "buy":
            # Buy YES = take from NO bids (implied asks)
            levels = _invert_levels(orderbook.no)  # Convert to YES ask prices
        else:
            # Sell YES = hit YES bids
            levels = orderbook.yes
    else:
        if action == "buy":
            # Buy NO = take from YES bids (implied asks)
            levels = _invert_levels(orderbook.yes)
        else:
            # Sell NO = hit NO bids
            levels = orderbook.no

    if not levels:
        return SlippageEstimate(
            best_price=0, avg_fill_price=0, worst_price=0,
            slippage_cents=0, slippage_pct=0,
            fillable_quantity=0, remaining_unfilled=quantity,
            levels_crossed=0,
        )

    # Walk book, accumulating fills
    filled = 0
    cost = 0.0
    levels_crossed = 0
    sorted_levels = sorted(levels, key=lambda x: x[0], reverse=(action == "sell"))
    best_price = sorted_levels[0][0]
    worst_price = best_price

    for price, available_qty in sorted_levels:
        if filled >= quantity:
            break

        take = min(available_qty, quantity - filled)
        filled += take
        cost += take * price
        worst_price = price
        levels_crossed += 1

    avg_fill = cost / filled if filled > 0 else 0
    slippage = avg_fill - best_price if action == "buy" else best_price - avg_fill

    return SlippageEstimate(
        best_price=best_price,
        avg_fill_price=avg_fill,
        worst_price=worst_price,
        slippage_cents=abs(slippage),
        slippage_pct=abs(slippage) / best_price * 100 if best_price > 0 else 0,
        fillable_quantity=filled,
        remaining_unfilled=quantity - filled,
        levels_crossed=levels_crossed,
    )

def _invert_levels(levels: list[tuple[int, int]] | None) -> list[tuple[int, int]]:
    """Convert bid levels to implied ask levels (100 - price)."""
    if levels is None:
        return []
    return [(100 - price, qty) for price, qty in levels]
```

### 3. Price Impact Model

**Definition**: Square-root impact model adapted for Kalshi's binary structure.

```python
def estimate_price_impact(
    market: Market,
    orderbook: Orderbook,
    order_quantity: int,
    impact_factor: float = 0.1,  # Calibrated for Kalshi
) -> float:
    """
    Estimate market price impact using square-root model.

    Based on CME Group research:
    Impact = Spread + Factor × Volatility × sqrt(Order / ADTV)

    For Kalshi, we simplify to:
    Impact = Spread/2 + Factor × sqrt(Order / Avg Daily Volume)

    Args:
        market: Market data with volume_24h
        orderbook: Current orderbook
        order_quantity: Proposed order size
        impact_factor: Calibration factor (default 0.1 for Kalshi)

    Returns:
        Estimated price impact in cents
    """
    spread = orderbook.spread or 10
    adtv = max(market.volume_24h, 1)

    # Square-root impact component
    sqrt_component = impact_factor * math.sqrt(order_quantity / adtv)

    # Total impact = half spread (cross) + sqrt component
    impact_cents = (spread / 2) + (sqrt_component * 100)

    return min(impact_cents, 50)  # Cap at 50c (half the range)
```

### 4. Liquidity Score (Composite)

**Definition**: Single 0-100 score combining multiple factors with configurable weights.

```python
class LiquidityGrade(str, Enum):
    """Liquidity grade classification."""
    ILLIQUID = "illiquid"    # 0-25: Avoid or tiny size only
    THIN = "thin"            # 26-50: Small size, expect slippage
    MODERATE = "moderate"    # 51-75: Reasonable size, manageable slippage
    LIQUID = "liquid"        # 76-100: Trade freely

@dataclass
class LiquidityWeights:
    """Weights for composite liquidity score."""
    spread: float = 0.30      # Tighter spread = better
    depth: float = 0.30       # More depth = better
    volume: float = 0.20      # More activity = better
    open_interest: float = 0.20  # More outstanding = better

    def __post_init__(self) -> None:
        total = self.spread + self.depth + self.volume + self.open_interest
        assert abs(total - 1.0) < 0.001, f"Weights must sum to 1.0, got {total}"

@dataclass
class LiquidityAnalysis:
    """Complete liquidity analysis results."""
    score: int                    # 0-100 composite score
    grade: LiquidityGrade         # Classification
    components: dict[str, float]  # Individual component scores
    depth: DepthAnalysis          # Orderbook depth details
    max_safe_size: int            # Max order within 3c slippage
    warnings: list[str]           # Risk warnings

def liquidity_score(
    market: Market,
    orderbook: Orderbook,
    weights: LiquidityWeights | None = None,
) -> LiquidityAnalysis:
    """
    Comprehensive liquidity analysis for a market.

    Components:
    - Spread (30%): Tighter = better. 1c = 100, 20c+ = 0
    - Depth (30%): Weighted contracts within 10c. 1000+ = 100
    - Volume 24h (20%): Trading activity. 10k+ = 100
    - Open Interest (20%): Outstanding contracts. 5k+ = 100

    Returns:
        LiquidityAnalysis with score, grade, and details
    """
    w = weights or LiquidityWeights()
    warnings = []

    # Spread component: 1c = 100, 20c = 0
    spread = orderbook.spread or 100
    spread_score = max(0, 100 - spread * 5)
    if spread > 10:
        warnings.append(f"Wide spread ({spread}c) will eat edge")

    # Depth component: weighted score, 1000 = 100
    depth = orderbook_depth_score(orderbook, radius_cents=10)
    depth_score = min(100, depth.weighted_score / 10)
    if depth.total_contracts < 100:
        warnings.append(f"Thin book ({depth.total_contracts} contracts visible)")

    # Imbalance warning
    if abs(depth.imbalance_ratio) > 0.5:
        side = "YES" if depth.imbalance_ratio > 0 else "NO"
        warnings.append(f"Orderbook imbalance: {side} side has more depth")

    # Volume component: 10k/day = 100
    volume_score = min(100, market.volume_24h / 100)
    if market.volume_24h < 1000:
        warnings.append(f"Low volume ({market.volume_24h}/24h)")

    # Open interest component: 5k = 100
    oi_score = min(100, market.open_interest / 50)

    # Composite score
    score = int(
        spread_score * w.spread +
        depth_score * w.depth +
        volume_score * w.volume +
        oi_score * w.open_interest
    )

    # Grade classification
    if score >= 76:
        grade = LiquidityGrade.LIQUID
    elif score >= 51:
        grade = LiquidityGrade.MODERATE
    elif score >= 26:
        grade = LiquidityGrade.THIN
    else:
        grade = LiquidityGrade.ILLIQUID
        warnings.append("ILLIQUID: Consider skipping this market")

    # Calculate max safe order size (3c slippage tolerance)
    max_safe = max_safe_order_size(orderbook, "yes", max_slippage_cents=3)

    return LiquidityAnalysis(
        score=score,
        grade=grade,
        components={
            "spread": spread_score,
            "depth": depth_score,
            "volume": volume_score,
            "open_interest": oi_score,
        },
        depth=depth,
        max_safe_size=max_safe,
        warnings=warnings,
    )
```

### 5. Max Safe Order Size

**Definition**: Largest order that won't exceed slippage tolerance.

```python
def max_safe_order_size(
    orderbook: Orderbook,
    side: Literal["yes", "no"],
    max_slippage_cents: int = 3,
) -> int:
    """
    Calculate largest order within slippage tolerance.

    Binary search to find maximum quantity where slippage <= threshold.

    Args:
        orderbook: Current orderbook
        side: Which side to buy
        max_slippage_cents: Maximum acceptable slippage

    Returns:
        Maximum contracts that can be bought within slippage limit
    """
    # BUY-side max size is limited by ask-side depth.
    # Buy YES consumes implied YES asks from NO bids; buy NO consumes implied NO asks from YES bids.
    levels = _invert_levels(orderbook.no) if side == "yes" else _invert_levels(orderbook.yes)
    max_possible = sum(qty for _, qty in levels)

    if max_possible == 0:
        return 0

    # Binary search for max size
    low, high = 1, max_possible
    result = 0

    while low <= high:
        mid = (low + high) // 2
        estimate = estimate_slippage(orderbook, side, "buy", mid)

        # Unfillable sizes are unsafe even if "slippage" looks small.
        if estimate.remaining_unfilled > 0:
            high = mid - 1
            continue

        if estimate.slippage_cents <= max_slippage_cents:
            result = mid
            low = mid + 1
        else:
            high = mid - 1

    return result
```

### 6. Execution Timing Optimizer

**Definition**: Recommend optimal execution windows based on typical liquidity patterns.

```python
@dataclass
class ExecutionWindow:
    """Recommended execution timing."""
    optimal_hours_utc: list[int]  # Best hours to execute
    avoid_hours_utc: list[int]    # Worst hours
    reasoning: str

def suggest_execution_timing(
    market: Market,
) -> ExecutionWindow:
    """
    Suggest optimal execution timing for a market.

    Kalshi follows US trading patterns. Liquidity is typically:
    - Highest: 9am-5pm ET (13:00-21:00 UTC)
    - Lowest: Overnight and weekends

    Returns:
        ExecutionWindow with timing recommendations
    """
    # Kalshi is US-based, peak hours during US market hours
    optimal = list(range(13, 22))  # 13:00-21:00 UTC = 9am-5pm ET
    avoid = list(range(0, 12))     # Overnight UTC

    return ExecutionWindow(
        optimal_hours_utc=optimal,
        avoid_hours_utc=avoid,
        reasoning="Kalshi liquidity peaks during US market hours (9am-5pm ET)"
    )
```

## Rate Limit & Performance Strategy

**CRITICAL:** Liquidity analysis requires fetching full orderbooks (`GET /markets/{ticker}/orderbook`). This endpoint is expensive and rate-limited.

1.  **Caching Policy:**
    *   Do NOT fetch orderbook for every single trade check if trading frequently.
    *   Cache orderbook analysis for 5-15 seconds for active markets.
    *   Use `lru_cache` for `liquidity_score` calculations if input objects are immutable.

2.  **Depth Limiting:**
    *   Always request `depth=25` (or similar) instead of full book (`depth=0`) unless deep analysis is required.
    *   This reduces payload size and parsing time.

3.  **High-Frequency Mode (WebSocket):**
    *   For agents trading >10 times/minute, **WebSocket is mandatory**.
    *   Subscribe to `orderbook_delta` and maintain a local orderbook replica.
    *   Run analysis against the local replica (0 API cost).

---

## Integration Points

### 1. CLI Command: `kalshi market liquidity TICKER`

```bash
$ kalshi market liquidity KXBTC-26JAN15-T100000

Liquidity Analysis: KXBTC-26JAN15-T100000
═══════════════════════════════════════════

Score:        72/100 (MODERATE)
Grade:        ████████████████████░░░░░░░░░░ MODERATE

Components:
  Spread:       85/100 (3c spread)
  Depth:        65/100 (823 weighted contracts)
  Volume 24h:   70/100 (7,012 contracts)
  Open Interest: 68/100 (3,421 contracts)

Orderbook Depth (within 10c of mid):
  YES side: 412 contracts
  NO side:  411 contracts
  Imbalance: +0.2% (balanced)

Order Size Analysis:
  ┌──────────┬─────────────┬───────────────┐
  │ Quantity │ Slippage    │ Avg Fill      │
  ├──────────┼─────────────┼───────────────┤
  │ 10       │ 0.1c (0.2%) │ 47.1c         │
  │ 50       │ 0.8c (1.7%) │ 47.8c         │
  │ 100      │ 2.1c (4.5%) │ 49.1c         │
  │ 500      │ 8.5c (18%)  │ 55.5c         │
  └──────────┴─────────────┴───────────────┘

Max Safe Size (3c slippage): 142 contracts

Execution Timing:
  Optimal: 9am-5pm ET (peak US hours)
  Avoid:   Overnight (low liquidity)

⚠️ Warnings: None
```

### 2. Scanner Integration: `--min-liquidity`

```bash
# Only show markets with liquidity score >= 50
$ kalshi scan opportunities --filter close-race --min-liquidity 50

# Show liquidity alongside other metrics
$ kalshi scan opportunities --show-liquidity
```

### 3. Research Workflow Integration

When recommending trades:
```
Edge Analysis: KXBTC-26JAN15-T100000
─────────────────────────────────────
Your estimate: 55% | Market: 47% | Edge: +8%
Expected value: +6.2c per contract

⚠️ LIQUIDITY WARNING:
  Score: 38/100 (THIN)
  Max safe size: 23 contracts
  Recommendation: Reduce position size or skip

Suggested action:
  Instead of 100 contracts, consider 20-25 contracts
  Expected slippage at 25: 1.2c (acceptable)
  Expected slippage at 100: 6.8c (would eat most of edge)
```

### 4. Pre-Trade Confirmation

```python
async def create_order_with_liquidity_check(
    client: KalshiClient,
    ticker: str,
    side: str,
    action: str,
    count: int,
    price: int,
    max_slippage_pct: float = 5.0,
) -> OrderResponse:
    """Create order with liquidity safety check."""

    # Fetch orderbook and analyze
    orderbook = await client.get_orderbook(ticker)
    analysis = liquidity_score(await client.get_market(ticker), orderbook)

    # Estimate slippage for this order
    slippage = estimate_slippage(orderbook, side, action, count)

    if slippage.slippage_pct > max_slippage_pct:
        raise LiquidityError(
            f"Order would incur {slippage.slippage_pct:.1f}% slippage "
            f"(max allowed: {max_slippage_pct}%). "
            f"Consider reducing to {analysis.max_safe_size} contracts."
        )

    if analysis.grade == LiquidityGrade.ILLIQUID:
        logger.warning(
            "Trading in ILLIQUID market",
            ticker=ticker,
            score=analysis.score,
            warnings=analysis.warnings,
        )

    return await client.create_order(
        ticker=ticker,
        side=side,
        action=action,
        count=count,
        price=price,
    )
```

---

## Implementation Plan

### Phase 1: Core Metrics (Week 1)

1. Create `src/kalshi_research/analysis/liquidity.py`:
   - [ ] `DepthAnalysis` dataclass
   - [ ] `SlippageEstimate` dataclass
   - [ ] `LiquidityAnalysis` dataclass
   - [ ] `LiquidityGrade` enum
   - [ ] `orderbook_depth_score()` function
   - [ ] `estimate_slippage()` function
   - [ ] `liquidity_score()` function
   - [ ] `max_safe_order_size()` function

2. Add comprehensive tests:
   - [ ] Mock orderbooks with various depth profiles
   - [ ] Edge cases (empty book, single level, imbalanced)
   - [ ] Slippage calculation accuracy

### Phase 2: CLI Integration (Week 2)

1. Add CLI command:
   - [ ] `kalshi market liquidity TICKER`
   - [ ] Rich table output with all metrics
   - [ ] Order size analysis table
   - [ ] Warnings display

2. Scanner integration:
   - [ ] `--min-liquidity` filter
   - [ ] `--show-liquidity` column option

### Phase 3: Research Workflow (Week 3)

1. Edge detection enhancement:
   - [ ] Include liquidity in edge recommendations
   - [ ] Position sizing based on liquidity
   - [ ] "Adjust size" suggestions

2. Pre-trade checks:
   - [ ] Slippage estimation before order
   - [ ] Warning for illiquid markets
   - [ ] Max safe size enforcement (optional)

### Phase 4: Historical Analysis (Future)

1. Liquidity tracking:
   - [ ] Store orderbook snapshots
   - [ ] Analyze liquidity patterns over time
   - [ ] Time-of-day optimization

---

## Acceptance Criteria

- [x] `OrderbookAnalyzer` class with all core metrics
- [x] `liquidity_score()` returns 0-100 with grade classification
- [x] `estimate_slippage()` accurately walks orderbook
- [x] `max_safe_order_size()` binary searches for safe size
- [x] CLI command: `kalshi market liquidity TICKER` with rich output
- [x] Scanner filter: `--min-liquidity N` works correctly
- [x] Research recommendations include liquidity warnings
- [x] Pre-trade slippage check available
- [x] Comprehensive unit tests (>90% coverage)
- [x] Documentation with real examples

---

## Testing Strategy

### Unit Tests

```python
class TestOrderbookDepth:
    def test_empty_orderbook_returns_zero(self):
        orderbook = Orderbook(yes=None, no=None)
        depth = orderbook_depth_score(orderbook)
        assert depth.total_contracts == 0
        assert depth.weighted_score == 0.0

    def test_single_level_scores_correctly(self):
        orderbook = Orderbook(yes=[(50, 100)], no=[(50, 100)])
        depth = orderbook_depth_score(orderbook, radius_cents=10)
        assert depth.total_contracts == 200
        assert depth.weighted_score > 0

    def test_distance_weighting_works(self):
        # Closer to mid should score higher
        close = Orderbook(yes=[(50, 100)], no=[(50, 100)])
        far = Orderbook(yes=[(40, 100)], no=[(60, 100)])
        assert orderbook_depth_score(close).weighted_score > orderbook_depth_score(far).weighted_score

class TestSlippageEstimation:
    def test_small_order_minimal_slippage(self):
        orderbook = Orderbook(yes=[(47, 1000)], no=[(53, 1000)])
        slip = estimate_slippage(orderbook, "yes", "buy", 10)
        assert slip.slippage_cents < 1

    def test_large_order_walks_book(self):
        orderbook = Orderbook(
            yes=[(47, 100), (46, 100), (45, 100)],
            no=[(53, 100), (54, 100), (55, 100)],
        )
        slip = estimate_slippage(orderbook, "yes", "buy", 250)
        assert slip.levels_crossed > 1
        assert slip.slippage_cents > 0

    def test_unfillable_order_reports_remaining(self):
        orderbook = Orderbook(yes=[(50, 50)], no=[(50, 50)])
        slip = estimate_slippage(orderbook, "yes", "buy", 1000)
        assert slip.remaining_unfilled > 0
```

### Integration Tests

```python
@pytest.mark.integration
async def test_real_orderbook_analysis():
    async with KalshiPublicClient() as client:
        markets = await client.get_markets(status="open", limit=10)
        for market in markets:
            orderbook = await client.get_orderbook(market.ticker)
            analysis = liquidity_score(market, orderbook)

            assert 0 <= analysis.score <= 100
            assert analysis.grade in LiquidityGrade
            assert analysis.max_safe_size >= 0
```

---

## References

### Official Kalshi API Documentation

- [Get Market Orderbook](https://docs.kalshi.com/api-reference/market/get-market-orderbook) - REST endpoint, `depth` parameter
- [Get Market](https://docs.kalshi.com/api-reference/market/get-market) - `liquidity_dollars`, `open_interest`, `volume_24h`
- [Orderbook Updates WebSocket](https://docs.kalshi.com/websockets/orderbook-updates) - Real-time `orderbook_delta` channel
- [API Changelog](https://docs.kalshi.com/changelog) - Field deprecations, breaking changes
- [The Orderbook (Help Center)](https://help.kalshi.com/markets/markets-101/the-orderbook) - Binary market mechanics

### Academic & Industry Research

- [The Economics of the Kalshi Prediction Market (UCD 2025)](https://www.ucd.ie/economics/t4media/WP2025_19.pdf) - Favorite-longshot bias, volume statistics
- [CME Group: Reassessing Liquidity Beyond Order Book Depth](https://www.cmegroup.com/articles/2025/reassessing-liquidity-beyond-order-book-depth.html) - Price impact models
- [Amberdata: Temporal Patterns in Market Depth](https://blog.amberdata.io/the-rhythm-of-liquidity-temporal-patterns-in-market-depth) - Time-of-day liquidity variation
- [Altrady: Liquidity and Order Book Depth](https://www.altrady.com/crypto-trading/fundamental-analysis/liquidity-order-book-depth) - Distance weighting

### Prediction Market Specific

- [Metamask: Prediction Market Concepts](https://metamask.io/news/prediction-markets-concepts-terminology) - Market making economics
- [Polymarket Deep Dive (BUVCG)](https://medium.com/buvcg-research/polymarket-deep-dive-06afa8c9a02b) - CLOB vs AMM liquidity
- [Predchain: How Prediction Markets Set Prices](https://docs.predchain.com/blog/how-prediction-markets-set-prices-complete-guide-to-market-dynamics) - Binary options mechanics

### Internal References

- `src/kalshi_research/api/models/orderbook.py` - Current orderbook model
- `src/kalshi_research/analysis/edge.py` - Edge detection (uses spread)
- `src/kalshi_research/analysis/scanner.py` - Market scanner
- `docs/_vendor-docs/kalshi-api-reference.md` - Our vendor docs mirror

---

## Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| Orderbook refresh frequency? | On-demand via REST; WebSocket `orderbook_delta` available for real-time |
| Historical liquidity tracking? | Phase 4 - store snapshots in database |
| Cross-market liquidity? | Future enhancement for event-level analysis |
| Dynamic position sizing? | Implemented via `max_safe_order_size()` |
| What does Kalshi's `liquidity_dollars` represent? | "Current offer value" - simple aggregate (REMAINS in API, replaces deprecated `liquidity`) |
| API depth limiting? | Use `depth` parameter (0-100) on REST endpoint for performance |
| Real-time updates? | WebSocket `orderbook_delta` channel with snapshot + incremental deltas |

---

## Appendix: Kalshi vs Traditional Market Liquidity

### Why Kalshi Needs Custom Metrics

Traditional liquidity metrics (like Amihud illiquidity ratio) assume:
- Continuous price movements
- Large trading volumes
- Professional market makers

Kalshi has:
- Discrete 1-cent price levels
- Relatively thin volumes (top decile avg $526k)
- Organic peer-to-peer liquidity

### The "Trapped Position" Problem

Unlike stocks where you can always sell (at some price), Kalshi positions can become truly trapped:
- If orderbook is empty on your side, you literally cannot exit
- As expiration approaches, liquidity can vanish
- News events can cause instant liquidity evaporation

This makes **pre-trade liquidity analysis** essential, not optional.
