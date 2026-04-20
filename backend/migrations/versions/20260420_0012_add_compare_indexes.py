"""add compare indexes

Revision ID: 20260420_0012
Revises: 20260420_0011
Create Date: 2026-04-20 14:30:00
"""

from alembic import op


revision = "20260420_0012"
down_revision = "20260420_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_region_score_snapshot_compare_lookup
        ON region_score_snapshot (profile_key, period, region_id);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_region_indicator_value_compare_lookup
        ON region_indicator_value (region_id, period, indicator_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_region_indicator_value_compare_lookup;")
    op.execute("DROP INDEX IF EXISTS ix_region_score_snapshot_compare_lookup;")
