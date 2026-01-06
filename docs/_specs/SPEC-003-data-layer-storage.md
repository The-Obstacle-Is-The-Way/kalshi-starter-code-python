# SPEC-003: Data Layer & Storage

**Status:** Draft
**Priority:** P1 (Required for historical analysis)
**Estimated Complexity:** Medium
**Dependencies:** SPEC-001, SPEC-002

---

## 1. Overview

Implement a local data storage layer for persisting Kalshi market data, enabling historical analysis, backtesting, and tracking probability changes over time.

### 1.1 Goals

- SQLite database for structured market data storage (Transaction Layer)
- **DuckDB Integration:** Efficient OLAP for analytical queries and large history
- Data fetching scheduler for automated snapshots
- Export capabilities (Parquet/CSV) for analysis
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
- **Strategy:** SQLite for recent/hot data and transaction integrity. Offload to DuckDB/Parquet for deep history and analytics.

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
│   └── export.py           # DuckDB/Parquet export
data/
├── kalshi.db               # Main SQLite database
├── analytics.duckdb        # Analytical database (optional)
├── exports/                # Exported Parquet files
└── backups/                # Database backups
```

### 3.2 Database Schema

```sql
-- Markets (reference data)
-- Note: API status values are: active, closed, determined, finalized
-- Filter params use different values: unopened, open, closed, settled
CREATE TABLE markets (
    ticker TEXT PRIMARY KEY,
    event_ticker TEXT NOT NULL,
    series_ticker TEXT,    -- May be NULL (not always in API response)
    title TEXT NOT NULL,
    subtitle TEXT,
    status TEXT NOT NULL,  -- active, closed, determined, finalized
    result TEXT,           -- yes, no, void, "" (empty string if undetermined)

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
-- Note: API may not return status field for events
CREATE TABLE events (
    ticker TEXT PRIMARY KEY,
    series_ticker TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT,  -- May be NULL if API doesn't provide it
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
```

### 3.3 SQLAlchemy Models (Timezone Aware)

```python
# src/kalshi_research/data/models.py
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Market(Base):
    """Market (reference data) - stores market metadata from Kalshi API."""

    __tablename__ = "markets"

    # NOTE: Use mapped_column (not Column) for mypy --strict compatibility.
    ticker: Mapped[str] = mapped_column(String, primary_key=True)
    event_ticker: Mapped[str] = mapped_column(String, ForeignKey("events.ticker"), nullable=False)
    # Note: series_ticker may not be present in all API responses
    series_ticker: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String, nullable=True)
    # API returns: active, closed, determined, finalized
    status: Mapped[str] = mapped_column(String, nullable=False)
    # Result: yes, no, void, or "" (empty string if undetermined)
    result: Mapped[str | None] = mapped_column(String, nullable=True)

    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expiration_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    category: Mapped[str | None] = mapped_column(String, nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    event: Mapped["Event"] = relationship("Event", back_populates="markets")
    price_snapshots: Mapped[list["PriceSnapshot"]] = relationship(
        "PriceSnapshot", back_populates="market"
    )
    settlement: Mapped["Settlement | None"] = relationship(
        "Settlement", back_populates="market", uselist=False
    )


class PriceSnapshot(Base):
    """Price snapshot for a market at a point in time."""

    __tablename__ = "price_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, ForeignKey("markets.ticker"), nullable=False)
    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    yes_bid: Mapped[int] = mapped_column(Integer, nullable=False)
    yes_ask: Mapped[int] = mapped_column(Integer, nullable=False)
    no_bid: Mapped[int] = mapped_column(Integer, nullable=False)
    no_ask: Mapped[int] = mapped_column(Integer, nullable=False)
    last_price: Mapped[int | None] = mapped_column(Integer, nullable=True)

    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    volume_24h: Mapped[int] = mapped_column(Integer, nullable=False)
    open_interest: Mapped[int] = mapped_column(Integer, nullable=False)
    liquidity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    market: Mapped["Market"] = relationship("Market", back_populates="price_snapshots")

    __table_args__ = (Index("idx_snapshots_ticker_time", "ticker", "snapshot_time"),)

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


class Event(Base):
    """Event containing multiple related markets."""

    __tablename__ = "events"

    ticker: Mapped[str] = mapped_column(String, primary_key=True)
    series_ticker: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    # Note: API may not return status for events, so we allow NULL
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    mutually_exclusive: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    markets: Mapped[list["Market"]] = relationship("Market", back_populates="event")


class Settlement(Base):
    """Settlement outcome for a resolved market."""

    __tablename__ = "settlements"

    ticker: Mapped[str] = mapped_column(String, ForeignKey("markets.ticker"), primary_key=True)
    event_ticker: Mapped[str] = mapped_column(String, nullable=False)
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result: Mapped[str] = mapped_column(String, nullable=False)  # yes, no, void

    final_yes_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_no_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    yes_payout: Mapped[int | None] = mapped_column(Integer, nullable=True)
    no_payout: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    market: Mapped["Market"] = relationship("Market", back_populates="settlement")
```

### 3.4 Repository Pattern

Standard Repository pattern (as in SPEC-003 Draft) but ensuring all datetime objects are timezone-aware (UTC) before persistence.

### 3.5 Alembic Configuration

**alembic/env.py configuration:**
Critical for async SQLAlchemy and autogeneration.

```python
# alembic/env.py (partial)
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import your models
from kalshi_research.data.models import Base

# Set target metadata for autogenerate
target_metadata = Base.metadata

config = context.config

# ... (standard alembic setup) ...

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine and associate a connection with the context."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())
```

### 3.6 Scheduler (Drift Corrected)

```python
# src/kalshi_research/data/scheduler.py
import asyncio
import time
from collections.abc import Awaitable, Callable

import structlog

logger = structlog.get_logger()


class DataScheduler:
    """Async scheduler for data collection tasks with drift correction."""

    def __init__(self) -> None:
        self.tasks: list[asyncio.Task[None]] = []
        self.running = False

    async def schedule_interval(
        self,
        name: str,
        func: Callable[[], Awaitable[None]],
        interval_seconds: int,
    ) -> None:
        """
        Schedule a function to run at fixed intervals.
        Corrects for execution time drift using monotonic clock.
        """

        async def runner() -> None:
            # Use monotonic time for drift correction (safer than wall clock)
            next_run = time.monotonic()
            while True:
                if not self.running:
                    # Allow scheduling before start(); tasks will wait until running = True.
                    await asyncio.sleep(0.1)
                    next_run = time.monotonic()
                    continue

                now = time.monotonic()
                if now >= next_run:
                    try:
                        logger.info("Running scheduled task", task=name)
                        await func()
                    except Exception as e:
                        logger.error("Scheduled task failed", task=name, error=str(e))

                    # Calculate next run time
                    next_run += interval_seconds
                    # If we fell way behind, skip intervals to catch up
                    while next_run <= time.monotonic():
                        next_run += interval_seconds

                # Sleep until next run
                sleep_duration = max(0, next_run - time.monotonic())
                await asyncio.sleep(sleep_duration)

        task = asyncio.create_task(runner())
        self.tasks.append(task)

    async def start(self) -> None:
        """Start the scheduler."""
        self.running = True
        logger.info("Scheduler started")

    async def stop(self) -> None:
        """Stop all scheduled tasks."""
        self.running = False
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        logger.info("Scheduler stopped")
```

### 3.6 Data Export & Analytical Storage

To handle 100M+ rows, we provide utilities to export data to DuckDB or Parquet files.

**Note:** The export uses DuckDB's SQLite extension which is downloaded at runtime via
`INSTALL sqlite;`. This may fail in offline/locked-down CI runners. For CI environments,
either pre-install the extension or skip Parquet export tests.

```python
# src/kalshi_research/data/export.py
from pathlib import Path
import duckdb
import structlog

logger = structlog.get_logger()


def export_to_parquet(sqlite_path: str | Path, output_dir: str | Path) -> None:
    """
    Export SQLite data to partitioned Parquet files for efficient analysis.
    Uses DuckDB for high-performance data transfer.

    Args:
        sqlite_path: Path to SQLite database file
        output_dir: Directory to write Parquet files

    Raises:
        FileNotFoundError: If SQLite database doesn't exist
        ValueError: If paths contain invalid characters
    """
    sqlite_path = Path(sqlite_path).resolve()
    output_dir = Path(output_dir).resolve()

    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    # Validate paths don't contain SQL injection characters
    for path in [sqlite_path, output_dir]:
        if any(c in str(path) for c in ["'", '"', ";", "--"]):
            raise ValueError(f"Invalid characters in path: {path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect()
    try:
        # Install and load SQLite extension
        conn.execute("INSTALL sqlite; LOAD sqlite;")

        # Attach SQLite database (paths are validated above)
        conn.execute(f"ATTACH '{sqlite_path}' AS kalshi (TYPE SQLITE);")

        # Export price snapshots partitioned by month
        snapshots_dir = output_dir / "snapshots"
        conn.execute(f"""
            COPY (
                SELECT *, strftime('%Y-%m', snapshot_time) as month
                FROM kalshi.price_snapshots
            ) TO '{snapshots_dir}'
            (FORMAT PARQUET, PARTITION_BY (month), OVERWRITE_OR_IGNORE true);
        """)

        logger.info("Exported price snapshots to Parquet", path=str(snapshots_dir))
    finally:
        conn.close()
```

---

## 4. Implementation Tasks

### 4.1 Phase 1: Database Setup

- [ ] Create SQLite database schema
- [ ] Implement SQLAlchemy models with timezone-aware datetimes
- [ ] Set up **Alembic** for migrations
- [ ] Write database connection management

### 4.2 Phase 2: Repositories

- [ ] Implement MarketRepository
- [ ] Implement PriceRepository
- [ ] Implement OrderbookRepository
- [ ] Implement TradeRepository
- [ ] Write unit tests for all repositories

### 4.3 Phase 3: Data Fetching

- [ ] Implement DataFetcher class
- [ ] Add market sync functionality
- [ ] Add price snapshot functionality
- [ ] Add trade history sync

### 4.4 Phase 4: Scheduler & Export

- [ ] Implement drift-corrected async scheduler
- [ ] Add CLI commands for data collection
- [ ] Implement DuckDB/Parquet export functionality

---

## 5. Acceptance Criteria

1. **Storage**: Can store 100k+ price snapshots without performance issues
2. **Time Handling**: All stored timestamps are UTC and timezone-aware
3. **Sync**: Can sync all markets in <5 minutes
4. **Reliability**: Scheduler runs indefinitely without drifting
5. **Analytics**: Can export history to Parquet for efficient querying
6. **Recovery**: Handles API failures gracefully with retries

---

## 6. CLI Commands

```bash
# Initialize database
kalshi data init

# Sync all markets
kalshi data sync-markets

# Run continuous collection
kalshi data collect --interval 15m

# Export to Parquet for analysis
kalshi data export-parquet --output ./data/exports
```
