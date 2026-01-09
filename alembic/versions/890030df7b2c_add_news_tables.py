"""add news tables

Revision ID: 890030df7b2c
Revises: 7f0c2b3a1d9e
Create Date: 2026-01-09 02:40:33.733426

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "890030df7b2c"
down_revision: str | Sequence[str] | None = "7f0c2b3a1d9e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "tracked_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(length=100), nullable=False),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("search_queries", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker"),
    )

    op.create_table(
        "news_articles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("url", sa.String(length=2000), nullable=False),
        sa.Column("url_hash", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_domain", sa.String(length=200), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("text_snippet", sa.Text(), nullable=True),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("exa_request_id", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index(op.f("ix_news_articles_url_hash"), "news_articles", ["url_hash"])
    op.create_index(op.f("idx_news_articles_collected_at"), "news_articles", ["collected_at"])
    op.create_index(op.f("idx_news_articles_published_at"), "news_articles", ["published_at"])

    op.create_table(
        "news_article_markets",
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["news_articles.id"]),
        sa.ForeignKeyConstraint(["ticker"], ["markets.ticker"]),
        sa.PrimaryKeyConstraint("article_id", "ticker"),
    )
    op.create_index(op.f("ix_news_article_markets_ticker"), "news_article_markets", ["ticker"])

    op.create_table(
        "news_article_events",
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("event_ticker", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["news_articles.id"]),
        sa.ForeignKeyConstraint(["event_ticker"], ["events.ticker"]),
        sa.PrimaryKeyConstraint("article_id", "event_ticker"),
    )
    op.create_index(
        op.f("ix_news_article_events_event_ticker"),
        "news_article_events",
        ["event_ticker"],
    )

    op.create_table(
        "news_sentiments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("label", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("keywords_matched", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["news_articles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_news_sentiments_article_id"), "news_sentiments", ["article_id"])
    op.create_index(op.f("idx_news_sentiments_analyzed_at"), "news_sentiments", ["analyzed_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("idx_news_sentiments_analyzed_at"), table_name="news_sentiments")
    op.drop_index(op.f("ix_news_sentiments_article_id"), table_name="news_sentiments")
    op.drop_table("news_sentiments")

    op.drop_index(op.f("ix_news_article_events_event_ticker"), table_name="news_article_events")
    op.drop_table("news_article_events")

    op.drop_index(op.f("ix_news_article_markets_ticker"), table_name="news_article_markets")
    op.drop_table("news_article_markets")

    op.drop_index(op.f("idx_news_articles_published_at"), table_name="news_articles")
    op.drop_index(op.f("idx_news_articles_collected_at"), table_name="news_articles")
    op.drop_index(op.f("ix_news_articles_url_hash"), table_name="news_articles")
    op.drop_table("news_articles")

    op.drop_table("tracked_items")
