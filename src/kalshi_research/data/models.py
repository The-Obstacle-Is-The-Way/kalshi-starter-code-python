"""SQLAlchemy ORM models for Kalshi market data storage."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


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
    markets: Mapped[list[Market]] = relationship("Market", back_populates="event")


class Market(Base):
    """Market (reference data) - stores market metadata from Kalshi API."""

    __tablename__ = "markets"

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
    event: Mapped[Event] = relationship("Event", back_populates="markets")
    price_snapshots: Mapped[list[PriceSnapshot]] = relationship(
        "PriceSnapshot", back_populates="market"
    )
    settlement: Mapped[Settlement | None] = relationship(
        "Settlement", back_populates="market", uselist=False
    )

    __table_args__ = (
        Index("idx_markets_status", "status"),
        Index("idx_markets_event", "event_ticker"),
        Index("idx_markets_expiration", "expiration_time"),
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
    market: Mapped[Market] = relationship("Market", back_populates="price_snapshots")

    __table_args__ = (
        Index("idx_snapshots_ticker_time", "ticker", "snapshot_time"),
        Index("idx_snapshots_time", "snapshot_time"),
    )

    @property
    def midpoint(self) -> float:
        """Calculate midpoint price."""
        return (self.yes_bid + self.yes_ask) / 2.0

    @property
    def spread(self) -> int:
        """Calculate bid-ask spread."""
        return self.yes_ask - self.yes_bid

    @property
    def implied_probability(self) -> float:
        """Convert midpoint to probability (0-1 scale)."""
        return self.midpoint / 100.0


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
    market: Mapped[Market] = relationship("Market", back_populates="settlement")


class TrackedItem(Base):
    """A market or event being tracked for news collection."""

    __tablename__ = "tracked_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "market" or "event"
    search_queries: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_collected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class NewsArticle(Base):
    """A news article related to tracked items."""

    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(2000), unique=True, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_domain: Mapped[str] = mapped_column(String(200), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    text_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    exa_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    sentiments: Mapped[list[NewsSentiment]] = relationship(
        "NewsSentiment", back_populates="article"
    )

    __table_args__ = (
        Index("idx_news_articles_collected_at", "collected_at"),
        Index("idx_news_articles_published_at", "published_at"),
    )


class NewsArticleMarket(Base):
    """Many-to-many mapping: articles can relate to multiple markets."""

    __tablename__ = "news_article_markets"

    article_id: Mapped[int] = mapped_column(ForeignKey("news_articles.id"), primary_key=True)
    ticker: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("markets.ticker"),
        primary_key=True,
        index=True,
    )


class NewsArticleEvent(Base):
    """Many-to-many mapping: articles can relate to multiple events."""

    __tablename__ = "news_article_events"

    article_id: Mapped[int] = mapped_column(ForeignKey("news_articles.id"), primary_key=True)
    event_ticker: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("events.ticker"),
        primary_key=True,
        index=True,
    )


class NewsSentiment(Base):
    """Sentiment analysis result for an article."""

    __tablename__ = "news_sentiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("news_articles.id"), index=True)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    score: Mapped[float] = mapped_column(Float, nullable=False)
    label: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    keywords_matched: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list

    article: Mapped[NewsArticle] = relationship("NewsArticle", back_populates="sentiments")

    __table_args__ = (Index("idx_news_sentiments_analyzed_at", "analyzed_at"),)
