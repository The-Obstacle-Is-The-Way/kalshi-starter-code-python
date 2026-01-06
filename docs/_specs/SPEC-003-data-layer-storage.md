# SPEC-003: Data Layer & Storage

**Status:** Draft
**Priority:** P1 (Required for historical analysis)
**Estimated Complexity:** Medium
**Dependencies:** SPEC-001, SPEC-002

---

## 1. Overview

Implement a local data storage layer for persisting Kalshi market data, enabling historical analysis, backtesting, and tracking probability changes over time.

### 1.1 Goals

- SQLite database for structured market data storage
- Efficient schema for time-series price/probability data
- Data fetching scheduler for automated snapshots
- Export capabilities (CSV, JSON, Parquet)
- Query interface for analysis

### 1.2 Non-Goals

- Cloud database deployment
- Real-time streaming storage (WebSocket data)
- Multi-user access patterns
- Data warehousing at scale

---

## 2. Data Requirements

### 2.1 What We Need to Store

| Data Type | Update Frequency | Retention | Use Case |
|-----------|------------------|-----------|----------|
| Market metadata | Once + on change | Forever | Reference data |
| Price snapshots | Every 5-15 min | 1 year | Probability tracking |
| Orderbook snapshots | Hourly | 30 days | Liquidity analysis |
| Trade history | Daily batch | Forever | Volume analysis |
| Event outcomes | On settlement | Forever | Calibration scoring |
| Candlesticks | Daily | Forever | Historical prices |

### 2.2 Data Volumes (Estimates)

- ~3,000 active markets at any time
- ~500 events
- Price snapshots: 3000 markets × 96 snapshots/day × 365 days = ~100M rows/year
- Storage: ~5-10 GB/year (SQLite handles this fine)

---

## 3. Technical Specification

### 3.1 Module Structure

```
src/kalshi_research/
├── data/
│   ├── __init__.py
│   ├── database.py         # SQLite connection management
│   ├── models.py           # SQLAlchemy ORM models
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── markets.py      # Market data repository
│   │   ├── prices.py       # Price snapshot repository
│   │   ├── orderbooks.py   # Orderbook repository
│   │   └── trades.py       # Trade repository
│   ├── fetcher.py          # Data fetching orchestrator
│   ├── scheduler.py        # Scheduled data collection
│   └── export.py           # CSV/JSON/Parquet export
data/
├── kalshi.db               # Main SQLite database
├── exports/                # Exported data files
└── backups/                # Database backups
```

### 3.2 Database Schema

```sql
-- Markets (reference data)
CREATE TABLE markets (
    ticker TEXT PRIMARY KEY,
    event_ticker TEXT NOT NULL,
    series_ticker TEXT NOT NULL,
    title TEXT NOT NULL,
    subtitle TEXT,
    status TEXT NOT NULL,  -- open, closed, settled
    result TEXT,           -- yes, no, void, null if unsettled

    open_time TIMESTAMP NOT NULL,
    close_time TIMESTAMP NOT NULL,
    expiration_time TIMESTAMP NOT NULL,

    -- Denormalized for query convenience
    category TEXT,
    subcategory TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (event_ticker) REFERENCES events(ticker)
);

CREATE INDEX idx_markets_status ON markets(status);
CREATE INDEX idx_markets_event ON markets(event_ticker);
CREATE INDEX idx_markets_expiration ON markets(expiration_time);

-- Events (reference data)
CREATE TABLE events (
    ticker TEXT PRIMARY KEY,
    series_ticker TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    category TEXT,
    mutually_exclusive BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Price Snapshots (time series - main analytical table)
CREATE TABLE price_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    snapshot_time TIMESTAMP NOT NULL,

    yes_bid INTEGER NOT NULL,      -- cents (1-99)
    yes_ask INTEGER NOT NULL,
    no_bid INTEGER NOT NULL,
    no_ask INTEGER NOT NULL,
    last_price INTEGER,

    volume INTEGER NOT NULL,
    volume_24h INTEGER NOT NULL,
    open_interest INTEGER NOT NULL,
    liquidity INTEGER NOT NULL,

    -- Calculated fields
    midpoint REAL GENERATED ALWAYS AS ((yes_bid + yes_ask) / 2.0) STORED,
    spread INTEGER GENERATED ALWAYS AS (yes_ask - yes_bid) STORED,

    FOREIGN KEY (ticker) REFERENCES markets(ticker),
    UNIQUE(ticker, snapshot_time)
);

CREATE INDEX idx_snapshots_ticker_time ON price_snapshots(ticker, snapshot_time DESC);
CREATE INDEX idx_snapshots_time ON price_snapshots(snapshot_time DESC);

-- Orderbook Snapshots (for liquidity analysis)
CREATE TABLE orderbook_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    snapshot_time TIMESTAMP NOT NULL,
    depth INTEGER NOT NULL,         -- number of levels

    -- Store as JSON for flexibility
    yes_bids JSON NOT NULL,         -- [{"price": 45, "quantity": 100}, ...]
    yes_asks JSON NOT NULL,

    -- Calculated summary stats
    total_bid_volume INTEGER,
    total_ask_volume INTEGER,
    best_bid INTEGER,
    best_ask INTEGER,

    FOREIGN KEY (ticker) REFERENCES markets(ticker),
    UNIQUE(ticker, snapshot_time)
);

CREATE INDEX idx_orderbook_ticker_time ON orderbook_snapshots(ticker, snapshot_time DESC);

-- Trade History
CREATE TABLE trades (
    trade_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    trade_time TIMESTAMP NOT NULL,
    price INTEGER NOT NULL,
    count INTEGER NOT NULL,         -- contracts
    taker_side TEXT NOT NULL,       -- yes, no

    FOREIGN KEY (ticker) REFERENCES markets(ticker)
);

CREATE INDEX idx_trades_ticker_time ON trades(ticker, trade_time DESC);
CREATE INDEX idx_trades_time ON trades(trade_time DESC);

-- Candlesticks (OHLC data)
CREATE TABLE candlesticks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    interval_minutes INTEGER NOT NULL,  -- 1, 5, 15, 60, 1440

    open_price INTEGER NOT NULL,
    high_price INTEGER NOT NULL,
    low_price INTEGER NOT NULL,
    close_price INTEGER NOT NULL,
    volume INTEGER NOT NULL,

    FOREIGN KEY (ticker) REFERENCES markets(ticker),
    UNIQUE(ticker, period_start, interval_minutes)
);

CREATE INDEX idx_candles_ticker_time ON candlesticks(ticker, period_start DESC);

-- Settlement Outcomes (for calibration)
CREATE TABLE settlements (
    ticker TEXT PRIMARY KEY,
    event_ticker TEXT NOT NULL,
    settled_at TIMESTAMP NOT NULL,
    result TEXT NOT NULL,           -- yes, no, void

    -- Final price before settlement
    final_yes_price INTEGER,
    final_no_price INTEGER,

    -- Payout per contract (in cents)
    yes_payout INTEGER,
    no_payout INTEGER,

    FOREIGN KEY (ticker) REFERENCES markets(ticker)
);

CREATE INDEX idx_settlements_event ON settlements(event_ticker);
CREATE INDEX idx_settlements_time ON settlements(settled_at DESC);

-- Data collection metadata
CREATE TABLE collection_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_type TEXT NOT NULL,         -- full_snapshot, price_update, trade_sync
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    markets_processed INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    error_details JSON
);
```

### 3.3 SQLAlchemy Models

```python
# src/kalshi_research/data/models.py
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, JSON,
    ForeignKey, Index, text
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Market(Base):
    __tablename__ = "markets"

    ticker = Column(String, primary_key=True)
    event_ticker = Column(String, ForeignKey("events.ticker"), nullable=False)
    series_ticker = Column(String, nullable=False)
    title = Column(String, nullable=False)
    subtitle = Column(String)
    status = Column(String, nullable=False)
    result = Column(String)

    open_time = Column(DateTime, nullable=False)
    close_time = Column(DateTime, nullable=False)
    expiration_time = Column(DateTime, nullable=False)

    category = Column(String)
    subcategory = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    event = relationship("Event", back_populates="markets")
    price_snapshots = relationship("PriceSnapshot", back_populates="market")
    settlement = relationship("Settlement", back_populates="market", uselist=False)


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, ForeignKey("markets.ticker"), nullable=False)
    snapshot_time = Column(DateTime, nullable=False)

    yes_bid = Column(Integer, nullable=False)
    yes_ask = Column(Integer, nullable=False)
    no_bid = Column(Integer, nullable=False)
    no_ask = Column(Integer, nullable=False)
    last_price = Column(Integer)

    volume = Column(Integer, nullable=False)
    volume_24h = Column(Integer, nullable=False)
    open_interest = Column(Integer, nullable=False)
    liquidity = Column(Integer, nullable=False)

    # Relationships
    market = relationship("Market", back_populates="price_snapshots")

    __table_args__ = (
        Index("idx_snapshots_ticker_time", "ticker", "snapshot_time"),
    )

    @property
    def midpoint(self) -> float:
        return (self.yes_bid + self.yes_ask) / 2.0

    @property
    def spread(self) -> int:
        return self.yes_ask - self.yes_bid

    @property
    def implied_probability(self) -> float:
        """Convert midpoint to probability (0-1 scale)."""
        return self.midpoint / 100.0


class Settlement(Base):
    __tablename__ = "settlements"

    ticker = Column(String, ForeignKey("markets.ticker"), primary_key=True)
    event_ticker = Column(String, nullable=False)
    settled_at = Column(DateTime, nullable=False)
    result = Column(String, nullable=False)  # yes, no, void

    final_yes_price = Column(Integer)
    final_no_price = Column(Integer)
    yes_payout = Column(Integer)
    no_payout = Column(Integer)

    # Relationships
    market = relationship("Market", back_populates="settlement")
```

### 3.4 Repository Pattern

```python
# src/kalshi_research/data/repositories/prices.py
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

from ..models import PriceSnapshot, Market


class PriceRepository:
    """Repository for price snapshot data operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_snapshot(self, snapshot: PriceSnapshot) -> None:
        """Save a single price snapshot."""
        self.session.add(snapshot)
        await self.session.commit()

    async def save_snapshots_batch(self, snapshots: list[PriceSnapshot]) -> int:
        """Bulk insert price snapshots. Returns count inserted."""
        self.session.add_all(snapshots)
        await self.session.commit()
        return len(snapshots)

    async def get_latest(self, ticker: str) -> Optional[PriceSnapshot]:
        """Get most recent snapshot for a market."""
        stmt = (
            select(PriceSnapshot)
            .where(PriceSnapshot.ticker == ticker)
            .order_by(PriceSnapshot.snapshot_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_history(
        self,
        ticker: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> list[PriceSnapshot]:
        """Get historical snapshots for a market."""
        stmt = select(PriceSnapshot).where(PriceSnapshot.ticker == ticker)

        if start_time:
            stmt = stmt.where(PriceSnapshot.snapshot_time >= start_time)
        if end_time:
            stmt = stmt.where(PriceSnapshot.snapshot_time <= end_time)

        stmt = stmt.order_by(PriceSnapshot.snapshot_time.desc()).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_history_as_dataframe(
        self,
        ticker: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Get price history as pandas DataFrame for analysis."""
        snapshots = await self.get_history(ticker, start_time, end_time, limit=100000)

        if not snapshots:
            return pd.DataFrame()

        data = [
            {
                "time": s.snapshot_time,
                "yes_bid": s.yes_bid,
                "yes_ask": s.yes_ask,
                "midpoint": s.midpoint,
                "spread": s.spread,
                "volume": s.volume,
                "volume_24h": s.volume_24h,
                "open_interest": s.open_interest,
                "implied_prob": s.implied_probability,
            }
            for s in snapshots
        ]

        df = pd.DataFrame(data)
        df.set_index("time", inplace=True)
        df.sort_index(inplace=True)
        return df

    async def get_probability_at_time(
        self,
        ticker: str,
        target_time: datetime,
    ) -> Optional[float]:
        """Get implied probability at a specific point in time."""
        stmt = (
            select(PriceSnapshot)
            .where(PriceSnapshot.ticker == ticker)
            .where(PriceSnapshot.snapshot_time <= target_time)
            .order_by(PriceSnapshot.snapshot_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        snapshot = result.scalar_one_or_none()

        if snapshot:
            return snapshot.implied_probability
        return None

    async def get_markets_by_price_change(
        self,
        hours: int = 24,
        min_change_cents: int = 5,
    ) -> list[dict]:
        """Find markets with significant price movement."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Get current and past prices
        stmt = """
        WITH current_prices AS (
            SELECT ticker, yes_bid, yes_ask,
                   (yes_bid + yes_ask) / 2.0 as current_mid
            FROM price_snapshots ps1
            WHERE snapshot_time = (
                SELECT MAX(snapshot_time)
                FROM price_snapshots ps2
                WHERE ps2.ticker = ps1.ticker
            )
        ),
        past_prices AS (
            SELECT ticker,
                   (yes_bid + yes_ask) / 2.0 as past_mid
            FROM price_snapshots ps1
            WHERE snapshot_time = (
                SELECT MAX(snapshot_time)
                FROM price_snapshots ps2
                WHERE ps2.ticker = ps1.ticker
                AND ps2.snapshot_time <= :cutoff
            )
        )
        SELECT
            c.ticker,
            c.current_mid,
            p.past_mid,
            (c.current_mid - p.past_mid) as change
        FROM current_prices c
        JOIN past_prices p ON c.ticker = p.ticker
        WHERE ABS(c.current_mid - p.past_mid) >= :min_change
        ORDER BY ABS(c.current_mid - p.past_mid) DESC
        """

        result = await self.session.execute(
            text(stmt),
            {"cutoff": cutoff, "min_change": min_change_cents}
        )
        return [dict(row._mapping) for row in result.fetchall()]
```

### 3.5 Data Fetcher

```python
# src/kalshi_research/data/fetcher.py
from datetime import datetime
from typing import Optional
import structlog

from ..api import KalshiPublicClient
from .database import get_async_session
from .models import Market, PriceSnapshot, Event
from .repositories.markets import MarketRepository
from .repositories.prices import PriceRepository

logger = structlog.get_logger()


class DataFetcher:
    """Orchestrates data fetching from Kalshi API to local storage."""

    def __init__(
        self,
        client: Optional[KalshiPublicClient] = None,
    ):
        self.client = client or KalshiPublicClient()

    async def fetch_all_markets(self) -> int:
        """
        Fetch and store all current markets.

        Returns:
            Number of markets processed
        """
        count = 0
        async with get_async_session() as session:
            repo = MarketRepository(session)

            async for api_market in self.client.get_all_markets():
                market = Market(
                    ticker=api_market.ticker,
                    event_ticker=api_market.event_ticker,
                    series_ticker=api_market.series_ticker,
                    title=api_market.title,
                    subtitle=api_market.subtitle,
                    status=api_market.status.value,
                    result=api_market.result.value if api_market.result else None,
                    open_time=api_market.open_time,
                    close_time=api_market.close_time,
                    expiration_time=api_market.expiration_time,
                )
                await repo.upsert(market)
                count += 1

                if count % 100 == 0:
                    logger.info("Fetched markets", count=count)

        logger.info("Completed market fetch", total=count)
        return count

    async def snapshot_all_prices(self) -> int:
        """
        Take price snapshot of all open markets.

        Returns:
            Number of snapshots saved
        """
        snapshot_time = datetime.utcnow()
        snapshots = []

        async with get_async_session() as session:
            async for api_market in self.client.get_all_markets(status="open"):
                snapshot = PriceSnapshot(
                    ticker=api_market.ticker,
                    snapshot_time=snapshot_time,
                    yes_bid=api_market.yes_bid,
                    yes_ask=api_market.yes_ask,
                    no_bid=api_market.no_bid,
                    no_ask=api_market.no_ask,
                    last_price=api_market.last_price,
                    volume=api_market.volume,
                    volume_24h=api_market.volume_24h,
                    open_interest=api_market.open_interest,
                    liquidity=api_market.liquidity,
                )
                snapshots.append(snapshot)

            # Batch insert
            repo = PriceRepository(session)
            count = await repo.save_snapshots_batch(snapshots)

        logger.info("Price snapshot complete", count=count, time=snapshot_time)
        return count

    async def fetch_market_history(
        self,
        ticker: str,
        days: int = 30,
    ) -> int:
        """
        Fetch historical candlestick data for a market.

        Returns:
            Number of candlesticks saved
        """
        # Implementation for backfilling historical data
        pass
```

### 3.6 Scheduler

```python
# src/kalshi_research/data/scheduler.py
import asyncio
from datetime import datetime
from typing import Callable, Awaitable
import structlog

logger = structlog.get_logger()


class DataScheduler:
    """Simple async scheduler for data collection tasks."""

    def __init__(self):
        self.tasks: list[asyncio.Task] = []
        self.running = False

    async def schedule_interval(
        self,
        name: str,
        func: Callable[[], Awaitable],
        interval_seconds: int,
    ) -> None:
        """Schedule a function to run at fixed intervals."""

        async def runner():
            while self.running:
                try:
                    logger.info("Running scheduled task", task=name)
                    await func()
                except Exception as e:
                    logger.error("Scheduled task failed", task=name, error=str(e))

                await asyncio.sleep(interval_seconds)

        task = asyncio.create_task(runner())
        self.tasks.append(task)

    async def start(self):
        """Start the scheduler."""
        self.running = True
        logger.info("Scheduler started")

    async def stop(self):
        """Stop all scheduled tasks."""
        self.running = False
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        logger.info("Scheduler stopped")


# Example usage
async def run_data_collection():
    """Run continuous data collection."""
    from .fetcher import DataFetcher

    fetcher = DataFetcher()
    scheduler = DataScheduler()

    # Schedule tasks
    await scheduler.schedule_interval(
        "price_snapshots",
        fetcher.snapshot_all_prices,
        interval_seconds=900,  # Every 15 minutes
    )

    await scheduler.schedule_interval(
        "market_sync",
        fetcher.fetch_all_markets,
        interval_seconds=3600,  # Every hour
    )

    await scheduler.start()

    # Run until interrupted
    try:
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        await scheduler.stop()
```

---

## 4. Implementation Tasks

### 4.1 Phase 1: Database Setup

- [ ] Create SQLite database schema
- [ ] Implement SQLAlchemy models
- [ ] Set up Alembic for migrations
- [ ] Write database connection management

### 4.2 Phase 2: Repositories

- [ ] Implement MarketRepository
- [ ] Implement PriceRepository
- [ ] Implement OrderbookRepository
- [ ] Implement TradeRepository
- [ ] Implement SettlementRepository
- [ ] Write unit tests for all repositories

### 4.3 Phase 3: Data Fetching

- [ ] Implement DataFetcher class
- [ ] Add market sync functionality
- [ ] Add price snapshot functionality
- [ ] Add trade history sync
- [ ] Add candlestick backfill

### 4.4 Phase 4: Scheduler & Export

- [ ] Implement async scheduler
- [ ] Add CLI commands for data collection
- [ ] Implement CSV export
- [ ] Implement JSON export
- [ ] Implement Parquet export (for pandas)

---

## 5. Acceptance Criteria

1. **Storage**: Can store 100k+ price snapshots without performance issues
2. **Queries**: Historical price query returns in <100ms
3. **Sync**: Can sync all markets in <5 minutes
4. **Snapshots**: Can snapshot all open market prices in <2 minutes
5. **Export**: Can export market history to CSV/Parquet
6. **Reliability**: Handles API failures gracefully with retries

---

## 6. CLI Commands

```bash
# Initialize database
kalshi data init

# Sync all markets
kalshi data sync-markets

# Take price snapshot
kalshi data snapshot

# Run continuous collection
kalshi data collect --interval 15m

# Export data
kalshi data export --ticker KXBTC-24DEC31-T100000 --format parquet

# Show database stats
kalshi data stats
```

---

## 7. Future Considerations

- Add PostgreSQL support for production deployment
- Implement data partitioning for large datasets
- Add data quality checks and anomaly detection
- Consider TimescaleDB for time-series optimization
- Add backup/restore utilities
