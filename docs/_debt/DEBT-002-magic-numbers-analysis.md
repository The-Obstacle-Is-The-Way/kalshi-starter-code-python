# DEBT-002: Hardcoded Strategy Parameters in Analysis

## Overview
Critical trading thresholds and scanner parameters are hardcoded as default arguments within the logic classes, rather than being centralized in a configuration file or environment variables. This makes it difficult to tune strategies without modifying code.

## Severity: Low (Maintenance / Flexibility)
- **Impact**: Changing a trading strategy parameter (e.g., "what is a 'close' race?") requires code changes and redeployment. It prevents running multiple strategy variants (e.g., "Conservative" vs "Aggressive") without code duplication.

## Locations & True Positives

### `src/kalshi_research/analysis/scanner.py`
These are subjective strategy defaults that should be configurable:
- `close_race_range=(0.40, 0.60)`: Defines the probability window for uncertainty.
- `high_volume_threshold=10000`: Defines arbitrary "high" volume.
- `wide_spread_threshold=5`: Defines arbitrary "wide" spread.

### `src/kalshi_research/analysis/edge.py`
- `min_spread_cents=5`: Subjective filter for liquidity.
- `min_price_move=0.10`: Subjective threshold for "significant" moves.

## False Positives (Verified via Vendor Docs)

The following were investigated and determined **NOT** to be debt. They are **Platform Constants** mandated by the Kalshi Market Model.



1.  **`PriceSnapshot.midpoint` divisor `200.0`**

    *   **Source**: `docs/_vendor-docs/kalshi-api-reference.md` (Section: Orderbook Response Format)

    *   **Citation**: "Binary market math: A YES bid at price X = NO ask at price (100-X)".

    *   **Reasoning**: Midpoint is `(Bid + Ask) / 2`. To normalize to probability (0-1), we divide by 100.

    *   **Math**: `((Bid + Ask) / 2) / 100` = `(Bid + Ask) / 200`.



2.  **Order Price Limits `1-99`**

    *   **Source**: `docs/_vendor-docs/kalshi-api-reference.md` (Section: Orderbook Response Format)

    *   **Citation**: "Integer fields: Cents (0-100 scale)".

    *   **Reasoning**: 0 and 100 are settled states. Valid trading occurs between 1 and 99 cents.



3.  **Page Limits `1000`**

    *   **Source**: `docs/_vendor-docs/kalshi-api-reference.md` (Section: Pagination)

    *   **Citation**: "GET /markets | limit | 1000".



## Plan

### Phase 1: Comments (Partial - In Progress)

Add explanatory comments citing the Vendor Docs next to the "False Positives" to prevent future confusion.

**Status**: Partially complete
- [x] `scanner.py:116-120` - Comment added for 200.0 divisor (2026-01-09)
- [ ] `scanner.py` - Other 200.0 occurrences (reference canonical comment)
- [ ] `client.py:146` - Comment for 1000 page limit
- [ ] `client.py:258` - Comment for 1000 page limit (trades)
- [ ] `client.py:606-607` - Comment for 1-99 price validation

### Phase 2: Configuration

Create `src/kalshi_research/config/analysis.py` with `AnalysisConfig` Pydantic model for the *actual* strategy defaults (0.40, 10000, 5).

### Phase 3: Refactoring

Inject `AnalysisConfig` into `MarketScanner` and `EdgeDetector`.
