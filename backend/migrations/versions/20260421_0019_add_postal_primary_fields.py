"""add postal primary selection fields

Revision ID: 20260421_0019
Revises: 20260420_0018
Create Date: 2026-04-21 00:30:00
"""

from alembic import op

revision = "20260421_0019"
down_revision = "20260420_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE postal.region_postal_code
        ADD COLUMN IF NOT EXISTS overlap_area double precision NULL;
        """
    )
    op.execute(
        """
        ALTER TABLE postal.region_postal_code
        ADD COLUMN IF NOT EXISTS is_primary boolean NOT NULL DEFAULT false;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_postal_region_postal_code_primary
        ON postal.region_postal_code (postal_code, is_primary);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS postal.ix_postal_region_postal_code_primary;")
    op.execute(
        """
        ALTER TABLE postal.region_postal_code
        DROP COLUMN IF EXISTS is_primary;
        """
    )
    op.execute(
        """
        ALTER TABLE postal.region_postal_code
        DROP COLUMN IF EXISTS overlap_area;
        """
    )
