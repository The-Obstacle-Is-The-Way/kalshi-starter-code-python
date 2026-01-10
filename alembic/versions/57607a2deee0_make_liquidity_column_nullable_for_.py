"""Make liquidity column nullable for deprecated field

Revision ID: 57607a2deee0
Revises: 890030df7b2c
Create Date: 2026-01-09 13:36:34.714561

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "57607a2deee0"
down_revision: str | Sequence[str] | None = "890030df7b2c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite requires batch mode to alter column nullability
    with op.batch_alter_table("price_snapshots", schema=None) as batch_op:
        batch_op.alter_column("liquidity", existing_type=sa.INTEGER(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # If the column contains NULLs after the upgrade, making it non-nullable will fail.
    # Since this downgrade restores the previous schema shape, coerce NULLs to a
    # reasonable default before tightening the constraint.
    op.execute("UPDATE price_snapshots SET liquidity = 0 WHERE liquidity IS NULL")
    # SQLite requires batch mode to alter column nullability
    with op.batch_alter_table("price_snapshots", schema=None) as batch_op:
        batch_op.alter_column("liquidity", existing_type=sa.INTEGER(), nullable=False)
