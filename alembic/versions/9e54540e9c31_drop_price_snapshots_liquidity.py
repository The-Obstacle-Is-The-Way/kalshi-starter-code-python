"""drop price_snapshots liquidity

Revision ID: 9e54540e9c31
Revises: 57607a2deee0
Create Date: 2026-01-10 00:08:43.435783

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9e54540e9c31"
down_revision: str | Sequence[str] | None = "57607a2deee0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("price_snapshots", schema=None) as batch_op:
        batch_op.drop_column("liquidity")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("price_snapshots", schema=None) as batch_op:
        batch_op.add_column(sa.Column("liquidity", sa.Integer(), nullable=True))
