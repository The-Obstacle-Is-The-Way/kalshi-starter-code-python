"""change_positions_thesis_id_to_string

Revision ID: 7f0c2b3a1d9e
Revises: 43e7135752b1
Create Date: 2026-01-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7f0c2b3a1d9e"
down_revision: str | Sequence[str] | None = "43e7135752b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("positions") as batch_op:
        batch_op.alter_column(
            "thesis_id",
            existing_type=sa.Integer(),
            type_=sa.String(length=64),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("positions") as batch_op:
        batch_op.alter_column(
            "thesis_id",
            existing_type=sa.String(length=64),
            type_=sa.Integer(),
            existing_nullable=True,
        )
