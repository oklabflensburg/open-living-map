"""add prefix indexes for region autocomplete

Revision ID: 20260421_0024
Revises: 20260421_0023
Create Date: 2026-04-21 23:35:00
"""

from alembic import op


revision = "20260421_0024"
down_revision = "20260421_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_region_name_prefix
        ON region (lower(name) text_pattern_ops);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_region_state_name_prefix
        ON region (lower(state_name) text_pattern_ops);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_region_state_name_prefix;")
    op.execute("DROP INDEX IF EXISTS ix_region_name_prefix;")
