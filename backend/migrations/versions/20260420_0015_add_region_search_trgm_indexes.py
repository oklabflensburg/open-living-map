"""add trigram indexes for region search

Revision ID: 20260420_0015
Revises: 20260420_0014
Create Date: 2026-04-20 18:05:00
"""

from alembic import op


revision = "20260420_0015"
down_revision = "20260420_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_region_name_trgm
        ON region
        USING gin (lower(name) gin_trgm_ops);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_region_state_name_trgm
        ON region
        USING gin (lower(state_name) gin_trgm_ops);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_region_state_name_trgm;")
    op.execute("DROP INDEX IF EXISTS ix_region_name_trgm;")
