"""add region district name

Revision ID: 20260419_0009
Revises: 20260419_0008
Create Date: 2026-04-19 11:05:00
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260419_0009"
down_revision: str | None = "20260419_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE region
        ADD COLUMN IF NOT EXISTS district_name text;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE region
        DROP COLUMN IF EXISTS district_name;
        """
    )
